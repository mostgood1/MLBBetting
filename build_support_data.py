"""Build supporting context data for pitcher projections.
Fetches:
  - Team batting stats (k_rate, bb_rate, pitches_per_pa)
  - Recent pitcher form (last 5 starts innings & strikeouts)
  - Park factors (via existing feature_engineering module if available)
Outputs JSON files under data/:
  team_batting_stats.json
  recent_pitcher_stats.json
  park_factors.json

Uses MLB Stats API (public) for fresh data.
"""
from __future__ import annotations
import os, json, time, math, sys
from datetime import datetime
from typing import Dict, Any, List, Tuple
import requests

DATA_DIR = 'data'
SEASON = os.environ.get('MLB_SEASON') or str(datetime.utcnow().year)
MLB_API = 'https://statsapi.mlb.com/api/v1'
HEADERS = {'User-Agent': 'MLB-Analytics-Tool/1.0'}

def _ensure_dir():
    os.makedirs(DATA_DIR, exist_ok=True)

def fetch_team_hitting_stats(season: str) -> Dict[str, Any]:
    url = f"{MLB_API}/teams/stats?group=hitting&season={season}&sportIds=1"
    try:
        r = requests.get(url, headers=HEADERS, timeout=25)
        r.raise_for_status()
        data = r.json()
    except Exception as e:
        print(f"[team_hitting] ERROR fetch failed: {e}")
        return {}
    out: Dict[str, Any] = {}
    try:
        splits = data.get('stats',[{}])[0].get('splits', [])
        for sp in splits:
            team = sp.get('team',{}).get('name')
            stat = sp.get('stat',{})
            if not team or not stat: continue
            pa = _safe_float(stat.get('plateAppearances'))
            so = _safe_float(stat.get('strikeOuts'))
            bb = _safe_float(stat.get('baseOnBalls'))
            pppa = _safe_float(stat.get('pitchesPerPlateAppearance'))  # sometimes string
            if pa and pa > 0:
                k_rate = so/pa if so is not None else None
                bb_rate = bb/pa if bb is not None else None
            else:
                k_rate = bb_rate = None
            out[team] = {
                'k_rate': round(k_rate,4) if k_rate is not None else None,
                'bb_rate': round(bb_rate,4) if bb_rate is not None else None,
                'pitches_per_pa': round(pppa,3) if pppa is not None else None,
                'plate_appearances': int(pa) if pa is not None else None
            }
    except Exception as e:
        print(f"[team_hitting] ERROR parse: {e}")
    return out

def _safe_float(v):
    try:
        if v is None: return None
        if isinstance(v,(int,float)): return float(v)
        s=str(v).strip()
        if s=='' or s.lower()=='null': return None
        return float(s)
    except Exception:
        return None

def load_master_pitcher_stats() -> Dict[str, Any]:
    path = os.path.join(DATA_DIR,'master_pitcher_stats.json')
    if not os.path.exists(path):
        return {}
    try:
        with open(path,'r') as f:
            data=json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}

def fetch_recent_pitcher_form(pitcher_ids: List[str], season: str, last_n: int = 5, id_to_name: Dict[str,str] | None = None) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    for i,pid in enumerate(pitcher_ids):
        url = f"{MLB_API}/people/{pid}/stats?stats=gameLog&group=pitching&season={season}"
        try:
            r = requests.get(url, headers=HEADERS, timeout=20)
            if r.status_code != 200:
                continue
            data = r.json()
        except Exception:
            continue
        splits = data.get('stats',[{}])[0].get('splits', [])
        # Keep only starts (gamesStarted=="1")
        starts = []
        for sp in splits:
            stat = sp.get('stat',{})
            if stat.get('gamesStarted') in ('1',1):
                starts.append(stat)
        # last N chronological - splits appear oldest first usually; sort by date
        def _date(stat):
            return stat.get('gameDate') or stat.get('date') or ''
        starts.sort(key=_date)
        recent = starts[-last_n:]
        if not recent:
            continue
        innings_total = 0.0
        so_total = 0
        for st in recent:
            ip_raw = st.get('inningsPitched')
            innings_total += _parse_ip(ip_raw)
            try:
                so_total += int(st.get('strikeOuts') or 0)
            except Exception:
                pass
        gs = len(recent)
        name = recent[-1].get('player','') or recent[-1].get('playerFullName','') or ''
        if (not name) and id_to_name:
            name = id_to_name.get(str(pid), '')
        out[str(pid)] = {
            'pitcher_name': name,
            'last5_games_started': gs,
            'last5_innings': round(innings_total,1),
            'last5_strikeouts': so_total
        }
        # soft rate limit
        time.sleep(0.15)
    return out

