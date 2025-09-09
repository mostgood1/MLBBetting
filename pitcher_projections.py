"""Pitcher projections module.
Generates simple projected stats for today's starting pitchers using season averages.
Independent utility used by /api/pitcher-projections and /pitcher-projections page.
"""
from __future__ import annotations
import os, json, time, math, re
from datetime import datetime
from typing import List, Dict, Any, Optional
import requests

DATA_DIR = os.path.join('data')

def _today_dates():
    dt = datetime.utcnow()
    return dt.strftime('%Y-%m-%d'), dt.strftime('%Y_%m_%d')

def load_master_pitcher_stats() -> Dict[str, Dict[str, Any]]:
    path = os.path.join(DATA_DIR, 'master_pitcher_stats.json')
    if not os.path.exists(path):
        return {}
    try:
        with open(path,'r') as f:
            data = json.load(f)
        # data keyed by pitcher_id -> stats
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}

def load_starting_pitchers(date_us: str) -> List[Dict[str, Any]]:
    # Primary pattern used elsewhere in repo appears to be starting_pitchers_YYYY_MM_DD.json
    candidate_files = [
        os.path.join(DATA_DIR, f'starting_pitchers_{date_us}.json'),
        os.path.join(DATA_DIR, f'today_pitchers_{date_us}.json'),  # from fast_pitcher_updater
    ]
    for fp in candidate_files:
        if os.path.exists(fp):
            try:
                with open(fp,'r') as f:
                    data = json.load(f)
                # support either {"games": [...]} or direct dict mapping
                if isinstance(data, dict):
                    if 'games' in data and isinstance(data['games'], list):
                        return data['games']
                    # fast updater structure is mapping id->stats (not game list) - skip
            except Exception:
                pass
    return []

def load_today_games() -> List[Dict[str, Any]]:
    # There is a root _today_games.json in repo snapshot.
    for name in ['_today_games.json','today_games.json']:
        if os.path.exists(name):
            try:
                with open(name,'r') as f:
                    data = json.load(f)
                if isinstance(data, dict):
                    # guess structure
                    if 'games' in data and isinstance(data['games'], list):
                        return data['games']
                if isinstance(data, list):
                    return data
            except Exception:
                pass
    return []

def _index_games_by_pitcher(games: List[Dict[str, Any]]):
    idx = {}
    for g in games:
        away_pitcher = g.get('away_pitcher') or g.get('pitcher_info',{}).get('away_pitcher_name')
        home_pitcher = g.get('home_pitcher') or g.get('pitcher_info',{}).get('home_pitcher_name')
        if away_pitcher:
            idx.setdefault(away_pitcher.lower(), []).append((g,'away'))
        if home_pitcher:
            idx.setdefault(home_pitcher.lower(), []).append((g,'home'))
    return idx

_BOVADA_CACHE: dict[str, Any] = {}
_BOVADA_CACHE_EXPIRY: float = 0.0

