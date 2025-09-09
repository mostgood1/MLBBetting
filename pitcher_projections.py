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

def load_team_batting_k_rates() -> Dict[str, float]:
    """Load team batting strikeout rate (K%) if available.
    Expected file: data/team_batting_stats.json with structure like:
      {
         "Atlanta Braves": {"k_rate": 0.211},
         "New York Yankees": {"k_rate": 0.225},
         ...
      }
    k_rate may also appear as 'k_percent' (e.g. 21.1 meaning 21.1%).
    Returns mapping normalized_team_name -> k_rate (decimal fraction).
    """
    path = os.path.join(DATA_DIR, 'team_batting_stats.json')
    if not os.path.exists(path):
        return {}
    try:
        with open(path,'r') as f:
            raw = json.load(f)
        out = {}
        if isinstance(raw, dict):
            for team, vals in raw.items():
                if not isinstance(vals, dict):
                    continue
                kr = vals.get('k_rate')
                if kr is None:
                    # maybe percent form
                    kr = vals.get('k_percent')
                    if isinstance(kr,(int,float)) and kr > 1.5:  # assume percent like 21.3
                        kr = kr / 100.0
                if isinstance(kr,(int,float)) and 0 < kr < 1:
                    out[normalize_name(team)] = float(kr)
        return out
    except Exception:
        return {}

def load_team_patience_stats() -> Dict[str, Dict[str, float]]:
    """Load team plate discipline (pitches_per_pa, bb_rate) from team_batting_stats.json if present."""
    path = os.path.join(DATA_DIR, 'team_batting_stats.json')
    if not os.path.exists(path):
        return {}
    try:
        with open(path,'r') as f:
            raw = json.load(f)
        out: Dict[str, Dict[str,float]] = {}
        if isinstance(raw, dict):
            for team, vals in raw.items():
                if not isinstance(vals, dict):
                    continue
                ppa = vals.get('pitches_per_pa') or vals.get('pitches_per_plate_appearance')
                bb = vals.get('bb_rate') or vals.get('walk_rate') or vals.get('bb_percent')
                if isinstance(bb,(int,float)) and bb > 1.5:
                    bb = bb/100.0
                rec: Dict[str,float] = {}
                if isinstance(ppa,(int,float)) and ppa>2:
                    rec['pitches_per_pa'] = float(ppa)
                if isinstance(bb,(int,float)) and 0 < bb < 0.3:
                    rec['bb_rate'] = float(bb)
                if rec:
                    out[normalize_name(team)] = rec
        return out
    except Exception:
        return {}

def load_recent_pitcher_stats() -> Dict[str, Dict[str, float]]:
    """Load recent pitcher form stats from recent_pitcher_stats.json if present."""
    path = os.path.join(DATA_DIR, 'recent_pitcher_stats.json')
    if not os.path.exists(path):
        return {}
    try:
        with open(path,'r') as f:
            raw = json.load(f)
        out: Dict[str, Dict[str,float]] = {}
        if isinstance(raw, dict):
            for name, vals in raw.items():
                if not isinstance(vals, dict):
                    continue
                fixed_name = name.replace('φ','í')  # repair common corruption
                out[normalize_name(fixed_name)] = vals
        # If any corrupted forms existed, optionally persist a cleaned file (non-fatal)
        try:
            cleaned_keys_original = set(raw.keys()) if isinstance(raw, dict) else set()
            cleaned_keys_new = set(out.keys())
            if cleaned_keys_original and cleaned_keys_new and cleaned_keys_original != cleaned_keys_new:
                repair_path = os.path.join(DATA_DIR, 'recent_pitcher_stats_cleaned.json')
                with open(repair_path,'w') as cf:
                    json.dump({k: out[k] for k in cleaned_keys_new}, cf, indent=2)
        except Exception:
            pass
        return out
    except Exception:
        return {}

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
    """Build index pitcher_name -> list of (game, side).

    Handles multiple potential key variants and nested structures.
    Expected primary keys in game objects (from `_today_games.json`):
      away_pitcher, home_pitcher, away_team, home_team
    Fallback nested: pitcher_info.away_pitcher_name, pitcher_info.home_pitcher_name
    """
    idx: Dict[str, List[tuple[Dict[str,Any], str]]] = {}
    for g in games:
        # Primary extraction
        away_pitcher = g.get('away_pitcher') or g.get('pitcher_info',{}).get('away_pitcher_name')
        home_pitcher = g.get('home_pitcher') or g.get('pitcher_info',{}).get('home_pitcher_name')
        # Some data may store probable labels
        if not away_pitcher:
            away_pitcher = g.get('away_probable_pitcher')
        if not home_pitcher:
            home_pitcher = g.get('home_probable_pitcher')
        if away_pitcher:
            idx.setdefault(normalize_name(away_pitcher), []).append((g, 'away'))
        if home_pitcher:
            idx.setdefault(normalize_name(home_pitcher), []).append((g, 'home'))
    return idx

