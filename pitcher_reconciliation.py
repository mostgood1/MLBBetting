import os
import json
import time
import unicodedata
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

import requests

DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')


def normalize_name(s: str) -> str:
    if not s:
        return ''
    s = unicodedata.normalize('NFKD', s)
    s = ''.join(c for c in s if not unicodedata.combining(c))
    return ''.join(ch for ch in s.lower() if ch.isalnum())


def ip_to_outs(ip_val: Any) -> Optional[int]:
    if ip_val is None:
        return None
    try:
        s = str(ip_val)
        if '.' in s:
            whole, frac = s.split('.', 1)
            outs = int(frac)
            outs = outs if outs in (0, 1, 2) else 0
            return int(whole) * 3 + outs
        return int(float(s) * 3)
    except Exception:
        return None


def _read_json(path: str) -> Optional[Any]:
    try:
        if os.path.exists(path):
            with open(path, 'r') as f:
                return json.load(f)
    except Exception:
        return None
    return None


def _write_json(path: str, data: Any):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w') as f:
        json.dump(data, f, indent=2)


def _load_games_with_ids(date_iso: str) -> List[Dict[str, Any]]:
    # Prefer local games file if it carries gamePk
    local_path = os.path.join(DATA_DIR, f'games_{date_iso}.json')
    games = []
    gj = _read_json(local_path)
    if isinstance(gj, list):
        games = gj
    elif isinstance(gj, dict) and 'games' in gj:
        games = gj.get('games') or []

    # Ensure gamePk present; if missing for most entries, fetch via MLB schedule
    if not games or not any('gamePk' in g for g in games):
        try:
            r = requests.get(f'https://statsapi.mlb.com/api/v1/schedule?sportId=1&date={date_iso}', timeout=12)
            if r.status_code == 200:
                sj = r.json()
                for d in sj.get('dates', []):
                    for g in d.get('games', []):
                        games.append({
                            'gamePk': g.get('gamePk'),
                            'away_team': ((g.get('teams', {}).get('away', {}) or {}).get('team', {}) or {}).get('name'),
                            'home_team': ((g.get('teams', {}).get('home', {}) or {}).get('team', {}) or {}).get('name'),
                            'game_datetime': g.get('gameDate')
                        })
        except Exception:
            pass
    return games


def _load_expected_starters(date_iso: str) -> Dict[str, str]:
    # Map normalized pitcher name -> team
    starters_path = os.path.join(DATA_DIR, f'starting_pitchers_{date_iso.replace("-","_")}.json')
    starters = {}
    sj = _read_json(starters_path)
    if isinstance(sj, list):
        for g in sj:
            for k in ['away_pitcher', 'home_pitcher']:
                nm = g.get(k)
                if nm:
                    side = 'away' if 'away' in k else 'home'
                    team = g.get(f'{side}_team') or g.get(f'{"away" if side=="home" else "home"}_team')
                    starters[normalize_name(nm)] = team
    return starters