def _parse_ip(ip_str):
    if ip_str is None: return 0.0
    if isinstance(ip_str,(int,float)): return float(ip_str)
    s=str(ip_str).strip()
    if s=='' or s.lower()=='null': return 0.0
    # MLB innings format: 5.2 means 5 and 2/3
    try:
        if '.' in s:
            whole, frac = s.split('.',1)
            outs = int(frac)
            if outs in (0,1,2):
                return int(whole) + outs/3.0
        return float(s)
    except Exception:
        return 0.0

def _today_date_tokens():
    dt = datetime.utcnow()
    return dt.strftime('%Y_%m_%d')

def load_starting_pitcher_names() -> List[str]:
    date_us = _today_date_tokens()
    candidates = [
        os.path.join(DATA_DIR, f'starting_pitchers_{date_us}.json'),
        os.path.join(DATA_DIR, f'today_pitchers_{date_us}.json'),
        '_today_games.json'
    ]
    names: List[str] = []
    for fp in candidates:
        if not os.path.exists(fp):
            continue
        try:
            with open(fp,'r') as f:
                data = json.load(f)
        except Exception:
            continue
        if isinstance(data, dict) and 'games' in data:
            for g in data['games']:
                for k in ['away_pitcher','home_pitcher','away_probable_pitcher','home_probable_pitcher']:
                    v = g.get(k)
                    if v and v not in names:
                        names.append(v)
        elif isinstance(data, list):
            # list of games objects
            for g in data:
                for k in ['away_pitcher','home_pitcher']:
                    v = g.get(k)
                    if v and v not in names:
                        names.append(v)
    return names

