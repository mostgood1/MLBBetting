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
                        synergy_doc = build_game_synergy(date_str)
                        if synergy_doc and isinstance(synergy_doc, dict):
                            # Broadcast top deltas (limit) via SSE
                            try:
                                from app import broadcast_pitcher_update  # type: ignore
                                games = synergy_doc.get('games', {})
                                # sort by sum abs win prob delta
                                items = []
                                for gk, gv in games.items():
                                    d = gv.get('deltas', {})
                                    score = abs(d.get('away_win_prob',0)) + abs(d.get('home_win_prob',0))
                                    items.append((score, gk, d))
                                items.sort(reverse=True)
                                for _, gk, d in items[:8]:
                                    broadcast_pitcher_update({'type':'synergy_delta','game': gk, 'deltas': d, 'date': date_str, 'ts': datetime.utcnow().isoformat()})
                            except Exception:
                                pass
                    except Exception as e2:
                        print(f"[PitcherPropsUpdater] Synergy build error: {e2}")
                    # Refresh unified betting engine predictions (best-effort) after synergy
                    try:
                        subprocess.run(["python","unified_betting_engine.py"], check=False)
                    except Exception as e3:
                        print(f"[PitcherPropsUpdater] Unified engine refresh error: {e3}")
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
import gzip
from datetime import datetime, timedelta
from typing import Dict, Any, Tuple, Optional
from math import pow

from fetch_bovada_pitcher_props import main as fetch_props_main
from generate_pitcher_prop_projections import main as generate_props_main
try:
    from tools.pitcher_sse_worker_bridge import send_events as bridge_send  # type: ignore
except Exception:
    def bridge_send(_events):
        return False

# Lazy import to avoid circular startup cost if MLB API unavailable briefly
_live_data_mod = None
AUTO_GIT = os.environ.get('PITCHER_PROPS_AUTO_GIT','0') == '1' or os.environ.get('AUTO_GIT','0') == '1'


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
    # Build path using a pre-sanitized date tag to avoid complex expressions inside f-strings
    date_tag = date_str.replace('-', '_')
    path = os.path.join('data', 'daily_bovada', f"bovada_pitcher_props_{date_tag}.json")
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
    tag = date_str.replace('-', '_')
    out_path = os.path.join('data', 'daily_bovada', f"pitcher_props_progress_{tag}.json")
    tmp_path = out_path + '.tmp'
    try:
        with open(tmp_path, 'w', encoding='utf-8') as f:
            json.dump(progress, f, indent=2)
        os.replace(tmp_path, out_path)
    except Exception:
        pass

def write_progress_summary(progress_summary: Dict[str, Any]):
    """Write a concise, date-agnostic progress summary for frontend polling.
    Path: data/daily_bovada/props_progress.json
    """
    out_path = os.path.join('data', 'daily_bovada', 'props_progress.json')
    tmp_path = out_path + '.tmp'
    try:
        with open(tmp_path, 'w', encoding='utf-8') as f:
            json.dump(progress_summary, f, indent=2)
        os.replace(tmp_path, out_path)
    except Exception:
        pass


VOLATILITY_FILE = os.path.join('data','daily_bovada','pitcher_prop_volatility.json')
REALIZED_RESULTS_FILE = os.path.join('data','daily_bovada','pitcher_prop_realized_results.json')
CALIBRATION_FILE = os.path.join('data','daily_bovada','pitcher_prop_calibration_meta.json')
INTRADAY_SNAP_DIR = os.path.join('data','daily_bovada','intraday_snapshots')

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

def load_realized_results():
    if os.path.exists(REALIZED_RESULTS_FILE):
        try:
            with open(REALIZED_RESULTS_FILE,'r',encoding='utf-8') as f:
                d=json.load(f)
            if isinstance(d, dict):
                return d
        except Exception:
            pass
    return {'games': [], 'pitcher_market_outcomes': []}

def save_realized_results(doc):
    tmp = REALIZED_RESULTS_FILE + '.tmp'
    try:
        with open(tmp,'w',encoding='utf-8') as f:
            json.dump(doc,f,indent=2)
        os.replace(tmp, REALIZED_RESULTS_FILE)
    except Exception:
        pass

realized_doc = load_realized_results()