def fetch_bovada_pitcher_props(ttl_seconds: int = 300) -> Dict[str, Dict[str, Any]]:
    """Fetch pitcher prop lines from Bovada (public API) with light caching.

    Returns mapping: pitcher_name_lower -> { 'strikeouts': { 'line': float, 'over_odds': int, 'under_odds': int }, ... }
    Supported keys we try to extract: strikeouts, outs, earned_runs, hits_allowed.
    Network/parse failures return an empty dict.
    """
    global _BOVADA_CACHE, _BOVADA_CACHE_EXPIRY
    now = time.time()
    if now < _BOVADA_CACHE_EXPIRY and _BOVADA_CACHE:
        return _BOVADA_CACHE

    endpoints = [
        # Main MLB events endpoint (contains displayGroups with player props)
        "https://www.bovada.lv/services/sports/event/v2/events/A/description/baseball/mlb"
    ]
    props: Dict[str, Dict[str, Any]] = {}
    try:
        for url in endpoints:
            try:
                resp = requests.get(url, timeout=12)
                if resp.status_code != 200:
                    continue
                data = resp.json()
            except Exception:
                continue
            # Data structure: list[ { 'events': [ { 'displayGroups': [ { 'markets': [...] } ] } ] } ]
            if not isinstance(data, list):
                continue
            for block in data:
                for event in block.get('events', []):
                    display_groups = event.get('displayGroups', []) or []
                    for dg in display_groups:
                        markets = dg.get('markets', []) or []
                        for m in markets:
                            desc = (m.get('description') or '').lower()
                            # Identify market type
                            stat_key: Optional[str] = None
                            if 'strikeouts' in desc:
                                stat_key = 'strikeouts'
                            elif 'outs recorded' in desc or 'pitcher outs' in desc:
                                stat_key = 'outs'
                            elif 'earned runs' in desc:
                                stat_key = 'earned_runs'
                            elif 'hits allowed' in desc or ('hits' in desc and 'allowed' in desc):
                                stat_key = 'hits_allowed'
                            if not stat_key:
                                continue
                            outcomes = m.get('outcomes', []) or []
                            # We expect two outcomes: Over / Under
                            over_o = None; under_o = None; line_val = None
                            for o in outcomes:
                                o_desc = (o.get('description') or '').lower()
                                price = o.get('price', {})
                                american = price.get('american')
                                # Line can be inside price['handicap'] OR outcome['line'] style fields
                                handicap = price.get('handicap') or o.get('line') or o.get('handicap')
                                try:
                                    if handicap is not None and line_val is None:
                                        line_val = float(handicap)
                                except Exception:
                                    pass
                                if 'over' in o_desc:
                                    over_o = american
                                elif 'under' in o_desc:
                                    under_o = american
                            # Extract pitcher name from market description (pattern: "Player Name - Strikeouts")
                            # Heuristic: split on ' - ' and take first part if has space and no keyword like 'total'
                            raw_name_part = None
                            if ' - ' in m.get('description',''):
                                raw_name_part = m['description'].split(' - ')[0].strip()
                            # Fallback: remove stat phrase
                            if not raw_name_part:
                                raw_name_part = re.sub(r'(strikeouts|outs recorded|earned runs|hits allowed).*','', m.get('description',''), flags=re.I).strip()
                            # Basic validation: letters and space
                            if raw_name_part and len(raw_name_part.split()) <= 4 and re.search(r'[a-zA-Z]', raw_name_part):
                                pkey = raw_name_part.lower()
                                entry = props.setdefault(pkey, {})
                                if stat_key not in entry:
                                    entry[stat_key] = {
                                        'line': line_val,
                                        'over_odds': int(over_o) if over_o and str(over_o).lstrip('+-').isdigit() else None,
                                        'under_odds': int(under_o) if under_o and str(under_o).lstrip('+-').isdigit() else None
                                    }
        _BOVADA_CACHE = props
        _BOVADA_CACHE_EXPIRY = now + ttl_seconds
        return props
    except Exception:
        return {}

def _edge_recommendation(stat: str, proj: float, line: Optional[float]) -> Optional[str]:
    if line is None or proj is None:
        return None
    # Thresholds
    if stat == 'strikeouts':
        diff = proj - line
        if diff >= 0.7: return 'OVER'
        if diff <= -0.7: return 'UNDER'
    elif stat == 'outs':
        diff = proj - line
        if diff >= 2: return 'OVER'
        if diff <= -2: return 'UNDER'
    elif stat == 'earned_runs':
        diff = line - proj  # lower better
        if diff >= 0.6: return 'UNDER'
        if diff <= -0.6: return 'OVER'
    elif stat == 'hits_allowed':
        diff = line - proj
        if diff >= 0.8: return 'UNDER'
        if diff <= -0.8: return 'OVER'
    return None