_BOVADA_CACHE: dict[str, Any] = {}
_BOVADA_CACHE_EXPIRY: float = 0.0
_RECENT_ON_DEMAND_CACHE: dict[str, dict[str, float]] = {}

# Common manual name aliases (mismatched spellings between sources)
NAME_ALIASES = {
    'zack littell': 'zach littell',
    'zac littell': 'zach littell',
    'german marquez': 'germán márquez',
    'yoendrys gomez': 'yoendrys gómez',
    # Common accent simplifications & corrupted forms
    'luis garcia': 'luis garcía',
    'luis garcφa': 'luis garcía',
    'martin perez': 'martín pérez',
    'martin pérez': 'martín pérez',
    'martín perez': 'martín pérez',
    'jesus luzardo': 'jesús luzardo',
    'jose soriano': 'josé soriano',
}

def normalize_name(name: str) -> str:
    """Full normalization pipeline: lower, strip accents, collapse spaces, apply alias."""
    if not name:
        return ''
    # Replace known stray characters before accent strip (e.g., Greek phi in corrupted feeds)
    trans_table = str.maketrans({
        'φ': 'i',  # corrupted 'í'
    })
    name = name.translate(trans_table)
    base = _strip_accents(name).lower().strip()
    base = re.sub(r'\s+', ' ', base)
    # apply alias mapping on accent-stripped version
    if base in NAME_ALIASES:
        return _strip_accents(NAME_ALIASES[base]).lower()
    return base

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
        pkey = normalize_name(pitcher)
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
                                props.setdefault(normalize_name(pitcher_name), {}).setdefault('strikeouts_alts', alt_ladder)
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
            detail_blocks = detail if isinstance(detail, list) else [detail]
            for blk in detail_blocks:
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
                                is_over = ' over ' in f' {o_desc} ' or o_desc.startswith('over ')
                                is_under = ' under ' in f' {o_desc} ' or o_desc.startswith('under ')
                                # If both not present treat as neutral listing (store only line w/ odds sign meaning Over maybe)
                                norm_player = normalize_name(player_name) if player_name else None
                                if norm_player and norm_player not in props:
                                    # Need counterpart outcome to fill both over/under; accumulate temp store
                                    entry = props.setdefault(norm_player, {})
                                    stat_entry = entry.setdefault(stat_key, {'line': line_val, 'over_odds': None, 'under_odds': None})
                                    if line_val is not None and stat_entry['line'] is None:
                                        stat_entry['line'] = line_val
                                    if is_over and stat_entry['over_odds'] is None and american:
                                        try: stat_entry['over_odds'] = int(american)
                                        except Exception: pass
                                    if is_under and stat_entry['under_odds'] is None and american:
                                        try: stat_entry['under_odds'] = int(american)
                                        except Exception: pass
                                elif norm_player:
                                    # Merge into existing
                                    stat_entry = props[norm_player].setdefault(stat_key, {'line': line_val, 'over_odds': None, 'under_odds': None})
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
        norm = normalize_name(nm)
        if norm:
            name_lookup[norm] = (pid, info)

    games = load_today_games()
    pitcher_game_index = _index_games_by_pitcher(games)

    # Build team->opponent map from games for cross-reference validation
    team_opponent_map: Dict[str, str] = {}
    for g in games:
        at = g.get('away_team') or g.get('awayTeam')
        ht = g.get('home_team') or g.get('homeTeam')
        if at and ht:
            team_opponent_map[normalize_name(at)] = ht
            team_opponent_map[normalize_name(ht)] = at

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
        if gp not in pitcher_names and normalize_name(gp) in line_map:
            pitcher_names.append(gp)

    # Track unmatched for logging
    unmatched_starters = []
    for nm in pitcher_names:
        if normalize_name(nm) not in line_map:
            unmatched_starters.append(nm)
    extra_props = [orig for orig in line_map.keys() if orig not in [normalize_name(p) for p in pitcher_names]]
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

    # Attempt to load park factors (optional)
    park_factors = {}
    pf_path = os.path.join(DATA_DIR, 'park_factors.json')
    if os.path.exists(pf_path):
        try:
            with open(pf_path,'r') as f:
                pf_data = json.load(f)
            if isinstance(pf_data, dict):
                park_factors = {normalize_name(k): float(v) for k,v in pf_data.items() if isinstance(v,(int,float,str)) and str(v).replace('.','',1).replace('-','').isdigit()}
        except Exception:
            park_factors = {}

    batting_k_rates = load_team_batting_k_rates()
    patience_stats = load_team_patience_stats()
    recent_pitcher_stats = load_recent_pitcher_stats()
    league_avg_k_factor = 1.0
    if batting_k_rates:
        try:
            vals = [v for v in batting_k_rates.values() if 0 < v < 1]
            if vals:
                league_avg_k_factor = sum(vals)/len(vals)
        except Exception:
            pass

    recent_used = 0
    recent_on_demand_used = 0
    synthetic_recent_count = 0
    patience_used = 0
    # Track missing adjustment inputs for audit
    missing_inputs = {
        'opponent': [],
        'park_factor': [],
        'opponent_k_rate': [],
        'patience_stats': [],
        'recent_form': []
    }
    # Helper: on-demand recent form fetch (uses MLB Stats API game logs)
    def _fetch_recent_form_for_pitcher(name: str) -> Optional[Dict[str, float]]:
        norm = normalize_name(name)
        if norm in _RECENT_ON_DEMAND_CACHE:
            return _RECENT_ON_DEMAND_CACHE[norm]
        # People search
        q = requests.utils.quote(name)
        try:
            resp = requests.get(f'https://statsapi.mlb.com/api/v1/people/search?names={q}', timeout=10)
            if resp.status_code != 200:
                return None
            pdata = resp.json()
            people = pdata.get('people') or []
            pid = None
            for p in people:
                pos = (p.get('primaryPosition') or {}).get('code')
                if pos == '1':  # pitcher
                    pid = p.get('id')
                    break
            if not pid and people:
                pid = people[0].get('id')
            if not pid:
                return None
            # game log
            gl = requests.get(f'https://statsapi.mlb.com/api/v1/people/{pid}/stats?stats=gameLog&group=pitching', timeout=12)
            if gl.status_code != 200:
                return None
            gdata = gl.json()
            splits = gdata.get('stats',[{}])[0].get('splits', [])
            starts = []
            for sp in splits:
                st = sp.get('stat',{})
                if st.get('gamesStarted') in ('1',1):
                    starts.append(st)
            def _d(st):
                return st.get('gameDate') or st.get('date') or ''
            starts.sort(key=_d)
            recent = starts[-5:]
            if not recent:
                return None
            innings_total = 0.0
            so_total = 0
            for st in recent:
                ip = st.get('inningsPitched')
                # reuse logic from build script: parse ip like 5.2 -> 5.6667
                conv = 0.0
                if ip is not None:
                    try:
                        s = str(ip)
                        if '.' in s:
                            whole, frac = s.split('.',1)
                            outs = int(frac)
                            if outs in (0,1,2):
                                conv = int(whole) + outs/3.0
                            else:
                                conv = float(s)
                        else:
                            conv = float(s)
                    except Exception:
                        conv = 0.0
                innings_total += conv
                try:
                    so_total += int(st.get('strikeOuts') or 0)
                except Exception:
                    pass
            rec = {
                'last5_games_started': len(recent),
                'last5_innings': round(innings_total,1),
                'last5_strikeouts': so_total
            }
            _RECENT_ON_DEMAND_CACHE[norm] = rec
            return rec
        except Exception:
            return None

    # Limit number of on-demand API calls per run
    on_demand_calls_allowed = 5
    for pname in pitcher_names:
        key = normalize_name(pname)
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
        recent_stats = recent_pitcher_stats.get(key)
        weighted_ip = None
        recent_ip_per_start = None
        if recent_stats and isinstance(recent_stats, dict):
            last_gs = recent_stats.get('last5_games_started') or recent_stats.get('last5_gs')
            last_ip = recent_stats.get('last5_innings') or recent_stats.get('last5_ip')
            if isinstance(last_gs,(int,float)) and last_gs and isinstance(last_ip,(int,float)) and last_ip>0:
                try:
                    recent_ip_per_start = last_ip / max(1.0, last_gs)
                    if last_gs >= 3:
                        weighted_ip = 0.6*avg_ip + 0.4*recent_ip_per_start
                        recent_used += 1
                except Exception:
                    pass
        else:
            # Attempt on-demand fetch if limit not exceeded
            if on_demand_calls_allowed > 0:
                fetched = _fetch_recent_form_for_pitcher(pname)
                if fetched:
                    recent_stats = fetched
                    last_gs = fetched.get('last5_games_started')
                    last_ip = fetched.get('last5_innings')
                    if isinstance(last_gs,(int,float)) and isinstance(last_ip,(int,float)) and last_gs > 0 and last_ip>0:
                        try:
                            recent_ip_per_start = last_ip / max(1.0, last_gs)
                            if last_gs >= 3:
                                weighted_ip = 0.6*avg_ip + 0.4*recent_ip_per_start
                                recent_on_demand_used += 1
                        except Exception:
                            pass
                    on_demand_calls_allowed -= 1
            # If still no stats, synthetic fallback
            if not recent_stats:
                synth_starts = min(5, gs if gs else 0)
                if synth_starts > 0:
                    synth_ip = synth_starts * avg_ip
                    synth_ks = round(k_per_ip * synth_ip)
                    recent_stats = {
                        'last5_games_started': synth_starts,
                        'last5_innings': round(synth_ip,1),
                        'last5_strikeouts': synth_ks,
                        'synthetic': True
                    }
                    synthetic_recent_count += 1
                    # Use weighting if enough synthetic starts
                    if synth_starts >= 3:
                        recent_ip_per_start = synth_ip / synth_starts
                        weighted_ip = 0.6*avg_ip + 0.4*recent_ip_per_start
        base_ip_for_proj = weighted_ip if weighted_ip else avg_ip
        projected_ip = max(3.0, min(8.1, base_ip_for_proj))
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
            home_team = g.get('home_team') or g.get('homeTeam')
            away_team = g.get('away_team') or g.get('awayTeam')
            if side == 'away':
                opponent = home_team
            else:
                opponent = away_team
            venue = home_team
        # fallback: attempt to infer from team field if opponent still None
        if (not opponent) and stats.get('team'):
            pteam = stats.get('team')
            # scan games list once (could optimize with pre-index but small list OK)
            for g in games:
                at = g.get('away_team') or g.get('awayTeam')
                ht = g.get('home_team') or g.get('homeTeam')
                if at == pteam:
                    opponent = ht
                    venue = ht
                    break
                if ht == pteam:
                    opponent = at
                    venue = ht
                    break

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

        # Adjustments (opponent K rate & park) - placeholders if data unavailable
        park_factor = None
        if venue:
            vkey = normalize_name(venue)
            park_factor = park_factors.get(vkey)
            if park_factor is None:
                # try last word (nickname) heuristic e.g. "Atlanta Braves" -> "braves"
                parts = vkey.split()
                if parts:
                    park_factor = park_factors.get(parts[-1])
        opp_k_rate = None
        if opponent:
            opp_k_rate = batting_k_rates.get(normalize_name(opponent))
        k_factor = 1.0
        if opp_k_rate and league_avg_k_factor:
            try:
                k_factor *= (opp_k_rate / league_avg_k_factor)
            except Exception:
                pass
        if park_factor and isinstance(park_factor,(int,float)):
            # assume >1 favors hitters (reduce Ks slightly), <1 favors pitchers (increase Ks)
            try:
                k_factor *= (1 - ((park_factor - 1) * 0.5))
            except Exception:
                pass
        # Patience-based outs factor
        outs_factor = 1.0
        if opponent:
            ps = patience_stats.get(normalize_name(opponent))
            if ps:
                ppa = ps.get('pitches_per_pa')
                bb_rate = ps.get('bb_rate')
                try:
                    ppa_vals = [v.get('pitches_per_pa') for v in patience_stats.values() if isinstance(v.get('pitches_per_pa'), (int,float))]
                    bb_vals = [v.get('bb_rate') for v in patience_stats.values() if isinstance(v.get('bb_rate'), (int,float))]
                    league_ppa = sum(ppa_vals)/len(ppa_vals) if ppa_vals else None
                    league_bb = sum(bb_vals)/len(bb_vals) if bb_vals else None
                except Exception:
                    league_ppa = league_bb = None
                patience_index = 1.0
                comps = []
                if ppa and league_ppa:
                    comps.append((ppa/league_ppa, 0.6))
                if bb_rate and league_bb and league_bb>0:
                    comps.append((bb_rate/league_bb, 0.4))
                if comps:
                    try:
                        patience_index = sum(v*w for v,w in comps) / sum(w for _,w in comps)
                        outs_factor = max(0.85, min(1.10, 1 - (patience_index-1)*0.18))
                        patience_used += 1
                    except Exception:
                        pass
        adjusted_ks = round(projected_ks * k_factor, 1)
        adjusted_outs = round(projected_outs * outs_factor)

        # Record missing inputs
        pname_out = stats.get('name', pname)
        if opponent is None:
            missing_inputs['opponent'].append(pname_out)
        if park_factor is None:
            missing_inputs['park_factor'].append(pname_out)
        if opponent is not None and opp_k_rate is None:
            missing_inputs['opponent_k_rate'].append(pname_out)
        if opponent is not None and patience_stats and outs_factor == 1.0:
            missing_inputs['patience_stats'].append(pname_out)
        if recent_stats is None:
            missing_inputs['recent_form'].append(pname_out)

        # Edge diffs (projection - line)
        diffs = {
            'outs': projected_outs - line_outs if line_outs is not None else None,
            'strikeouts': projected_ks - line_ks if line_ks is not None else None,
            'earned_runs': projected_er - line_er if line_er is not None else None,
            'hits_allowed': projected_hits - line_hits if line_hits is not None else None,
            'walks': projected_walks - line_walks if line_walks is not None else None,
        }
        diffs_adjusted = {
            'outs': adjusted_outs - line_outs if line_outs is not None else None,
            'strikeouts': adjusted_ks - line_ks if line_ks is not None else None,
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
            'adjusted_projections': {
                'strikeouts': adjusted_ks,
                'outs': adjusted_outs,
                'k_factor': round(k_factor,3),
                'park_factor_used': park_factor,
                'opponent_k_rate': opp_k_rate,
                'league_avg_k_rate': league_avg_k_factor if batting_k_rates else None,
                'outs_factor': outs_factor if outs_factor != 1.0 else None,
                'recent_ip_weighted': round(weighted_ip,2) if weighted_ip else None,
                'recent_ip_per_start': round(recent_ip_per_start,2) if recent_ip_per_start else None,
            },
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
            'diffs': diffs,
            'diffs_adjusted': diffs_adjusted
        })
    # end for pitchers loop
    result = {
        'date': date_iso,
        'generated_at': datetime.utcnow().isoformat(),
        'pitchers': projections,
        'count': len(projections),
        'notes': 'Season averages baseline + opponent K-rate, park factor, patience (outs), recent form weighted IP when data available.',
        'unmatched_starting_pitchers': unmatched_starting_pitchers,
        'props_without_start_flag': props_without_start_flag,
        'adjustment_meta': {
            'recent_form_pitchers_used': recent_used,
            'patience_adjustments_used': patience_used,
            'total_pitchers': len(pitcher_names),
            'park_factors_count': len(park_factors),
            'batting_k_rates_count': len(batting_k_rates),
            'patience_teams_count': len(patience_stats),
            'recent_pitchers_count': len(recent_pitcher_stats),
            'park_factor_example_keys': list(park_factors.keys())[:8],
            'missing_counts': {k: len(v) for k,v in missing_inputs.items()},
            'recent_form_on_demand_used': recent_on_demand_used,
            'synthetic_recent_form_count': synthetic_recent_count
        }
    }
    # Cross-reference opponent correctness using team_opponent_map
    opponent_corrections = []
    if team_opponent_map:
        for p in result['pitchers']:
            team_nm = p.get('team')
            if not team_nm:
                continue
            mapped_opp = team_opponent_map.get(normalize_name(team_nm))
            if not mapped_opp:
                continue
            current_opp = p.get('opponent')
            # If opponent missing or mismatched, correct it
            if (not current_opp) or (current_opp != mapped_opp):
                p['opponent_corrected_from'] = current_opp
                p['opponent'] = mapped_opp
                p['opponent_corrected'] = True
                opponent_corrections.append({
                    'pitcher_id': p.get('pitcher_id'),
                    'pitcher_name': p.get('pitcher_name'),
                    'team': team_nm,
                    'old_opponent': current_opp,
                    'new_opponent': mapped_opp
                })
    if opponent_corrections:
        result['opponent_corrections'] = opponent_corrections
        result['adjustment_meta']['opponent_corrections_count'] = len(opponent_corrections)
    else:
        result['adjustment_meta']['opponent_corrections_count'] = 0
    # Add truncated lists (first 12 names) for quick inspection
    result['adjustment_gaps'] = {k: v[:12] for k,v in missing_inputs.items()}
    # Persist enriched features snapshot (non-fatal on failure)
    try:
        out_dir = os.path.join(DATA_DIR, 'daily_bovada')
        os.makedirs(out_dir, exist_ok=True)
        with open(os.path.join(out_dir, f'projection_features_{date_us}.json'),'w') as f:
            json.dump(result, f, indent=2)
        # concise summary file
        summary = {
            'date': date_iso,
            'generated_at': result['generated_at'],
            'counts': result['adjustment_meta'],
            'missing_sample': result['adjustment_gaps']
        }
        with open(os.path.join(out_dir, f'adjustment_summary_{date_us}.json'),'w') as f:
            json.dump(summary, f, indent=2)
    except Exception:
        pass
    return result

if __name__ == '__main__':
    import pprint
    pprint.pprint(compute_pitcher_projections())
