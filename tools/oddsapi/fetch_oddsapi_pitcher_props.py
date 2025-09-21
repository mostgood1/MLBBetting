import os
import sys
import json
import time
import argparse
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List, Tuple, Optional, Set

import requests
import importlib.util

API_BASE = "https://api.the-odds-api.com/v4/sports"
SPORT = "baseball_mlb"

# Canonical OddsAPI market keys (external -> internal)
# See: https://the-odds-api.com/sports-odds-data/betting-markets.html (MLB Player Props)
DEFAULT_EXTERNAL_TO_INTERNAL = {
    "pitcher_strikeouts": "strikeouts",
    "pitcher_outs": "outs",
    # Additional MLB pitcher markets (opt-in via --markets)
    # "pitcher_hits_allowed": "hits_allowed",
    # "pitcher_walks": "walks",
    # "pitcher_earned_runs": "earned_runs",
}

# Backwards-compatible synonyms → canonical external keys
MARKET_SYNONYMS = {
    # Historic/incorrect names sometimes used in code or docs
    "player_strikeouts": "pitcher_strikeouts",
    "player_recorded_outs": "pitcher_outs",
    "pitcher_recorded_outs": "pitcher_outs",
    "recorded_outs": "pitcher_outs",
    "outs": "pitcher_outs",
}


def american_from_decimal(decimal_odds: float) -> Optional[str]:
    if decimal_odds is None:
        return None
    try:
        d = float(decimal_odds)
    except Exception:
        return None
    if d <= 0:
        return None
    if d >= 2:
        return f"+{int(round((d - 1) * 100))}"
    return f"-{int(round(100 / (d - 1)))}"


_NORMALIZE_FN = None


def _get_normalize_fn():
    global _NORMALIZE_FN
    if _NORMALIZE_FN is not None:
        return _NORMALIZE_FN
    # 1) Try regular import
    try:
        from utils.name_normalization import normalize_name  # type: ignore
        _NORMALIZE_FN = normalize_name
        return _NORMALIZE_FN
    except Exception:
        pass
    # 2) Try by adjusting sys.path to repo root
    try:
        here = os.path.abspath(os.path.dirname(__file__))
        repo_root = os.path.abspath(os.path.join(here, os.pardir, os.pardir))
        if repo_root not in sys.path:
            sys.path.insert(0, repo_root)
        from utils.name_normalization import normalize_name  # type: ignore
        _NORMALIZE_FN = normalize_name
        return _NORMALIZE_FN
    except Exception:
        pass
    # 3) Try import by absolute file path
    try:
        here = os.path.abspath(os.path.dirname(__file__))
        repo_root = os.path.abspath(os.path.join(here, os.pardir, os.pardir))
        mod_path = os.path.join(repo_root, "utils", "name_normalization.py")
        if os.path.exists(mod_path):
            spec = importlib.util.spec_from_file_location("utils.name_normalization", mod_path)
            if spec and spec.loader:
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                _NORMALIZE_FN = getattr(mod, "normalize_name")
                return _NORMALIZE_FN
    except Exception:
        pass
    # 4) Fallback minimal normalizer
    def _fallback(x: str | None) -> str:
        s = (x or "").lower().strip()
        for ch in [".", "'", ",", "-", "  "]:
            s = s.replace(ch, " ")
        return " ".join(s.split())

    _NORMALIZE_FN = _fallback
    return _NORMALIZE_FN


def norm_name(name: str) -> str:
    normalize_name = _get_normalize_fn()
    return normalize_name((name or "").split("(")[0].strip())


def _http_get(url: str, params: Dict[str, Any], timeout: int = 30) -> Any:
    r = requests.get(url, params=params, timeout=timeout)
    # Raise for non-2xx; let caller handle
    r.raise_for_status()
    return r.json(), {k.lower(): v for k, v in r.headers.items()}


def _event_has_any_markets(ev_id: str, desired_markets: List[str], api_key: str) -> bool:
    """Query event markets and check if any of desired player prop markets are present.
    If the markets endpoint errors, return True (don't over-filter).
    """
    try:
        url = f"{API_BASE}/{SPORT}/events/{ev_id}/markets"
        data, _ = _http_get(url, {"apiKey": api_key})
        keys = set((m.get("key") or "").lower() for m in (data or []))
        for k in desired_markets:
            if k in keys:
                return True
        return False
    except Exception:
        # Be permissive on probe failure
        return True


