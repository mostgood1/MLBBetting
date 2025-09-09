"""Pitcher projections module.
Generates simple projected stats for today's starting pitchers using season averages.
Independent utility used by /api/pitcher-projections and /pitcher-projections page.
"""
from __future__ import annotations
import os, json
from datetime import datetime
from typing import List, Dict, Any

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

def compute_pitcher_projections() -> Dict[str, Any]:
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
        # derive base metrics
        if not stats:
            # no stats -> skip (avoid misleading projection)
            continue
        ip = float(stats.get('innings_pitched', 0) or 0)
        gs = int(stats.get('games_started', 0) or 0)
        era = float(stats.get('era', 0) or 0)
        whip = float(stats.get('whip', 0) or 0)
        so = int(stats.get('strikeouts', stats.get('strikeOuts', 0) or 0))
        bb = int(stats.get('walks', stats.get('baseOnBalls', 0) or 0))
        avg_ip = ip/gs if gs>0 else 5.0
        # clamp to plausible range
        projected_ip = max(3.0, min(8.0, avg_ip))
        projected_outs = round(projected_ip * 3)
        k_per_ip = (so/ip) if ip>0 else 0.9  # fallback typical
        projected_ks = round(k_per_ip * projected_ip, 1)
        projected_er = round((era * projected_ip / 9.0), 1) if era>0 else 2.5
        # estimate hits from WHIP (assume 60% hits of WHIP baserunners) and subtract walks component
        bb_per_ip = (bb/ip) if ip>0 else 0.3
        baserunners_per_ip = whip if whip>0 else (bb_per_ip + 0.6)
        hits_per_ip_est = max(0.0, baserunners_per_ip - bb_per_ip)
        projected_hits = round(hits_per_ip_est * projected_ip, 1)

        # opponent + game context
        opponent = None
        venue = None
        game_keys = pitcher_game_index.get(key, [])
        if game_keys:
            g, side = game_keys[0]
            opponent = g.get('home_team') if side=='away' else g.get('away_team')
            venue = g.get('home_team')

        # simple confidence tiers
        reliability = 'LOW'
        if gs >= 10 and ip >= 50:
            reliability = 'HIGH'
        elif gs >= 5:
            reliability = 'MEDIUM'

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
                'outs': None,
                'strikeouts': None,
                'earned_runs': None,
                'hits_allowed': None
            },
            'recommendations': {
                'outs': None,
                'strikeouts': None,
                'earned_runs': None,
                'hits_allowed': None
            }
        })

    return {
        'date': date_iso,
        'generated_at': datetime.utcnow().isoformat(),
        'pitchers': projections,
        'count': len(projections),
        'notes': 'Projections derived from season averages; lines not integrated yet.'
    }

if __name__ == '__main__':
    import pprint
    pprint.pprint(compute_pitcher_projections())
