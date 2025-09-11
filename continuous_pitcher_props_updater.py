#!/usr/bin/env python3
"""Continuous Bovada Pitcher Props Updater

Purpose:
  Repeatedly poll Bovada pitcher prop lines and regenerate pitcher prop
  projections/recommendations until all games for the day have started (or a
  max runtime cutoff is reached). Designed to be run alongside the Flask app
  so the frontend/API surfaces newly available lines & recommendations in
  near real-time (the app already reloads recommendations file per request).

Behavior:
  - Interval-based loop (default 600s) adjustable via env var
    PITCHER_PROPS_POLL_INTERVAL_SEC.
  - Faster early polling while coverage < 50% (default 180s) via
    PITCHER_PROPS_FAST_INTERVAL_SEC.
  - Stops once all scheduled games have started (live or final) OR reaches
    max age in minutes (PITCHER_PROPS_MAX_AGE_MIN, default 480).
  - Per-iteration: fetch props -> generate projections -> measure coverage.
  - Writes progress snapshot: data/daily_bovada/pitcher_props_progress_<date>.json
  - Detects and logs newly added markets per pitcher.
  - Skips re-fetch if last fetch was < 60s ago (guard against manual spamming).

Optional Env Vars:
  PITCHER_PROPS_POLL_INTERVAL_SEC=600
  PITCHER_PROPS_FAST_INTERVAL_SEC=180
  PITCHER_PROPS_MAX_AGE_MIN=480
  PITCHER_PROPS_EDGE_THRESHOLD=0.5 (currently used only in projections script; adjust there if needed)
  PITCHER_PROPS_MIN_MARKETS=1 (markets with a 'line' to consider pitcher covered)

Run:
  python continuous_pitcher_props_updater.py

Safe to terminate anytime; restart resumes where left off.
"""
import os
import json
import time
import traceback
import subprocess
from datetime import datetime, timedelta
from typing import Dict, Any, Tuple
from math import pow

from fetch_bovada_pitcher_props import main as fetch_props_main
from generate_pitcher_prop_projections import main as generate_props_main

# Lazy import to avoid circular startup cost if MLB API unavailable briefly
_live_data_mod = None
AUTO_GIT = os.environ.get('PITCHER_PROPS_AUTO_GIT','0') == '1'


def load_live_games(date_str: str):
    global _live_data_mod
    try:
        if _live_data_mod is None:
            import live_mlb_data as _live_data_mod  # type: ignore
        mlb = _live_data_mod.LiveMLBData()
        return mlb.get_enhanced_games_data(date_str) or []
    except Exception:
        return []


def normalize_pitcher_key(name: str) -> str:
    return name.lower().strip()


def load_props_file(date_str: str) -> Dict[str, Any]:
    path = os.path.join('data', 'daily_bovada', f'bovada_pitcher_props_{date_str.replace('-', '_')}.json')
    if not os.path.exists(path):
        return {}
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {}