def _parse_iso(ts: str) -> Optional[datetime]:
    if not ts:
        return None
    try:
        # Ensure timezone-aware in UTC
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        return None


def _extract_pitcher_props_from_markets(
    markets: List[Dict[str, Any]],
    external_to_internal: Dict[str, str],
    pitcher_props: Dict[str, Dict[str, Dict[str, Any]]],
):
    for m in markets or []:
        key = (m.get("key") or "").lower()
        if key not in external_to_internal:
            continue
        internal_key = external_to_internal[key]
        outcomes = m.get("outcomes") or []
        for oc in outcomes:
            # For player props, description should contain the player name; name often is Over/Under.
            name = oc.get("description") or oc.get("participant") or None
            line = oc.get("point")
            price = oc.get("price") or oc.get("odds") or None
            side = (oc.get("name") or "").upper()  # Often 'Over' or 'Under'
            american = None
            try:
                if isinstance(price, str) and (price.startswith("+") or price.startswith("-")):
                    american = price
                elif isinstance(price, (int, float)):
                    # OddsAPI often uses american integers already; if not in range, fallback
                    american = str(price) if abs(float(price)) >= 100 else american_from_decimal(float(price))
            except Exception:
                american = None
            if not name or line is None:
                continue
            nk = norm_name(name)
            if not nk:
                continue
            bucket = pitcher_props.setdefault(nk, {})
            entry = bucket.setdefault(internal_key, {"line": None, "over_odds": None, "under_odds": None, "_src": "oddsapi"})
            # Use the first seen line; different books may differ by 0.5 – we keep earliest
            if entry["line"] is None:
                entry["line"] = line
            if side.startswith("OVER") and entry.get("over_odds") is None:
                entry["over_odds"] = american
            elif side.startswith("UNDER") and entry.get("under_odds") is None:
                entry["under_odds"] = american