def extract_pitcher_ids_for_today(master_stats: Dict[str, Any], starter_names: List[str]) -> List[str]:
    """Resolve probable starter MLB IDs.

    Strategy:
      1. Direct name -> id match from master_pitcher_stats.json
      2. If not found, query MLB Stats API people/search endpoint (cached) to locate id
      3. Fallback to small sample (first 40) so recent file not empty
    """
    name_to_id = {}
    for pid, info in master_stats.items():
        nm = (info.get('name') or '').lower()
        if nm and pid:
            name_to_id[nm] = pid

    resolved: List[str] = []
    unresolved: List[str] = []

    cache_path = os.path.join(DATA_DIR, 'mlb_people_cache.json')
    people_cache: Dict[str, Dict[str,str]] = {}
    if os.path.exists(cache_path):
        try:
            with open(cache_path,'r') as cf:
                people_cache = json.load(cf) or {}
        except Exception:
            people_cache = {}

    cache_dirty = False

    # Simple rate limiting/backoff state
    last_req = {'t': 0.0}
    backoff = {'delay': 0.0}

    def _norm(n: str) -> str:
        try:
            import unicodedata, re
            n2 = ''.join(c for c in unicodedata.normalize('NFD', n) if unicodedata.category(c) != 'Mn').lower()
            n2 = n2.replace('φ','i')
            n2 = re.sub(r'\s+',' ', n2).strip()
            # align with aliases used in pitcher_projections
            alias_map = {
                'luis garcia':'luis garcia',
                'luis garc i a':'luis garcia'
            }
            return alias_map.get(n2, n2)
        except Exception:
            return n.lower()

    def search_mlb_people(name: str) -> Tuple[str,str] | None:
        # Returns (id, fullName) or None
        q = name.replace(' ','%20')
        key = name.lower()
        if key in people_cache:
            rec = people_cache[key]
            pid = rec.get('id'); full = rec.get('fullName')
            if pid and full:
                return (pid, full)
        # basic pacing: at least 0.1s between calls + additive backoff on failures
        import time as _t
        now = _t.time()
        min_gap = 0.1 + backoff['delay']
        wait = min_gap - (now - last_req['t'])
        if wait > 0:
            _t.sleep(wait)
        url = f"{MLB_API}/people/search?names={q}"
        try:
            r = requests.get(url, headers=HEADERS, timeout=12)
            if r.status_code != 200:
                backoff['delay'] = min(1.5, backoff['delay'] + 0.15)
                return None
            data = r.json()
            backoff['delay'] = max(0.0, backoff['delay'] * 0.6)  # decay
        except Exception:
            backoff['delay'] = min(1.5, backoff['delay'] + 0.2)
            return None
        last_req['t'] = _t.time()
        try:
            people = data.get('people') or []
            # pick first pitcher match
            for p in people:
                pos = (p.get('primaryPosition') or {}).get('code')
                full = p.get('fullName')
                pid = p.get('id')
                if pos == '1' and pid and full:
                    people_cache[key] = {'id': str(pid), 'fullName': full}
                    cache_dirty = True  # type: ignore
                    return (str(pid), full)
            if people:
                p0 = people[0]
                if p0.get('id') and p0.get('fullName'):
                    people_cache[key] = {'id': str(p0['id']), 'fullName': p0['fullName']}
                    cache_dirty = True  # type: ignore
                    return (str(p0['id']), p0['fullName'])
        except Exception:
            return None
        return None

    for nm in starter_names:
        key = nm.lower()
        pid = name_to_id.get(key)
        if pid:
            if pid not in resolved:
                resolved.append(pid)
            continue
        # attempt MLB search
        found = search_mlb_people(nm)
        if found:
            pid_found, full = found
            if pid_found not in resolved:
                resolved.append(pid_found)
                # augment name_to_id for subsequent duplicates
                name_to_id[_norm(full)] = pid_found
        else:
            unresolved.append(nm)

    if not resolved:
        resolved = list(master_stats.keys())[:40]
    if unresolved:
        print(f"[pitcher_ids] Unresolved starters (no id match): {len(unresolved)} -> {unresolved[:6]}")
    print(f"[pitcher_ids] Resolved starter IDs: {len(resolved)}")
    if cache_dirty:
        try:
            with open(cache_path,'w') as cf:
                json.dump(people_cache, cf, indent=2)
            print(f"[people_cache] Updated cache entries: {len(people_cache)}")
        except Exception as e:
            print(f"[people_cache] WARN write failed: {e}")
    return resolved

