"""Pitcher projections module.
Generates simple projected stats for today's starting pitchers using season averages.
Independent utility used by /api/pitcher-projections and /pitcher-projections page.
"""
from __future__ import annotations
import os, json, time, math, re, unicodedata
from datetime import datetime
from typing import List, Dict, Any, Optional
import requests

DATA_DIR = os.path.join('data')

def _today_dates():
    dt = datetime.utcnow()
    return dt.strftime('%Y-%m-%d'), dt.strftime('%Y_%m_%d')

def _strip_accents(s: str) -> str:
    try:
        return ''.join(c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn')
    except Exception:
        return s

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

def fetch_bovada_pitcher_props(ttl_seconds: int = 300, pitcher_names: Optional[List[str]] = None) -> Dict[str, Dict[str, Any]]:
    """Fetch pitcher prop lines from Bovada with broader endpoint coverage & parsing.

    Strategy:
      1. Try multiple endpoint variants (language, marketGroup).
      2. Add desktop User-Agent (Bovada sometimes filters).
      3. Parse all displayGroups/markets; robust name & stat extraction.
      4. Cache in-memory for ttl_seconds.
      5. Optional debug via env PITCHER_PROPS_DEBUG=1.
    Returns mapping pitcher_name_lower -> { stat: { line, over_odds, under_odds } }
    """
    global _BOVADA_CACHE, _BOVADA_CACHE_EXPIRY
    now = time.time()
    if now < _BOVADA_CACHE_EXPIRY and _BOVADA_CACHE:
        return _BOVADA_CACHE

    debug = os.environ.get('PITCHER_PROPS_DEBUG') == '1'
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0 Safari/537.36',
        'Accept': 'application/json,text/plain,*/*'
    }
    # Candidate endpoints (some may 404 silently; we ignore failures)
    endpoints = [
        'https://www.bovada.lv/services/sports/event/v2/events/A/description/baseball/mlb?lang=en',
        'https://www.bovada.lv/services/sports/event/v2/events/A/description/baseball/mlb?marketGroup=player-props',
        'https://www.bovada.lv/services/sports/event/v2/events/A/description/baseball/mlb?preMatchOnly=true',
        # base fallback
        'https://www.bovada.lv/services/sports/event/v2/events/A/description/baseball/mlb'
    ]
    # Add schedule endpoints which sometimes list player prop groups separately
    schedule_endpoints = [
        'https://www.bovada.lv/services/sports/event/v2/events/A/orphans/baseball/mlb',
        'https://www.bovada.lv/services/sports/event/v2/events/A/baseball/mlb'
    ]

    # Regex patterns to identify stat type from description
    stat_patterns: list[tuple[re.Pattern,str]] = [
        (re.compile(r'strikeouts', re.I), 'strikeouts'),
        (re.compile(r'(outs\s*(recorded|\b)|pitcher\s*outs)', re.I), 'outs'),
        (re.compile(r'earned\s*runs', re.I), 'earned_runs'),
        (re.compile(r'hits\s*allowed', re.I), 'hits_allowed'),
        (re.compile(r'(pitcher\s*walks|total\s*walks)', re.I), 'walks'),
    ]

    props: Dict[str, Dict[str, Any]] = {}
    normalized_pitchers = {}
    if pitcher_names:
        for n in pitcher_names:
            ln = n.lower()
            normalized_pitchers[ln] = n
            # Add surname key for fuzzy
            parts = ln.split()
            if len(parts) >= 2:
                normalized_pitchers.setdefault(parts[-1], n)

    def norm_pitcher_name(desc: str) -> Optional[str]:
        if not desc:
            return None
        base = desc
        if ' - ' in desc:
            left, right = desc.split(' - ', 1)
            if re.search(r'(strikeouts|outs|earned runs|hits allowed|pitcher walks|walks)', left, re.I):
                base = right
            else:
                base = left
        base = re.sub(r'\([A-Z]{2,3}\)$','', base).strip()
        base = re.sub(r'(strikeouts|outs recorded|earned runs|hits allowed|pitcher walks|walks)\s*$', '', base, flags=re.I).strip()
        # Filter out generic words
        if not base or len(base.split()) > 4:
            return None
        if not re.search(r'[a-zA-Z]', base):
            return None
        # Fuzzy map if provided
        b_low = base.lower()
        if normalized_pitchers:
            if b_low in normalized_pitchers:
                return normalized_pitchers[b_low]
            # Try surname-only match
            parts = b_low.split()
            if parts:
                last = parts[-1]
                if last in normalized_pitchers:
                    return normalized_pitchers[last]
        return base

    def record_prop(pitcher: str, stat_key: str, line_val, over_o, under_o):
        if pitcher is None or stat_key is None:
            return
        pkey = pitcher.lower()
        entry = props.setdefault(pkey, {})
        # only set if not present (first seen wins)
        if stat_key not in entry:
            entry[stat_key] = {
                'line': line_val if (isinstance(line_val, (int,float))) else None,
                'over_odds': int(over_o) if isinstance(over_o, (int,str)) and str(over_o).lstrip('+-').isdigit() else None,
                'under_odds': int(under_o) if isinstance(under_o, (int,str)) and str(under_o).lstrip('+-').isdigit() else None
            }

    event_ids: set[str] = set()
    for url in endpoints + schedule_endpoints:
        try:
            resp = requests.get(url, headers=headers, timeout=15)
            if resp.status_code != 200:
                continue
            data = resp.json()
        except Exception:
            continue
        if not isinstance(data, list):
            continue
        for block in data:
            for event in block.get('events', []) or []:
                eid = event.get('id') or event.get('eventId')
                if eid:
                    event_ids.add(str(eid))
                dgs = event.get('displayGroups', []) or []
                for dg in dgs:
                    for market in dg.get('markets', []) or []:
                        mdesc_raw = market.get('description') or ''
                        mdesc = mdesc_raw.lower()
                        # Determine stat type via patterns
                        stat_key = None
                        for pat, sk in stat_patterns:
                            if pat.search(mdesc):
                                stat_key = sk
                                break
                        if not stat_key:
                            continue
                        pitcher_name = norm_pitcher_name(mdesc_raw)
                        outcomes = market.get('outcomes', []) or []
                        over_o = under_o = None
                        line_val = None
                        is_alt_strikeouts = 'alternate' in mdesc and stat_key == 'strikeouts'
                        alt_ladder: list[dict[str, Any]] = []
                        for o in outcomes:
                            o_desc = (o.get('description') or '').lower()
                            price = o.get('price') or {}
                            handicap = price.get('handicap') or o.get('line') or o.get('handicap')
                            if line_val is None and handicap is not None:
                                try:
                                    line_val = float(str(handicap).replace('+',''))
                                except Exception:
                                    line_val = None
                            american = price.get('american')
                            if is_alt_strikeouts:
                                m_alt = re.search(r'(\d+)\+\s*strikeouts', o_desc)
                                if m_alt:
                                    try:
                                        alt_ladder.append({'threshold': int(m_alt.group(1)), 'odds': int(american) if american and str(american).lstrip('+-').isdigit() else None})
                                    except Exception:
                                        pass
                            if 'over' in o_desc and over_o is None:
                                over_o = american
                            elif 'under' in o_desc and under_o is None:
                                under_o = american
                        if pitcher_name:
                            record_prop(pitcher_name, stat_key, line_val, over_o, under_o)
                            if is_alt_strikeouts and alt_ladder:
                                props.setdefault(pitcher_name.lower(), {}).setdefault('strikeouts_alts', alt_ladder)
                        # If no pitcher name and this looks like aggregate market, skip for now
    # Deep fetch individual event details for player outcome parsing if we still lack props
    if pitcher_names and len(props) < len(pitcher_names):
        # Limit detail fetches to avoid overload
        detail_fetch_limit = 40
        fetched = 0
        for eid in list(event_ids):
            if fetched >= detail_fetch_limit:
                break
            try:
                detail_url = f'https://www.bovada.lv/services/sports/event/v2/events/A/event/{eid}'
                r = requests.get(detail_url, headers=headers, timeout=12)
                if r.status_code != 200:
                    continue
                detail = r.json()
            except Exception:
                continue
            fetched += 1
            # Structure could be a list with a single block
            blocks = detail if isinstance(detail, list) else [detail]
            for blk in blocks:
                for event in blk.get('events', []) or []:
                    dgs = event.get('displayGroups', []) or []
                    for dg in dgs:
                        for market in dg.get('markets', []) or []:
                            mdesc_raw = market.get('description') or ''
                            mdesc = mdesc_raw.lower()
                            stat_key = None
                            for pat, sk in stat_patterns:
                                if pat.search(mdesc):
                                    stat_key = sk
                                    break
                            if not stat_key:
                                continue
                            outcomes = market.get('outcomes', []) or []
                            # In alternate / aggregate markets, each outcome might contain player + line in description
                            for o in outcomes:
                                o_desc_raw = o.get('description') or ''
                                o_desc = o_desc_raw.lower()
                                # Attempt to extract line and player name
                                price = o.get('price') or {}
                                handicap = price.get('handicap') or o.get('line') or o.get('handicap')
                                try:
                                    line_val = float(str(handicap).replace('+','')) if handicap is not None else None
                                except Exception:
                                    line_val = None
                                # Player name candidate: leading two words before a number or 'over/under'
                                name_match = re.match(r'([A-Za-z`\-\.]+\s+[A-Za-z`\-\.]+)', o_desc_raw)
                                player_name = name_match.group(1) if name_match else None
                                # Improve with normalized list
                                if player_name:
                                    player_name = norm_pitcher_name(player_name)
                                # Determine if this is OVER or UNDER style or a combined listing
                                american = price.get('american')
                                is_over = ' over ' in f' {o_desc} ' or o_desc.startswith('over ')
                                is_under = ' under ' in f' {o_desc} ' or o_desc.startswith('under ')
                                # If both not present treat as neutral listing (store only line w/ odds sign meaning Over maybe)
                                if player_name and player_name.lower() not in props:
                                    # Need counterpart outcome to fill both over/under; accumulate temp store
                                    entry = props.setdefault(player_name.lower(), {})
                                    stat_entry = entry.setdefault(stat_key, {'line': line_val, 'over_odds': None, 'under_odds': None})
                                    if line_val is not None and stat_entry['line'] is None:
                                        stat_entry['line'] = line_val
                                    if is_over and stat_entry['over_odds'] is None and american:
                                        try: stat_entry['over_odds'] = int(american)
                                        except Exception: pass
                                    if is_under and stat_entry['under_odds'] is None and american:
                                        try: stat_entry['under_odds'] = int(american)
                                        except Exception: pass
                                elif player_name:
                                    # Merge into existing
                                    stat_entry = props[player_name.lower()].setdefault(stat_key, {'line': line_val, 'over_odds': None, 'under_odds': None})
                                    if stat_entry['line'] is None and line_val is not None:
                                        stat_entry['line'] = line_val
                                    if is_over and stat_entry['over_odds'] is None and american:
                                        try: stat_entry['over_odds'] = int(american)
                                        except Exception: pass
                                    if is_under and stat_entry['under_odds'] is None and american:
                                        try: stat_entry['under_odds'] = int(american)
                                        except Exception: pass
            # Early exit if we have covered most pitchers
            if pitcher_names and sum(1 for p in pitcher_names if p.lower() in props) >= len(pitcher_names)*0.8:
                break

    _BOVADA_CACHE = props
    _BOVADA_CACHE_EXPIRY = now + ttl_seconds
    # Persist to daily file for audit
    try:
        date_iso, date_us = _today_dates()
        out_dir = os.path.join(DATA_DIR, 'daily_bovada')
        os.makedirs(out_dir, exist_ok=True)
        out_path = os.path.join(out_dir, f'bovada_pitcher_props_{date_us}.json')
        with open(out_path,'w') as f:
            json.dump({'date': date_iso, 'retrieved_at': datetime.utcnow().isoformat(), 'pitcher_props': props}, f, indent=2)
    except Exception:
        pass
    if debug:
        have_stats = {k: list(v.keys()) for k,v in list(props.items())[:5]}
        print(f"[DEBUG] Bovada props fetched pitchers={len(props)} sample={have_stats}")
    return props

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
    name_lookup: Dict[str, tuple[str, Dict[str, Any]]] = {}
    for pid, info in master_stats.items():
        nm = info.get('name','')
        low = nm.lower()
        name_lookup[low] = (pid, info)
        no_acc = _strip_accents(nm).lower()
        if no_acc not in name_lookup:
            name_lookup[no_acc] = (pid, info)

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

    # Remove placeholder / TBD pitchers early
    def _is_placeholder(name: str) -> bool:
        if not name: return True
        nl = name.lower().strip()
        if nl in {'tbd','probable','unknown'}: return True
        if nl.startswith('tbd') or nl.startswith('probable'): return True
        if len(nl) <= 2: return True
        return False

    pitcher_names = [p for p in pitcher_names if not _is_placeholder(p)]

    projections = []
    line_map = fetch_bovada_pitcher_props(pitcher_names=pitcher_names) if include_lines else {}

    # Ensure pitcher list covers all starters in games that have lines
    game_pitchers = []
    for g in games:
        for role in ['away_pitcher','home_pitcher']:
            nm = g.get(role)
            if nm and nm not in game_pitchers:
                game_pitchers.append(nm)
    for gp in game_pitchers:
        if gp not in pitcher_names and gp.lower() in line_map:
            pitcher_names.append(gp)

    # Track unmatched for logging
    unmatched_starters = []
    for nm in pitcher_names:
        if nm.lower() not in line_map:
            unmatched_starters.append(nm)
    extra_props = [orig for orig in line_map.keys() if orig not in [p.lower() for p in pitcher_names]]
    unmatched_starting_pitchers = unmatched_starters  # alias for final output
    props_without_start_flag = extra_props
    try:
        date_iso, date_us = _today_dates()
        out_dir = os.path.join(DATA_DIR, 'daily_bovada')
        os.makedirs(out_dir, exist_ok=True)
        rep_path = os.path.join(out_dir, f'matching_report_{date_us}.json')
        with open(rep_path,'w') as f:
            json.dump({
                'date': date_iso,
                'generated_at': datetime.utcnow().isoformat(),
                'starting_pitchers_count': len(pitcher_names),
                'props_pitchers_count': len(line_map),
                'unmatched_starting_pitchers': unmatched_starters,
                'props_without_start_flag': extra_props
            }, f, indent=2)
    except Exception:
        pass

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
            nk_acc = _strip_accents(nk)
            for n2,(pid2,info2) in name_lookup.items():
                n2k = n2.replace('.','').replace('-',' ')
                if nk == n2k or nk_acc == _strip_accents(n2k):
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
        projected_walks = round(bb_per_ip * projected_ip, 1)

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
        # Access helper
        def _stat_line(stat):
            obj = p_lines.get(stat) or {}
            return obj.get('line')
        line_outs = _stat_line('outs')
        line_ks = _stat_line('strikeouts')
        line_er = _stat_line('earned_runs')
        line_hits = _stat_line('hits_allowed')
        line_walks = _stat_line('walks')

        rec_outs = _edge_recommendation('outs', projected_outs, line_outs)
        rec_ks = _edge_recommendation('strikeouts', projected_ks, line_ks)
        rec_er = _edge_recommendation('earned_runs', projected_er, line_er)
        rec_hits = _edge_recommendation('hits_allowed', projected_hits, line_hits)
        rec_walks = _edge_recommendation('walks', projected_walks, line_walks)

        # Edge diffs (projection - line)
        diffs = {
            'outs': projected_outs - line_outs if line_outs is not None else None,
            'strikeouts': projected_ks - line_ks if line_ks is not None else None,
            'earned_runs': projected_er - line_er if line_er is not None else None,
            'hits_allowed': projected_hits - line_hits if line_hits is not None else None,
            'walks': projected_walks - line_walks if line_walks is not None else None,
        }
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
            'projected_walks': projected_walks,
            'confidence': reliability,
            'lines': {
                'outs': p_lines.get('outs'),
                'strikeouts': p_lines.get('strikeouts'),
                'strikeouts_alts': p_lines.get('strikeouts_alts'),
                'earned_runs': p_lines.get('earned_runs'),
                'hits_allowed': p_lines.get('hits_allowed'),
                'walks': p_lines.get('walks')
            },
            'recommendations': {
                'outs': rec_outs,
                'strikeouts': rec_ks,
                'earned_runs': rec_er,
                'hits_allowed': rec_hits,
                'walks': rec_walks
            },
            'diffs': diffs
        })

    return {
        'date': date_iso,
        'generated_at': datetime.utcnow().isoformat(),
        'pitchers': projections,
        'count': len(projections),
        'notes': 'Projections derived from season averages; Bovada lines integrated when available.',
        'unmatched_starting_pitchers': unmatched_starting_pitchers,
        'props_without_start_flag': props_without_start_flag
    }

if __name__ == '__main__':
    import pprint
    pprint.pprint(compute_pitcher_projections())