def _extract_pitchers_from_box(box: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    pitchers = {}
    for side in ['home', 'away']:
        team = box.get('teams', {}).get(side, {})
        players = team.get('players', {})
        for pid, pdata in players.items():
            info = pdata.get('person', {})
            stats = pdata.get('stats', {}).get('pitching') or {}
            if not stats:
                continue
            name = info.get('fullName') or info.get('boxscoreName')
            if not name:
                continue
            pitchers[normalize_name(name)] = {
                'name': name,
                'team_side': side,
                'ip': stats.get('inningsPitched'),
                'so': stats.get('strikeOuts'),
                'er': stats.get('earnedRuns'),
                'h': stats.get('hits'),
                'bb': stats.get('baseOnBalls')
            }
    return pitchers


def fetch_pitcher_actuals(date_iso: str, live: bool = False) -> Dict[str, Any]:
    """Fetch actual pitcher results for a date. If live=True, query live feeds regardless of cache."""
    out_dir = os.path.join(DATA_DIR, 'daily_results')
    out_path = os.path.join(out_dir, f'pitcher_results_{date_iso.replace("-","_")}.json')
    if not live:
        cached = _read_json(out_path)
        if cached and isinstance(cached.get('pitchers'), list):
            return cached

    games = _load_games_with_ids(date_iso)
    results: Dict[str, Dict[str, Any]] = {}
    for g in games:
        gpk = g.get('gamePk')
        if not gpk:
            continue
        try:
            r = requests.get(f'https://statsapi.mlb.com/api/v1/game/{gpk}/boxscore', timeout=12)
            if r.status_code != 200:
                continue
            box = r.json()
            ps = _extract_pitchers_from_box(box)
            for key, p in ps.items():
                if key not in results:
                    results[key] = {
                        'name': p['name'],
                        'ip': p['ip'],
                        'outs': ip_to_outs(p['ip']),
                        'strikeouts': p['so'],
                        'earned_runs': p['er'],
                        'hits_allowed': p['h'],
                        'walks': p['bb']
                    }
                else:
                    # Combine across appearances (doubleheaders, relief etc.)
                    prev = results[key]
                    prev['outs'] = (prev.get('outs') or 0) + (ip_to_outs(p['ip']) or 0)
                    prev['strikeouts'] = (prev.get('strikeouts') or 0) + int(p['so'] or 0)
                    prev['earned_runs'] = (prev.get('earned_runs') or 0) + int(p['er'] or 0)
                    prev['hits_allowed'] = (prev.get('hits_allowed') or 0) + int(p['h'] or 0)
                    prev['walks'] = (prev.get('walks') or 0) + int(p['bb'] or 0)
        except Exception:
            continue

    payload = {
        'date': date_iso,
        'generated_at': datetime.utcnow().isoformat(),
        'pitchers': list(results.values()),
        'count': len(results)
    }
    # Save snapshot (even if live, helps caching between calls)
    _write_json(out_path, payload)
    return payload


def load_projections_snapshot(date_iso: str) -> Optional[Dict[str, Any]]:
    ppath = os.path.join(DATA_DIR, 'daily_bovada', f'pitcher_projections_{date_iso.replace("-","_")}.json')
    return _read_json(ppath)


def reconcile_projections(date_iso: str, live: bool = False) -> Dict[str, Any]:
    """Join projections snapshot with actual stats and compute errors."""
    proj = load_projections_snapshot(date_iso)
    if not proj:
        # Attempt to compute today's snapshot if date == local (US/Eastern) today
        try:
            from zoneinfo import ZoneInfo
            today_local = datetime.now(ZoneInfo('America/New_York')).strftime('%Y-%m-%d')
        except Exception:
            today_local = datetime.now().strftime('%Y-%m-%d')
        if date_iso == today_local:
            try:
                from pitcher_projections import compute_pitcher_projections
                proj = compute_pitcher_projections(include_lines=True, force_refresh=False)
            except Exception:
                proj = None
    actuals = fetch_pitcher_actuals(date_iso, live=live)
    proj_map = {}
    if proj:
        for p in proj.get('pitchers', []):
            proj_map[normalize_name(p.get('pitcher_name'))] = p
    rows = []
    for a in actuals.get('pitchers', []):
        key = normalize_name(a.get('name'))
        p = proj_map.get(key)
        row = {
            'pitcher_name': a.get('name'),
            'team': (p or {}).get('team'),
            'opponent': (p or {}).get('opponent'),
            'proj': {
                'outs': (p or {}).get('projected_outs'),
                'k': (p or {}).get('projected_strikeouts'),
                'er': (p or {}).get('projected_earned_runs'),
                'h': (p or {}).get('projected_hits_allowed'),
                'bb': (p or {}).get('projected_walks'),
            },
            'adj': {
                'outs': ((p or {}).get('adjusted_projections') or {}).get('outs'),
                'k': ((p or {}).get('adjusted_projections') or {}).get('strikeouts'),
            },
            'act': {
                'outs': a.get('outs'),
                'k': a.get('strikeouts'),
                'er': a.get('earned_runs'),
                'h': a.get('hits_allowed'),
                'bb': a.get('walks'),
            }
        }
        # Errors
        row['err'] = {
            'outs': _safe_diff(row['act']['outs'], row['proj']['outs']),
            'outs_adj': _safe_diff(row['act']['outs'], row['adj']['outs']),
            'k': _safe_diff(row['act']['k'], row['proj']['k']),
            'k_adj': _safe_diff(row['act']['k'], row['adj']['k']),
            'er': _safe_diff(row['act']['er'], row['proj']['er']),
            'h': _safe_diff(row['act']['h'], row['proj']['h']),
            'bb': _safe_diff(row['act']['bb'], row['proj']['bb'])
        }
        rows.append(row)
    rows.sort(key=lambda r: (r['pitcher_name'] or ''))
    return {
        'success': True,
        'date': date_iso,
        'generated_at': datetime.utcnow().isoformat(),
        'count': len(rows),
        'rows': rows
    }


def _safe_diff(a: Optional[float], b: Optional[float]) -> Optional[float]:
    try:
        if a is None or b is None:
            return None
        return float(a) - float(b)
    except Exception:
        return None