def fetch_props(api_key: str, date_str: str, *, regions: str = "us", bookmakers: Optional[str] = None,
                external_to_internal: Optional[Dict[str, str]] = None, include_completed: bool = False,
                snapshot_offset_minutes: int = 60, odds_format: str = "american",
                hist_snapshots: Optional[List[str]] = None, probe_markets: bool = False) -> Dict[str, Any]:
    """
    Fetch MLB pitcher player props from OddsAPI for a specific date.

    Strategy:
    - Get current events (/events) and query per-event odds for requested player prop markets.
    - Optionally include completed same-day events by querying historical endpoints:
      • /historical/sports/{sport}/events for the date → event ids
      • /historical/sports/{sport}/events/{eventId}/odds at (commence_time - snapshot_offset)
    """
    external_to_internal = external_to_internal or DEFAULT_EXTERNAL_TO_INTERNAL
    pitcher_props: Dict[str, Dict[str, Dict[str, Any]]] = {}

    # 1) Current events (upcoming + live)
    events_url = f"{API_BASE}/{SPORT}/events"
    params_events = {"apiKey": api_key}
    events, headers_events = _http_get(events_url, params_events)

    # Filter to target date (UTC date match against commence_time)
    todays_events: List[Dict[str, Any]] = []
    for ev in events or []:
        ct = (ev.get("commence_time") or "")[:10]
        if ct == date_str:
            todays_events.append(ev)

    # For each event, get event odds for player prop markets
    desired_external_markets = list(external_to_internal.keys())
    markets_csv = ",".join(desired_external_markets)
    # Probe stats
    probed_events = 0
    events_with_markets = 0
    for ev in todays_events:
        ev_id = ev.get("id")
        if not ev_id:
            continue
        if probe_markets:
            # Skip events that clearly don't list our desired markets
            probed_events += 1
            has_any = _event_has_any_markets(ev_id, desired_external_markets, api_key)
            if has_any:
                events_with_markets += 1
            if not has_any:
                continue
        ev_odds_url = f"{API_BASE}/{SPORT}/events/{ev_id}/odds"
        params_odds = {
            "apiKey": api_key,
            "regions": regions,
            "oddsFormat": odds_format,
            "markets": markets_csv,
        }
        if bookmakers:
            params_odds["bookmakers"] = bookmakers
        try:
            ev_odds, _ = _http_get(ev_odds_url, params_odds)
        except requests.HTTPError as e:
            # Skip problematic events; continue
            continue
        # The schema returns a single game object
        if not ev_odds or not isinstance(ev_odds, dict):
            continue
        for bk in (ev_odds.get("bookmakers") or []):
            _extract_pitcher_props_from_markets(bk.get("markets") or [], external_to_internal, pitcher_props)

    # 2) Optionally include completed games via historical snapshot
    if include_completed:
        # Get list of historical events for the date (snapshot at end of day UTC)
        hist_events_url = f"https://api.the-odds-api.com/v4/historical/sports/{SPORT}/events"
        end_of_day_iso = f"{date_str}T23:59:59Z"
        params_hist_events = {"apiKey": api_key, "date": end_of_day_iso}
        try:
            hist_events, _ = _http_get(hist_events_url, params_hist_events)
        except requests.HTTPError:
            hist_events = []

        # Build a set of event ids we already processed (from current events) to avoid duplicate work
        seen_ids: Set[str] = {e.get("id") for e in todays_events if e.get("id")}

        # Determine snapshot list
        snapshot_list: List[str] = []
        if hist_snapshots:
            for t in hist_snapshots:
                t = t.strip()
                if not t:
                    continue
                # Accept either HH:MM(:SS) or full ISO; build ISO if time-only
                if "T" in t:
                    iso_ts = t if t.endswith("Z") else (t + "Z")
                else:
                    # Assume UTC time-of-day on the same date
                    iso_ts = f"{date_str}T{t}Z"
                snapshot_list.append(iso_ts)
        if not snapshot_list:
            snapshot_list = [end_of_day_iso]

        for hev in hist_events or []:
            # Filter to target date again
            ct = (hev.get("commence_time") or "")[:10]
            if ct != date_str:
                continue
            ev_id = hev.get("id")
            if not ev_id or ev_id in seen_ids:
                continue
            hist_event_odds_url = f"https://api.the-odds-api.com/v4/historical/sports/{SPORT}/events/{ev_id}/odds"
            for snap_iso in snapshot_list:
                params_hist_odds = {
                    "apiKey": api_key,
                    "regions": regions,
                    "oddsFormat": odds_format,
                    "markets": markets_csv,
                    "date": snap_iso,
                }
                if bookmakers:
                    params_hist_odds["bookmakers"] = bookmakers
                try:
                    hev_odds, _ = _http_get(hist_event_odds_url, params_hist_odds)
                except requests.HTTPError:
                    continue
                if not hev_odds or not isinstance(hev_odds, dict):
                    continue
                for bk in (hev_odds.get("bookmakers") or []):
                    _extract_pitcher_props_from_markets(bk.get("markets") or [], external_to_internal, pitcher_props)

    return {
        "date": date_str,
        "retrieved_at": datetime.utcnow().isoformat(),
        "pitcher_props": pitcher_props,
        "meta": {
            "markets": list(external_to_internal.keys()),
            "regions": regions,
            "bookmakers": bookmakers.split(",") if bookmakers else None,
            "include_completed": include_completed,
            "hist_snapshots": hist_snapshots or [end_of_day_iso] if include_completed else None,
            "probe_markets": probe_markets,
            "probe_stats": {"probed_events": probed_events, "events_with_markets": events_with_markets} if probe_markets else None,
        }
    }