def extract_pitcher_market_summary(props_payload: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    out = {}
    pitcher_props = props_payload.get('pitcher_props', {}) if isinstance(props_payload, dict) else {}
    for p_key, markets in pitcher_props.items():
        line_markets = {mk: mv for mk, mv in markets.items() if isinstance(mv, dict) and mv.get('line') is not None}
        out[p_key] = {
            'markets_with_lines': list(line_markets.keys()),
            'market_count': len(line_markets)
        }
    return out


def coverage_stats(summary: Dict[str, Dict[str, Any]], min_markets: int) -> Tuple[int, int, float]:
    total = len(summary)
    covered = sum(1 for v in summary.values() if v['market_count'] >= min_markets)
    pct = (covered / total * 100.0) if total else 0.0
    return covered, total, pct


def all_games_started(games) -> bool:
    if not games:
        return False
    for g in games:
        status = (g.get('status') or '').lower()
        if status in ('scheduled', 'pre-game', 'pregame'):
            return False
    return True


def write_progress(date_str: str, progress: Dict[str, Any]):
    out_path = os.path.join('data', 'daily_bovada', f'pitcher_props_progress_{date_str.replace('-', '_')}.json')
    tmp_path = out_path + '.tmp'
    try:
        with open(tmp_path, 'w', encoding='utf-8') as f:
            json.dump(progress, f, indent=2)
        os.replace(tmp_path, out_path)
    except Exception:
        pass


VOLATILITY_FILE = os.path.join('data','daily_bovada','pitcher_prop_volatility.json')

def load_volatility_doc():
    if os.path.exists(VOLATILITY_FILE):
        try:
            with open(VOLATILITY_FILE,'r',encoding='utf-8') as f:
                d = json.load(f)
            if isinstance(d, dict):
                return d
        except Exception:
            pass
    return {}

def save_volatility_doc(doc):
    tmp = VOLATILITY_FILE + '.tmp'
    try:
        with open(tmp,'w',encoding='utf-8') as f:
            json.dump(doc,f,indent=2)
        os.replace(tmp,VOLATILITY_FILE)
    except Exception:
        pass

vol_doc = load_volatility_doc()


def main():
    date_str = datetime.now().strftime('%Y-%m-%d')

    poll_interval = int(os.environ.get('PITCHER_PROPS_POLL_INTERVAL_SEC', 600))
    fast_interval = int(os.environ.get('PITCHER_PROPS_FAST_INTERVAL_SEC', 180))
    max_age_min = int(os.environ.get('PITCHER_PROPS_MAX_AGE_MIN', 480))
    min_markets = int(os.environ.get('PITCHER_PROPS_MIN_MARKETS', 1))

    start_time = datetime.utcnow()
    last_fetch_time = None
    previous_summary = {}
    previous_lines_snapshot: Dict[str, Dict[str, Dict[str, float]]] = {}

    def load_line_history_path(date_str: str) -> str:
        return os.path.join('data', 'daily_bovada', f'pitcher_prop_line_history_{date_str.replace('-', '_')}.json')

    def append_line_history_events(date_str: str, events: list[dict]):
        if not events:
            return
        path = load_line_history_path(date_str)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        doc = {'date': date_str, 'events': []}
        if os.path.exists(path):
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    existing = json.load(f)
                if isinstance(existing, dict) and isinstance(existing.get('events'), list):
                    doc = existing
            except Exception:
                pass
        doc['events'].extend(events)
        tmp = path + '.tmp'
        try:
            with open(tmp, 'w', encoding='utf-8') as f:
                json.dump(doc, f, indent=2)
            os.replace(tmp, path)
        except Exception:
            pass

    print(f"[PitcherPropsUpdater] Starting continuous updater for {date_str}")
    print(f"  poll_interval={poll_interval}s fast_interval={fast_interval}s max_age_min={max_age_min} min_markets={min_markets}")

    iteration = 0
    while True:
        iteration += 1
        now = datetime.utcnow()
        age_min = (now - start_time).total_seconds() / 60.0

        if age_min > max_age_min:
            print(f"[PitcherPropsUpdater] Max age {max_age_min} min reached; exiting")
            break

        games = load_live_games(date_str)
        if games and all_games_started(games):
            print("[PitcherPropsUpdater] All games started; exiting updater")
            break

        # Guard: avoid too-frequent fetches if external trigger also running
        if last_fetch_time and (now - last_fetch_time).total_seconds() < 60:
            time.sleep(30)
            continue

        print(f"[PitcherPropsUpdater] Iteration {iteration} fetching props...")
        try:
            fetch_ok = fetch_props_main()
            last_fetch_time = datetime.utcnow()
        except Exception as e:
            print(f"[PitcherPropsUpdater] Fetch error: {e}")
            fetch_ok = False

        if fetch_ok:
            try:
                generate_props_main()
            except Exception as e:
                print(f"[PitcherPropsUpdater] Generation error: {e}")

        props_payload = load_props_file(date_str)
        summary = extract_pitcher_market_summary(props_payload)

        # Line movement detection (compare each market line & odds)
        line_events = []
        current_pitcher_props = props_payload.get('pitcher_props', {}) if isinstance(props_payload, dict) else {}
        for p_key, markets in current_pitcher_props.items():
            prev_p = previous_lines_snapshot.get(p_key, {})
            for mk, mv in markets.items():
                if not isinstance(mv, dict):
                    continue
                if 'line' not in mv:
                    continue
                new_line = mv.get('line')
                new_over = mv.get('over_odds')
                new_under = mv.get('under_odds')
                prev_mk = prev_p.get(mk, {})
                changed = (
                    prev_mk.get('line') != new_line or
                    prev_mk.get('over_odds') != new_over or
                    prev_mk.get('under_odds') != new_under
                )
                if changed and prev_mk:  # skip first appearance as movement event; treat as initial snapshot
                    line_events.append({
                        'ts': datetime.utcnow().isoformat(),
                        'pitcher': p_key,
                        'market': mk,
                        'old_line': prev_mk.get('line'),
                        'new_line': new_line,
                        'old_over_odds': prev_mk.get('over_odds'),
                        'new_over_odds': new_over,
                        'old_under_odds': prev_mk.get('under_odds'),
                        'new_under_odds': new_under
                    })
                # update snapshot structure staged
                prev_p.setdefault(mk, {})
                prev_p[mk]['line'] = new_line
                prev_p[mk]['over_odds'] = new_over
                prev_p[mk]['under_odds'] = new_under
            previous_lines_snapshot[p_key] = prev_p
        if line_events:
            append_line_history_events(date_str, line_events)
            # Attempt live broadcast for recent events (non-fatal if unavailable)
            try:
                from app import broadcast_pitcher_update  # type: ignore
                for ev in line_events[-20:]:  # limit burst
                    broadcast_pitcher_update({'type': 'line_move', **ev})
            except Exception:
                pass
            # Update simple volatility estimates per pitcher/market (EW variance of line changes)
            for ev in line_events:
                pk = ev['pitcher']
                mk = ev['market']
                old_line = ev.get('old_line')
                new_line = ev.get('new_line')
                if old_line is None or new_line is None:
                    continue
                delta = float(new_line) - float(old_line)
                rec = vol_doc.setdefault(pk, {}).setdefault(mk, {'var': 0.5, 'updates': 0})
                # Exponential weighting
                alpha = 0.2
                rec['var'] = (1-alpha)*rec['var'] + alpha*(delta*delta)
                rec['updates'] = rec.get('updates',0) + 1
            save_volatility_doc(vol_doc)
        covered, total, pct = coverage_stats(summary, min_markets)

        # Diff new markets
        newly_filled = []
        changed_any = False
        for p_key, info in summary.items():
            prev = previous_summary.get(p_key, {})
            prev_set = set(prev.get('markets_with_lines', []))
            new_set = set(info['markets_with_lines'])
            if new_set - prev_set:
                newly_filled.append((p_key, list(new_set)))
                changed_any = True
            if info['market_count'] != prev.get('market_count'):
                changed_any = True

        if changed_any:
            # Regenerate recommendations again (ensures updated odds/lines stored)
            try:
                generate_props_main()
            except Exception as e:
                print(f"[PitcherPropsUpdater] Secondary generation error: {e}")

            # Optional git commit for remote sync (Render) if enabled
            if AUTO_GIT:
                try:
                    subprocess.run(["git","add","data/daily_bovada"], check=False)
                    subprocess.run(["git","commit","-m", f"auto: update pitcher props {date_str} iteration {iteration}"], check=False)
                    subprocess.run(["git","push"], check=False)
                except Exception as e:
                    print(f"[PitcherPropsUpdater] Git push failed: {e}")

        print(f"[PitcherPropsUpdater] Coverage: {covered}/{total} pitchers with >= {min_markets} market(s) ({pct:.1f}%)")
        if newly_filled:
            print(f"[PitcherPropsUpdater] New/expanded markets for {len(newly_filled)} pitcher(s):")
            for p_key, mkts in newly_filled[:8]:  # limit spam
                print(f"   - {p_key}: {mkts}")
            if len(newly_filled) > 8:
                print(f"   (+{len(newly_filled)-8} more)")

        progress_doc = {
            'date': date_str,
            'timestamp': datetime.utcnow().isoformat(),
            'iteration': iteration,
            'coverage': {
                'covered_pitchers': covered,
                'total_pitchers': total,
                'percent': pct
            },
            'newly_filled_pitchers': [p for p, _ in newly_filled],
            'all_pitcher_markets': summary,
            'all_games_started': all_games_started(games),
            'active_game_count': len(games),
        }
        write_progress(date_str, progress_doc)

        previous_summary = summary

        # Adaptive interval: if coverage < 50% use fast interval
        target_sleep = fast_interval if pct < 50.0 else poll_interval
        # If near game start times (within 30 min), reduce sleep to fast interval
        try:
            upcoming_soon = False
            for g in games:
                status = (g.get('status') or '').lower()
                if status in ('scheduled', 'pre-game', 'pregame'):
                    # Attempt to parse game_time (ISO or HH:MM) if available
                    gt = g.get('game_time') or g.get('start_time')
                    if gt:
                        try:
                            # Accept HH:MM local; treat as today UTC fallback
                            if 'T' in gt:
                                dt = datetime.fromisoformat(gt.replace('Z',''))
                            else:
                                dt = datetime.strptime(gt, '%H:%M')
                                # assign today's date
                                dt = datetime.utcnow().replace(hour=dt.hour, minute=dt.minute, second=0, microsecond=0)
                            if 0 <= (dt - datetime.utcnow()).total_seconds() <= 1800:
                                upcoming_soon = True
                                break
                        except Exception:
                            pass
            if upcoming_soon:
                target_sleep = min(target_sleep, fast_interval)
        except Exception:
            pass

        print(f"[PitcherPropsUpdater] Sleeping {target_sleep}s...")
        time.sleep(target_sleep)

    print("[PitcherPropsUpdater] Exited cleanly")
    return True


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("[PitcherPropsUpdater] Interrupted; exiting")
    except Exception:
        print("[PitcherPropsUpdater] Fatal error:\n" + traceback.format_exc())