def compute_pitcher_projections(include_lines: bool = True) -> Dict[str, Any]:
    date_iso, date_us = _today_dates()
    master_stats = load_master_pitcher_stats()
    # build name lookup from master stats
    name_lookup = { (info.get('name','').lower()): (pid, info) for pid, info in master_stats.items() }

    games = load_today_games()
    pitcher_game_index = _index_games_by_pitcher(games)

    starting_pitcher_games = load_starting_pitchers(date_us)
    # fallback: derive from games if starting pitcher file missing
    derived_pitchers = []
    if not starting_pitcher_games and games:
        for g in games:
            for role,pname in [('away', g.get('away_pitcher')),('home', g.get('home_pitcher'))]:
                if pname and pname not in derived_pitchers:
                    derived_pitchers.append(pname)

    pitcher_names: List[str] = []
    if starting_pitcher_games:
        for g in starting_pitcher_games:
            for k in ['away_pitcher','home_pitcher','away_probable_pitcher','home_probable_pitcher']:
                v = g.get(k)
                if v and v not in pitcher_names:
                    pitcher_names.append(v)
    else:
        pitcher_names = derived_pitchers

    projections = []
    line_map = fetch_bovada_pitcher_props() if include_lines else {}

    for pname in pitcher_names:
        key = pname.lower()
        pid = None
        stats = None
        # try direct match
        if key in name_lookup:
            pid, stats = name_lookup[key]
        else:
            # loose match ignoring punctuation
            nk = key.replace('.','').replace('-',' ')
            for n2,(pid2,info2) in name_lookup.items():
                n2k = n2.replace('.','').replace('-',' ')
                if nk == n2k:
                    pid, stats = pid2, info2
                    break
        if not stats:
            continue

        ip = float(stats.get('innings_pitched', 0) or 0)
        gs = int(stats.get('games_started', 0) or 0)
        era = float(stats.get('era', 0) or 0)
        whip = float(stats.get('whip', 0) or 0)
        so = int(stats.get('strikeouts', stats.get('strikeOuts', 0) or 0))
        bb = int(stats.get('walks', stats.get('baseOnBalls', 0) or 0))
        avg_ip = ip/gs if gs>0 else 5.0
        projected_ip = max(3.0, min(8.0, avg_ip))
        projected_outs = round(projected_ip * 3)
        k_per_ip = (so/ip) if ip>0 else 0.9
        projected_ks = round(k_per_ip * projected_ip, 1)
        projected_er = round((era * projected_ip / 9.0), 1) if era>0 else 2.5
        bb_per_ip = (bb/ip) if ip>0 else 0.3
        baserunners_per_ip = whip if whip>0 else (bb_per_ip + 0.6)
        hits_per_ip_est = max(0.0, baserunners_per_ip - bb_per_ip)
        projected_hits = round(hits_per_ip_est * projected_ip, 1)

        opponent = None
        venue = None
        game_keys = pitcher_game_index.get(key, [])
        if game_keys:
            g, side = game_keys[0]
            opponent = g.get('home_team') if side=='away' else g.get('away_team')
            venue = g.get('home_team')

        reliability = 'LOW'
        if gs >= 10 and ip >= 50:
            reliability = 'HIGH'
        elif gs >= 5:
            reliability = 'MEDIUM'

        p_lines = line_map.get(key, {}) if line_map else {}
        line_outs = p_lines.get('outs', {}).get('line')
        line_ks = p_lines.get('strikeouts', {}).get('line')
        line_er = p_lines.get('earned_runs', {}).get('line')
        line_hits = p_lines.get('hits_allowed', {}).get('line')

        rec_outs = _edge_recommendation('outs', projected_outs, line_outs)
        rec_ks = _edge_recommendation('strikeouts', projected_ks, line_ks)
        rec_er = _edge_recommendation('earned_runs', projected_er, line_er)
        rec_hits = _edge_recommendation('hits_allowed', projected_hits, line_hits)

        projections.append({
            'pitcher_id': pid,
            'pitcher_name': stats.get('name', pname),
            'team': stats.get('team'),
            'opponent': opponent,
            'venue_home_team': venue,
            'projected_outs': projected_outs,
            'projected_innings': round(projected_ip,1),
            'projected_strikeouts': projected_ks,
            'projected_earned_runs': projected_er,
            'projected_hits_allowed': projected_hits,
            'confidence': reliability,
            'lines': {
                'outs': line_outs,
                'strikeouts': line_ks,
                'earned_runs': line_er,
                'hits_allowed': line_hits
            },
            'recommendations': {
                'outs': rec_outs,
                'strikeouts': rec_ks,
                'earned_runs': rec_er,
                'hits_allowed': rec_hits
            }
        })

    return {
        'date': date_iso,
        'generated_at': datetime.utcnow().isoformat(),
        'pitchers': projections,
        'count': len(projections),
    'notes': 'Projections derived from season averages; Bovada lines integrated when available.'
    }

if __name__ == '__main__':
    import pprint
    pprint.pprint(compute_pitcher_projections())