def ingest_completed_game_outcomes(date_str: str):
    """Ingest completed game pitcher outcomes (outs, strikeouts, walks, ER, hits) when available.
    Expects a file data/games_<date>.json with final stats or an extended live feed structure.
    Appends to realized_doc if not already present.
    """
    games_path = os.path.join('data', f'games_{date_str}.json')
    if not os.path.exists(games_path):
        return
    try:
        with open(games_path,'r',encoding='utf-8') as f:
            gdata = json.load(f)
    except Exception:
        return
    iterable = []
    if isinstance(gdata, list):
        iterable = gdata
    elif isinstance(gdata, dict):
        if 'games' in gdata and isinstance(gdata['games'], list):
            iterable = gdata['games']
        elif 'games' in gdata and isinstance(gdata['games'], dict):
            iterable = list(gdata['games'].values())
    new_events = 0
    for g in iterable:
        status = (g.get('status') or '').lower()
        if status not in ('final', 'completed'):  # skip unfinished
            continue
        for side in ('away','home'):
            p_name = g.get(f'{side}_pitcher') or g.get('pitcher_info',{}).get(f'{side}_pitcher_name')
            if not p_name:
                continue
            key = p_name.lower().strip()
            # Expect basic stat fields
            line_stats = g.get('pitcher_stats',{}).get(key) or {}
            # fallback direct keys
            k = line_stats.get('strikeouts') or g.get(f'{side}_pitcher_strikeouts')
            outs = line_stats.get('outs_recorded') or g.get(f'{side}_pitcher_outs')
            er = line_stats.get('earned_runs') or g.get(f'{side}_pitcher_er')
            walks = line_stats.get('walks') or g.get(f'{side}_pitcher_walks')
            hits = line_stats.get('hits_allowed') or g.get(f'{side}_pitcher_hits')
            if outs is None and k is None:
                continue
            outcome_entry = {
                'date': date_str,
                'pitcher': key,
                'markets': {
                    'strikeouts': k,
                    'outs': outs,
                    'earned_runs': er,
                    'walks': walks,
                    'hits_allowed': hits
                }
            }
            # de-dup
            if not any(r.get('pitcher')==key and r.get('date')==date_str for r in realized_doc['pitcher_market_outcomes']):
                realized_doc['pitcher_market_outcomes'].append(outcome_entry)
                new_events += 1
    if new_events:
        save_realized_results(realized_doc)

def calibration_pass():
    """Adjust baseline STD_FACTORS in calibration meta file based on historical prediction accuracy vs. realized outcomes.
    For each market: compute absolute error distribution from projections stored in recommendation files vs. realized.
    """
    try:
        meta = {'updated_at': datetime.utcnow().isoformat(), 'markets': {}}
        # Aggregate errors
        # Scan recommendation files (recent 30 days)
        rec_files = sorted([f for f in os.listdir(os.path.join('data','daily_bovada')) if f.startswith('pitcher_prop_recommendations_')])[-30:]
        errors = {}
        for rf in rec_files:
            try:
                with open(os.path.join('data','daily_bovada', rf),'r',encoding='utf-8') as f:
                    rec = json.load(f)
                recs = rec.get('recommendations', [])
                date_tag = rec.get('date') or rf.split('recommendations_')[-1].split('.json')[0]
                # Build realized lookup per pitcher/date
                realized_map = {(r['pitcher'], r['date']): r for r in realized_doc.get('pitcher_market_outcomes', [])}
                for r in recs:
                    pitcher = r.get('pitcher')
                    key = (pitcher, date_tag)
                    realized_entry = realized_map.get(key)
                    if not realized_entry:
                        continue
                    proj = r.get('projections', {})
                    for mkt, proj_val in proj.items():
                        if mkt not in ('strikeouts','outs','earned_runs','walks','hits_allowed'):
                            continue
                        realized_val = realized_entry['markets'].get(mkt)
                        if realized_val is None:
                            continue
                        try:
                            err = abs(float(proj_val) - float(realized_val))
                        except Exception:
                            continue
                        errors.setdefault(mkt, []).append(err)
            except Exception:
                continue
        for mkt, arr in errors.items():
            if not arr:
                continue
            avg_err = sum(arr)/len(arr)
            # Map average error to target std suggestion (heuristic): target std ~ avg_err * 1.25
            target_std = max(0.4, min(3.5, avg_err * 1.25))
            meta['markets'][mkt] = {'avg_abs_error': round(avg_err,3), 'suggested_std': target_std, 'sample_size': len(arr)}
        # Persist calibration suggestions
        tmp = CALIBRATION_FILE + '.tmp'
        with open(tmp,'w',encoding='utf-8') as f:
            json.dump(meta,f,indent=2)
        os.replace(tmp, CALIBRATION_FILE)
        return True
    except Exception:
        return False

