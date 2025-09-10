"""Build a historical dataset for pitcher prop modeling.

Collects per-start features and the corresponding sportsbook closing lines (if available) for:
- Strikeouts (K line)
- Outs / IP (outs line)

Data Sources (existing repository assets expected):
- starting_pitchers_YYYY_MM_DD.json (probables per day)
- master_pitcher_stats.json (season aggregates)
- daily_bovada/bovada_pitcher_props_YYYY_MM_DD.json (captured lines for day)
- team_batting_stats.json (opponent context)
- park_factors.json (park context)

Output:
- data/modeling/pitcher_prop_history.parquet
"""
from __future__ import annotations
import os, json, re, glob, math
from datetime import datetime
from typing import Dict, Any, List

import csv

DATA_DIR = 'data'
DAILY_BOVADA_DIR = os.path.join(DATA_DIR, 'daily_bovada')
OUT_DIR = os.path.join(DATA_DIR, 'modeling')
os.makedirs(OUT_DIR, exist_ok=True)

# Lightweight parquet fallback via csv (parquet optional later)
OUT_CSV = os.path.join(OUT_DIR, 'pitcher_prop_history.csv')

# Normalization reuse (simple version)
import unicodedata

def _strip_accents(s: str) -> str:
    try:
        return ''.join(c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn')
    except Exception:
        return s

def normalize_name(name: str) -> str:
    if not name: return ''
    base = _strip_accents(name).lower().strip()
    base = re.sub(r'\s+',' ', base)
    return base


def _iter_starting_pitcher_files() -> List[str]:
    pattern = os.path.join(DATA_DIR, 'starting_pitchers_20*.json')
    return sorted(glob.glob(pattern))


def load_team_batting():
    path = os.path.join(DATA_DIR,'team_batting_stats.json')
    if not os.path.exists(path):
        return {}
    try:
        with open(path,'r') as f: return json.load(f)
    except Exception: return {}


def load_park_factors():
    path = os.path.join(DATA_DIR,'park_factors.json')
    if not os.path.exists(path): return {}
    try:
        with open(path,'r') as f: return json.load(f)
    except Exception: return {}


def load_bovada_props_by_date(date_us: str):
    path = os.path.join(DAILY_BOVADA_DIR, f'bovada_pitcher_props_{date_us}.json')
    if not os.path.exists(path): return {}
    try:
        with open(path,'r') as f: data = json.load(f)
        return data.get('pitcher_props',{})
    except Exception:
        return {}


def extract_game_pitchers(start_file: str) -> List[Dict[str, Any]]:
    try:
        with open(start_file,'r') as f: raw = json.load(f)
    except Exception:
        return []
    games = raw.get('games') if isinstance(raw, dict) else None
    if not games: return []
    date = raw.get('date') or os.path.basename(start_file).replace('starting_pitchers_','').replace('.json','')
    pitchers: List[Dict[str,Any]] = []
    for g in games:
        away = g.get('away_pitcher') or g.get('away_probable_pitcher')
        home = g.get('home_pitcher') or g.get('home_probable_pitcher')
        away_team = g.get('away_team')
        home_team = g.get('home_team')
        if away:
            pitchers.append({'date': date, 'pitcher_name': away, 'team': away_team, 'opponent': home_team, 'is_home': 0})
        if home:
            pitchers.append({'date': date, 'pitcher_name': home, 'team': home_team, 'opponent': away_team, 'is_home': 1})
    return pitchers


def load_master_stats():
    path = os.path.join(DATA_DIR,'master_pitcher_stats.json')
    if not os.path.exists(path): return {}
    try:
        with open(path,'r') as f: return json.load(f)
    except Exception: return {}


def build():
    team_batting = load_team_batting()
    park_factors = load_park_factors()
    master = load_master_stats()
    rows: List[List[Any]] = []
    header = [
        'date','pitcher_name','team','opponent','is_home',
        'k_line','outs_line',
        'season_ip','season_gs','season_so','season_bb','season_era','season_whip',
        'team_k_rate','opponent_k_rate','park_factor'
    ]
    if not os.path.exists(OUT_CSV):
        with open(OUT_CSV,'w',newline='') as f:
            csv.writer(f).writerow(header)

    start_files = _iter_starting_pitcher_files()
    for sf in start_files:
        date_token = os.path.basename(sf).split('starting_pitchers_')[-1].replace('.json','')
        date_iso = date_token.replace('_','-')
        props = load_bovada_props_by_date(date_token)
        pitchers = extract_game_pitchers(sf)
        for p in pitchers:
            norm_name = normalize_name(p['pitcher_name'])
            # lines
            k_line = None; outs_line = None
            prop_entry = props.get(norm_name) or {}
            if 'strikeouts' in prop_entry:
                k_line = prop_entry['strikeouts'].get('line')
            if 'outs' in prop_entry:
                outs_line = prop_entry['outs'].get('line')
            # season stats
            ms = None
            for pid,info in master.items():
                nm = normalize_name(info.get('name',''))
                if nm == norm_name:
                    ms = info; break
            season_ip = ms.get('innings_pitched') if ms else None
            season_gs = ms.get('games_started') if ms else None
            season_so = ms.get('strikeouts') if ms else None
            season_bb = ms.get('walks') if ms else None
            season_era = ms.get('era') if ms else None
            season_whip = ms.get('whip') if ms else None
            # opponent context
            opp = p.get('opponent')
            opp_k_rate = None
            if opp and isinstance(team_batting, dict):
                for tname, rec in team_batting.items():
                    if normalize_name(tname) == normalize_name(opp):
                        opp_k_rate = rec.get('k_rate')
                        break
            park_factor = None
            venue_key = p['opponent'] if p['is_home'] == 0 else p['team']
            if park_factors:
                for pk, val in park_factors.items():
                    if normalize_name(pk) == normalize_name(venue_key):
                        if isinstance(val,(int,float)):
                            park_factor = float(val)
                            break
            team_k_rate = None
            team_rec = team_batting.get(p['team']) if isinstance(team_batting, dict) else None
            if team_rec:
                team_k_rate = team_rec.get('k_rate')
            rows.append([
                date_iso,p['pitcher_name'],p['team'],p['opponent'],p['is_home'],
                k_line, outs_line,
                season_ip, season_gs, season_so, season_bb, season_era, season_whip,
                team_k_rate, opp_k_rate, park_factor
            ])
    # Append rows
    if rows:
        with open(OUT_CSV,'a',newline='') as f:
            w=csv.writer(f)
            w.writerows(rows)
    print(f"Historical dataset rows appended: {len(rows)} -> {OUT_CSV}")

if __name__ == '__main__':
    build()