def build_park_factors() -> Dict[str, float]:
    """Return normalized park factor mapping usable by projections.

    feature_engineering.AdvancedFeatureEngineer uses shortened keys (e.g. 'Braves').
    We'll output both the raw keys and expanded 'Atlanta Braves' style where we can.
    """
    try:
        import feature_engineering  # type: ignore
        if hasattr(feature_engineering, 'AdvancedFeatureEngineer'):
            afe = feature_engineering.AdvancedFeatureEngineer(DATA_DIR)
            afe._add_ballpark_factors()
            factors = getattr(afe, 'ballpark_factors', {})
        else:
            factors = {}
    except Exception as e:
        print(f"[park_factors] WARN fallback init: {e}")
        factors = {}
    if not isinstance(factors, dict) or not factors:
        return {}

    # Mapping from nickname to full team name used in schedule data
    nickname_to_full = {
        'Angels': 'Los Angeles Angels',
        'Astros': 'Houston Astros',
        'Athletics': 'Oakland Athletics',
        'Blue_Jays': 'Toronto Blue Jays',
        'Braves': 'Atlanta Braves',
        'Brewers': 'Milwaukee Brewers',
        'Cardinals': 'St. Louis Cardinals',
        'Cubs': 'Chicago Cubs',
        'Diamondbacks': 'Arizona Diamondbacks',
        'Dodgers': 'Los Angeles Dodgers',
        'Giants': 'San Francisco Giants',
        'Guardians': 'Cleveland Guardians',
        'Mariners': 'Seattle Mariners',
        'Marlins': 'Miami Marlins',
        'Mets': 'New York Mets',
        'Nationals': 'Washington Nationals',
        'Orioles': 'Baltimore Orioles',
        'Padres': 'San Diego Padres',
        'Phillies': 'Philadelphia Phillies',
        'Pirates': 'Pittsburgh Pirates',
        'Rangers': 'Texas Rangers',
        'Rays': 'Tampa Bay Rays',
        'Red_Sox': 'Boston Red Sox',
        'Reds': 'Cincinnati Reds',
        'Rockies': 'Colorado Rockies',
        'Royals': 'Kansas City Royals',
        'Tigers': 'Detroit Tigers',
        'Twins': 'Minnesota Twins',
        'White_Sox': 'Chicago White Sox',
        'Yankees': 'New York Yankees'
    }
    cleaned: Dict[str,float] = {}
    for k,v in factors.items():
        try:
            fv = float(v)
        except Exception:
            continue
        cleaned[k] = round(fv,3)
        full = nickname_to_full.get(k)
        if full:
            cleaned[full] = round(fv,3)
    print(f"[park_factors] Prepared {len(cleaned)} keys (raw + expanded)")
    return cleaned


def main():
    _ensure_dir()
    print(f"Building support data for season {SEASON} ...")
    # Team batting
    team_stats = fetch_team_hitting_stats(SEASON)
    with open(os.path.join(DATA_DIR,'team_batting_stats.json'),'w') as f:
        json.dump(team_stats, f, indent=2)
    print(f"Team batting stats saved: {len(team_stats)} teams")

    # Master pitchers and today starters
    master = load_master_pitcher_stats()
    starters = load_starting_pitcher_names()
    pitcher_ids = extract_pitcher_ids_for_today(master, starters)
    # Build id->name map for better naming fallback
    id_to_name = {pid: info.get('name','') for pid,info in master.items() if isinstance(info, dict)}
    recent_form = fetch_recent_pitcher_form(pitcher_ids, SEASON, id_to_name=id_to_name)
    # Map by pitcher name for projections (we store both id key and name key)
    recent_by_name = {}
    for pid, rec in recent_form.items():
        nm = rec.get('pitcher_name')
        if not nm:
            continue
        # unify duplicate names keep the one with greater innings
        existing = recent_by_name.get(nm)
        if existing:
            if rec['last5_innings'] <= existing['last5_innings']:
                continue
        recent_by_name[nm] = {
            'last5_games_started': rec['last5_games_started'],
            'last5_innings': rec['last5_innings'],
            'last5_strikeouts': rec['last5_strikeouts']
        }
    with open(os.path.join(DATA_DIR,'recent_pitcher_stats.json'),'w') as f:
        json.dump(recent_by_name, f, indent=2)
    print(f"Recent pitcher stats saved: {len(recent_by_name)} pitchers")

    park = build_park_factors()
    if park:
        with open(os.path.join(DATA_DIR,'park_factors.json'),'w') as f:
            json.dump(park, f, indent=2)
        print(f"Park factors saved: {len(park)} parks")
    else:
        print("Park factors unavailable (feature_engineering fallback empty).")

    print("Done.")

if __name__ == '__main__':
    main()