def snapshot_intraday(date_str: str, iteration: int, summary: dict):
    try:
        os.makedirs(INTRADAY_SNAP_DIR, exist_ok=True)
        snap = {
            'date': date_str,
            'iteration': iteration,
            'ts': datetime.utcnow().isoformat(),
            'coverage_pct': summary.get('coverage',{}).get('percent'),
            'pitcher_count': summary.get('coverage',{}).get('total_pitchers')
        }
        raw = json.dumps(snap).encode('utf-8')
        path = os.path.join(INTRADAY_SNAP_DIR, f'snap_{date_str}_{iteration}.json.gz')
        with gzip.open(path,'wb') as gz:
            gz.write(raw)
    except Exception:
        pass


def main():
    date_str = datetime.now().strftime('%Y-%m-%d')

    poll_interval = int(os.environ.get('PITCHER_PROPS_POLL_INTERVAL_SEC', 600))
    fast_interval = int(os.environ.get('PITCHER_PROPS_FAST_INTERVAL_SEC', 180))
    max_age_min = int(os.environ.get('PITCHER_PROPS_MAX_AGE_MIN', 480))
    min_markets = int(os.environ.get('PITCHER_PROPS_MIN_MARKETS', 1))
    ingest_interval = int(os.environ.get('PITCHER_PROPS_INGEST_INTERVAL', 5))
    calibration_interval = int(os.environ.get('PITCHER_PROPS_CALIBRATION_INTERVAL', 20))
    snapshot_interval = int(os.environ.get('PITCHER_PROPS_SNAPSHOT_INTERVAL', 3))
    sse_burst_limit = int(os.environ.get('PITCHER_PROPS_SSE_MAX_EVENTS', 20))

    start_time = datetime.utcnow()
    last_fetch_time = None
    previous_summary = {}
    previous_lines_snapshot: Dict[str, Dict[str, Dict[str, float]]] = {}
    last_git_push_ts: Optional[float] = None

    def load_line_history_path(date_str: str) -> str:
        # Precompute date tag to keep f-string simple and robust
        tag = date_str.replace('-', '_')
        return os.path.join('data', 'daily_bovada', f"pitcher_prop_line_history_{tag}.json")

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
        try:
            top_keys = list(props_payload.keys()) if isinstance(props_payload, dict) else []
            pcount = len((props_payload.get('pitcher_props') or {})) if isinstance(props_payload, dict) else 0
            if pcount == 0:
                print(f"[PitcherPropsUpdater] Warning: props payload empty for {date_str}. top_keys={top_keys}")
        except Exception:
            pass
        summary = extract_pitcher_market_summary(props_payload)
        # Relay full props snapshot to web so the site can serve latest lines (even without git)
        try:
            if props_payload:
                ok = bridge_send([{'type': 'props_snapshot', 'date': date_str, 'doc': props_payload}])
                if not ok:
                    print("[PitcherPropsUpdater] Bridge relay failed for props_snapshot (check WEB_BASE_URL and PITCHER_SSE_INGEST_TOKEN)")
        except Exception as _e:
            print(f"[PitcherPropsUpdater] Bridge error (props_snapshot): {_e}")

        # Line movement detection (compare each market line & odds)
        line_events = []
        initial_events = []
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
                if changed and prev_mk:  # movement event
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
                elif changed and not prev_mk and new_line is not None:
                    # First time we've seen this market -> broadcast initial snapshot so frontend can display without waiting for movement
                    initial_events.append({
                        'ts': datetime.utcnow().isoformat(),
                        'pitcher': p_key,
                        'market': mk,
                        'line': new_line,
                        'over_odds': new_over,
                        'under_odds': new_under
                    })
                # update snapshot structure staged
                prev_p.setdefault(mk, {})
                prev_p[mk]['line'] = new_line
                prev_p[mk]['over_odds'] = new_over
                prev_p[mk]['under_odds'] = new_under
            previous_lines_snapshot[p_key] = prev_p

        # Persist last-known lines snapshot for fallback rendering (even if Bovada delists later)
        try:
            tag = date_str.replace('-', '_')
            lk_path = os.path.join('data','daily_bovada', f"pitcher_last_known_lines_{tag}.json")
            os.makedirs(os.path.dirname(lk_path), exist_ok=True)
            doc = {
                'date': date_str,
                'updated_at': datetime.utcnow().isoformat(),
                'pitchers': previous_lines_snapshot
            }
            tmp = lk_path + '.tmp'
            with open(tmp, 'w', encoding='utf-8') as f:
                json.dump(doc, f, indent=2)
            os.replace(tmp, lk_path)
        except Exception as _e:
            print(f"[PitcherPropsUpdater] last-known save error: {_e}")
        if initial_events:
            try:
                from app import broadcast_pitcher_update  # type: ignore
                for ev in initial_events:
                    ev['date'] = date_str
                    broadcast_pitcher_update({'type': 'line_initial', **ev})
            except Exception:
                pass
            # Optional relay to web app for persistence if running cross-process
            try:
                ok = bridge_send([{'type':'line_initial', **ev} for ev in initial_events])
                if not ok:
                    print("[PitcherPropsUpdater] Bridge relay failed for line_initial events")
            except Exception as _e:
                print(f"[PitcherPropsUpdater] Bridge error (line_initial): {_e}")
        if line_events:
            append_line_history_events(date_str, line_events)
            # Attempt live broadcast for recent events (non-fatal if unavailable)
            try:
                from app import broadcast_pitcher_update  # type: ignore
                for ev in line_events[-sse_burst_limit:]:  # limit burst configurable
                    ev['date'] = date_str
                    broadcast_pitcher_update({'type': 'line_move', **ev})
            except Exception:
                pass
            # Optional relay to web app for persistence
            try:
                ok = bridge_send([{'type':'line_move', **ev} for ev in line_events[-sse_burst_limit:]])
                if not ok:
                    print("[PitcherPropsUpdater] Bridge relay failed for line_move events")
            except Exception as _e:
                print(f"[PitcherPropsUpdater] Bridge error (line_move): {_e}")
            # Incremental distribution updates for affected pitchers (Phase 2)
            try:
                from pitcher_distributions import update_distributions_for_pitchers  # type: ignore
                changed_pitchers = list({ev['pitcher'] for ev in line_events if ev.get('pitcher')})
                dist_changes = update_distributions_for_pitchers(date_str, changed_pitchers)
                if dist_changes:
                    try:
                        from app import broadcast_pitcher_update  # type: ignore
                        for pk, deltas in dist_changes.items():
                            payload = {'type':'distribution_update','pitcher': pk, 'deltas': deltas, 'date': date_str, 'ts': datetime.utcnow().isoformat()}
                            broadcast_pitcher_update(payload)
                        try:
                            ok = bridge_send([{'type':'distribution_update','pitcher': pk, 'deltas': deltas, 'date': date_str, 'ts': datetime.utcnow().isoformat()} for pk, deltas in dist_changes.items()])
                            if not ok:
                                print("[PitcherPropsUpdater] Bridge relay failed for distribution_update events")
                        except Exception as _e:
                            print(f"[PitcherPropsUpdater] Bridge error (distribution_update): {_e}")
                    except Exception:
                        pass
            except Exception as _e:
                print(f"[PitcherPropsUpdater] Incremental distribution update error: {_e}")
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
                alpha = 0.2  # smoothing factor
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
                # After generation, attempt to send fresh recommendations snapshot to the web
                try:
                    tag = date_str.replace('-', '_')
                    rec_path = os.path.join('data','daily_bovada', f"pitcher_prop_recommendations_{tag}.json")
                    if os.path.exists(rec_path):
                        with open(rec_path,'r',encoding='utf-8') as rf:
                            rec_doc = json.load(rf)
                        ok = bridge_send([{'type': 'recommendations_snapshot', 'date': date_str, 'doc': rec_doc}])
                        if not ok:
                            print("[PitcherPropsUpdater] Bridge relay failed for recommendations_snapshot")
                except Exception:
                    pass
                # Always rebuild full distributions & game synergy after successful generation
                try:
                    from pitcher_distributions import build_and_save_distributions  # type: ignore
                    dist_changed = build_and_save_distributions(date_str)
                    if dist_changed:
                        try:
                            from app import broadcast_pitcher_update  # type: ignore
                            broadcast_pitcher_update({'type': 'distribution_rebuild', 'date': date_str, 'ts': datetime.utcnow().isoformat()})
                        except Exception:
                            pass
                    try:
                        from synergy_game_adjustments import build_game_synergy  # type: ignore
                        build_game_synergy(date_str)
                    except Exception as e2:
                        print(f"[PitcherPropsUpdater] Synergy build error: {e2}")
                except Exception as e2:
                    print(f"[PitcherPropsUpdater] Distribution build error: {e2}")
            except Exception as e:
                print(f"[PitcherPropsUpdater] Secondary generation error: {e}")
                # Build pitcher distributions for synergy layer (best-effort)
                try:
                    from pitcher_distributions import build_and_save_distributions  # type: ignore
                    build_and_save_distributions(date_str)
                    # Build game synergy adjustments (Phase 4) best-effort
                    try:
                        from synergy_game_adjustments import build_game_synergy  # type: ignore
                        build_game_synergy(date_str)
                    except Exception as e2:
                        print(f"[PitcherPropsUpdater] Synergy build error: {e2}")
                except Exception as e:
                    print(f"[PitcherPropsUpdater] Distribution build error: {e}")

            # Optional git commit for remote sync (Render) if enabled
            if AUTO_GIT:
                try:
                    # Rate-limit pushes to at most once per 60 seconds
                    now_ts = time.time()
                    if (last_git_push_ts is None) or ((now_ts - last_git_push_ts) >= 60):
                        # Stage only daily_bovada changes
                        subprocess.run(["git","add","data/daily_bovada"], check=False)
                        # Commit only if there are staged changes
                        commit = subprocess.run(["git","diff","--cached","--quiet"], check=False)
                        if commit.returncode != 0:
                            subprocess.run(["git","commit","-m", f"auto: pitcher props sync {date_str} iter {iteration}"], check=False)
                            subprocess.run(["git","push"], check=False)
                            last_git_push_ts = now_ts
                        else:
                            # Nothing new to commit
                            pass
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
        # Also write a concise shared progress summary file for the site
        try:
            next_sleep = None
            # Estimate next run ETA based on chosen target_sleep below (approx)
            # We'll recompute once target_sleep is decided.
        except Exception:
            next_sleep = None

        progress_summary = {
            'date': date_str,
            'updated_at': progress_doc['timestamp'],
            'iteration': iteration,
            'coverage_percent': round(pct, 1),
            'covered_pitchers': covered,
            'total_pitchers': total,
            'all_games_started': progress_doc['all_games_started'],
            'active_game_count': progress_doc['active_game_count'],
            'last_git_push': datetime.utcfromtimestamp(last_git_push_ts).isoformat() if last_git_push_ts else None
        }
        # Will add next_run_eta below once target_sleep is defined

        previous_summary = summary

        # Periodic ingestion & calibration triggers
        if ingest_interval > 0 and iteration % ingest_interval == 0:
            # Load outcomes locally and also emit to web app for persistence
            before = len(realized_doc.get('pitcher_market_outcomes', []))
            ingest_completed_game_outcomes(date_str)
            after = len(realized_doc.get('pitcher_market_outcomes', []))
            if after > before:
                new_items = [r for r in realized_doc.get('pitcher_market_outcomes', []) if r.get('date') == date_str][-max(0, after-before):]
                try:
                    ok = bridge_send([{'type':'final_outcomes_batch','date': date_str, 'outcomes': new_items}])
                    if not ok:
                        print("[PitcherPropsUpdater] Bridge relay failed for final_outcomes_batch")
                except Exception as _e:
                    print(f"[PitcherPropsUpdater] Bridge error (final_outcomes_batch): {_e}")
        if calibration_interval > 0 and iteration % calibration_interval == 0:
            calibration_pass()
        if snapshot_interval > 0 and iteration % snapshot_interval == 0:
            snapshot_intraday(date_str, iteration, progress_doc)

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

        # finalize next_run_eta and write concise summary
        try:
            eta = datetime.utcnow() + timedelta(seconds=int(target_sleep))
            progress_summary['next_run_eta'] = eta.isoformat()
        except Exception:
            progress_summary['next_run_eta'] = None
        write_progress_summary(progress_summary)

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