def main():
    parser = argparse.ArgumentParser(description="Fetch MLB pitcher props from OddsAPI and save to data folder")
    parser.add_argument("--date", default=datetime.utcnow().strftime("%Y-%m-%d"), help="Target date in YYYY-MM-DD (UTC)")
    parser.add_argument("--api-key", default=os.environ.get("ODDS_API_KEY") or os.environ.get("ODDSAPI_KEY"), help="OddsAPI key or set ODDS_API_KEY env var")
    parser.add_argument("--regions", default="us", help="Regions filter (e.g., us,us2,uk)")
    parser.add_argument("--bookmakers", default=None, help="Comma-separated bookmaker keys (takes priority over regions)")
    parser.add_argument("--markets", default=",".join(DEFAULT_EXTERNAL_TO_INTERNAL.keys()), help="Comma-separated OddsAPI market keys to fetch (accepts synonyms)")
    parser.add_argument("--include-completed", action="store_true", help="Also fetch historical odds for completed same-day games")
    parser.add_argument("--hist-snapshots", default=None, help="Comma-separated UTC times (HH:MM[:SS]) or ISO timestamps to snapshot historical odds; defaults to end-of-day if omitted")
    parser.add_argument("--probe-markets", action="store_true", help="Probe /events/{id}/markets to skip events with no desired markets (current events only)")
    parser.add_argument("--snapshot-offset-minutes", type=int, default=60, help="Historical snapshot offset before commence_time (minutes)")
    parser.add_argument("--out", default=None, help="Optional explicit output file path (JSON)")
    args = parser.parse_args()

    if not args.api_key:
        # Fallback: try to read from data/closing_lines_config.json
        try:
            cfg_path = os.path.join("data", "closing_lines_config.json")
            if os.path.exists(cfg_path):
                with open(cfg_path, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                api_keys = (cfg or {}).get("api_keys", {})
                args.api_key = api_keys.get("odds_api_key") or api_keys.get("the_odds_api_key")
        except Exception:
            args.api_key = None
    if not args.api_key:
        print("ERROR: ODDS_API_KEY not provided via --api-key, env var, or data/closing_lines_config.json", file=sys.stderr)
        sys.exit(2)

    # Build external→internal map from CLI with synonym resolution
    requested = [m.strip().lower() for m in (args.markets or "").split(",") if m.strip()]
    resolved_external: List[str] = []
    for mk in requested:
        canonical = MARKET_SYNONYMS.get(mk, mk)
        resolved_external.append(canonical)
    # Keep only supported keys and preserve order without duplicates
    seen: Set[str] = set()
    filtered_external = []
    for mk in resolved_external:
        if mk in DEFAULT_EXTERNAL_TO_INTERNAL and mk not in seen:
            filtered_external.append(mk)
            seen.add(mk)
    # Fallback to defaults if nothing valid requested
    if not filtered_external:
        filtered_external = list(DEFAULT_EXTERNAL_TO_INTERNAL.keys())
    external_to_internal = {mk: DEFAULT_EXTERNAL_TO_INTERNAL[mk] for mk in filtered_external}

    # Build hist snapshots list
    hist_snaps: Optional[List[str]] = None
    if args.hist_snapshots:
        hist_snaps = [s.strip() for s in args.hist_snapshots.split(",") if s.strip()]

    out_doc = fetch_props(
        args.api_key,
        args.date,
        regions=args.regions,
        bookmakers=args.bookmakers,
        external_to_internal=external_to_internal,
        include_completed=args.include_completed,
        snapshot_offset_minutes=args.snapshot_offset_minutes,
        hist_snapshots=hist_snaps,
        probe_markets=args.probe_markets,
    )

    # Save to data/daily_oddsapi and also a union mirror in data/daily_bovada naming for easy consumption
    base1 = os.path.join("data", "daily_oddsapi")
    base2 = os.path.join("data", "daily_bovada")
    os.makedirs(base1, exist_ok=True)
    os.makedirs(base2, exist_ok=True)
    safe_date = args.date.replace("-", "_")

    # If an explicit output is provided, write only that file
    saved_paths: List[str] = []
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(out_doc, f, indent=2)
        saved_paths.append(args.out)
    else:
        f1 = os.path.join(base1, f"oddsapi_pitcher_props_{safe_date}.json")
        with open(f1, "w", encoding="utf-8") as f:
            json.dump(out_doc, f, indent=2)
        saved_paths.append(f1)
        # Also write a merged-naming file so unified can read alongside Bovada if needed
        f2 = os.path.join(base2, f"oddsapi_pitcher_props_{safe_date}.json")
        with open(f2, "w", encoding="utf-8") as f:
            json.dump(out_doc, f, indent=2)
        saved_paths.append(f2)

    print(json.dumps({
        "ok": True,
        "saved": saved_paths,
        "pitchers": len(out_doc.get("pitcher_props", {})),
        "markets": out_doc.get("meta", {}).get("markets"),
        "include_completed": out_doc.get("meta", {}).get("include_completed"),
    }))


if __name__ == "__main__":
    main()
