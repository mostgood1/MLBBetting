"""Augment historical pitcher prop dataset with actual outcomes (Ks, outs).

Uses final_scores_YYYY_MM_DD.json to discover game_pks, then fetches box scores
from MLB Stats API to extract starting pitcher strikeouts and innings pitched.

Adds / updates columns:
  actual_strikeouts
  actual_outs
  outcome_source (boxscore|missing)

Only updates rows where these fields are empty.
Run daily (ideally next morning) before modeling.
"""
from __future__ import annotations
import os, csv, json, re, time
from typing import Dict, Any, List
import requests

DATA_DIR = 'data'
CSV_PATH = os.path.join(DATA_DIR, 'model_datasets', 'pitcher_props_history.csv')
HEADERS = {'User-Agent': 'MLB-Analytics-Tool/1.0'}
MLB_API = 'https://statsapi.mlb.com/api/v1'

BOX_SCORE_CACHE: Dict[int, Dict[str, Any]] = {}
CACHE_PATH = os.path.join(DATA_DIR, 'boxscore_cache.json')

if os.path.exists(CACHE_PATH):
    try:
        with open(CACHE_PATH,'r') as f:
            BOX_SCORE_CACHE = json.load(f) or {}
    except Exception:
        BOX_SCORE_CACHE = {}

def _parse_ip(ip_str):
    if ip_str is None: return 0.0
    if isinstance(ip_str,(int,float)): return float(ip_str)
    s=str(ip_str).strip()
    if s=='': return 0.0
    try:
        if '.' in s:
            whole, frac = s.split('.',1)
            outs = int(frac)
            if outs in (0,1,2):
                return int(whole) + outs/3.0
        return float(s)
    except Exception:
        return 0.0

FINAL_SCORE_PATTERN = re.compile(r'final_scores_(20\d{2}_\d{2}_\d{2})\.json$')

def _list_final_score_files():
    for fname in os.listdir(DATA_DIR):
        m = FINAL_SCORE_PATTERN.match(fname)
        if m:
            yield fname, m.group(1)

def _date_from_token(tok: str) -> str:
    # 2025_09_05 -> 2025-09-05
    return f"{tok[0:4]}-{tok[5:7]}-{tok[8:10]}"

def _load_box_score(game_pk: int) -> Dict[str, Any] | None:
    if str(game_pk) in BOX_SCORE_CACHE:
        return BOX_SCORE_CACHE[str(game_pk)]
    url = f"{MLB_API}/game/{game_pk}/boxscore"
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        if r.status_code != 200:
            return None
        data = r.json()
        BOX_SCORE_CACHE[str(game_pk)] = data
        # persist occasionally
        if len(BOX_SCORE_CACHE) % 25 == 0:
            try:
                with open(CACHE_PATH,'w') as cf:
                    json.dump(BOX_SCORE_CACHE, cf)
            except Exception:
                pass
        time.sleep(0.12)
        return data
    except Exception:
        return None

def _extract_starting_pitchers(box: Dict[str, Any]) -> List[Dict[str, Any]]:
    starters = []
    try:
        teams = [box['teams']['away'], box['teams']['home']]
        for t in teams:
            pitchers = t.get('players', {})
            for pid_key, pdata in pitchers.items():
                stats = pdata.get('stats', {}).get('pitching', {})
                if not stats:
                    continue
                # Identify starters: gamesStarted==1 OR outs recorded very early & batters faced etc.
                gs = stats.get('gamesStarted') in (1, '1')
                if gs:
                    person = pdata.get('person', {})
                    starters.append({
                        'pitcher_id': str(person.get('id')),
                        'pitcher_name': person.get('fullName'),
                        'strikeouts': stats.get('strikeOuts'),
                        'innings_pitched': stats.get('inningsPitched'),
                    })
    except Exception:
        return starters
    return starters

def update_outcomes():
    if not os.path.exists(CSV_PATH):
        print('Dataset CSV not found; nothing to update.')
        return

    # Read existing rows
    with open(CSV_PATH,'r',newline='') as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        fieldnames = list(reader.fieldnames or [])

    # Ensure columns
    added_cols = []
    for col in ['actual_strikeouts','actual_outs','outcome_source']:
        if col not in fieldnames:
            fieldnames.append(col)
            added_cols.append(col)

    # Build index date->pitcher rows needing outcome
    need_dates: Dict[str, List[int]] = {}
    for idx, row in enumerate(rows):
        if not row.get('date') or not row.get('pitcher_id'):
            continue
        if row.get('actual_strikeouts') or row.get('actual_outs'):
            continue
        # skip today's date (incomplete games)
        if row['date'] == time.strftime('%Y-%m-%d'):
            continue
        need_dates.setdefault(row['date'], []).append(idx)

    if not need_dates:
        print('No rows need outcomes.')
        return

    # Map available final score files
    final_files = { _date_from_token(tok): fname for fname, tok in _list_final_score_files() }

    updated = 0
    for date, indices in need_dates.items():
        token = date.replace('-','_')
        fname = final_files.get(date)
        if not fname:
            continue
        path = os.path.join(DATA_DIR, fname)
        try:
            with open(path,'r') as f:
                finals = json.load(f)
        except Exception:
            continue
        # Collect all game_pks
        game_pks = []
        for v in finals.values():
            if isinstance(v, dict) and v.get('is_final') and 'game_pk' in v:
                game_pks.append(int(v['game_pk']))
        pitcher_outcomes: Dict[str, Dict[str, Any]] = {}
        for gpk in game_pks:
            box = _load_box_score(gpk)
            if not box:
                continue
            for sp in _extract_starting_pitchers(box):
                pid = sp['pitcher_id']
                ks = sp.get('strikeouts')
                ip = sp.get('innings_pitched')
                outs = round(_parse_ip(ip) * 3) if ip is not None else None
                pitcher_outcomes[(pid)] = {
                    'actual_strikeouts': ks,
                    'actual_outs': outs,
                    'outcome_source': 'boxscore'
                }
        # Apply to rows
        for idx in indices:
            pid = rows[idx]['pitcher_id']
            res = pitcher_outcomes.get(pid)
            if not res:
                continue
            for k,v in res.items():
                rows[idx][k] = v
                updated += 1
    # Write back if changes
    if updated:
        tmp = CSV_PATH + '.tmp'
        with open(tmp,'w',newline='') as f:
            w = csv.DictWriter(f, fieldnames=fieldnames)
            w.writeheader()
            for r in rows:
                w.writerow(r)
        os.replace(tmp, CSV_PATH)
        # Persist cache
        try:
            with open(CACHE_PATH,'w') as cf:
                json.dump(BOX_SCORE_CACHE, cf)
        except Exception:
            pass
        print(f'Updated outcome fields for {updated} values.')
    else:
        print('No outcomes updated.')

if __name__ == '__main__':
    update_outcomes()
