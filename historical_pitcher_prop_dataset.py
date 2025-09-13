"""Build or update historical pitcher prop feature dataset.

Aggregates daily projection_features_*.json and bovada_pitcher_props_*.json files
into a flat CSV for model training (strikeouts & outs).

Columns (initial set):
  date,pitcher_id,pitcher_name,team,opponent,venue_home_team,
  line_strikeouts,line_outs,proj_strikeouts,proj_outs,adj_strikeouts,adj_outs,
  k_factor,outs_factor,opponent_k_rate,park_factor_used,recent_ip_per_start,
  recent_ip_weighted,league_avg_k_rate,edge_dir_ks,edge_dir_outs,
  diff_ks,diff_outs,diff_adj_ks,diff_adj_outs,
  over_odds_ks,under_odds_ks,over_odds_outs,under_odds_outs

The script is idempotent: avoids duplicate (date,pitcher_id) rows per stat.
"""
from __future__ import annotations
import os, json, csv, re, unicodedata
from glob import glob
from datetime import datetime
from typing import Dict, Any

DATA_DIR = 'data'
DAILY_DIR = os.path.join(DATA_DIR, 'daily_bovada')
OUT_DIR = os.path.join(DATA_DIR, 'model_datasets')
OUT_CSV = os.path.join(OUT_DIR, 'pitcher_props_history.csv')

FIELDS = [
    'date','pitcher_id','pitcher_name','pitcher_key','team','opponent','venue_home_team',
    'line_strikeouts','line_outs','proj_strikeouts','proj_outs','adj_strikeouts','adj_outs',
    'k_factor','outs_factor','opponent_k_rate','park_factor_used','recent_ip_per_start',
    'recent_ip_weighted','league_avg_k_rate','edge_dir_ks','edge_dir_outs',
    'diff_ks','diff_outs','diff_adj_ks','diff_adj_outs',
    'over_odds_ks','under_odds_ks','over_odds_outs','under_odds_outs'
]

def _list_files(pattern: str):
    return sorted(glob(os.path.join(DAILY_DIR, pattern)))

def _load_json(path: str):
    try:
        with open(path,'r') as f:
            return json.load(f)
    except Exception:
        return None

def _ensure_dirs():
    os.makedirs(OUT_DIR, exist_ok=True)

# Load existing rows to skip duplicates

def _load_existing_keys():
    keys = set()
    if not os.path.exists(OUT_CSV):
        return keys
    try:
        with open(OUT_CSV,'r',newline='') as f:
            r = csv.DictReader(f)
            for row in r:
                keys.add((row['date'], row['pitcher_id']))
    except Exception:
        pass
    return keys

def build_dataset():
    _ensure_dirs()
    existing = _load_existing_keys()

    projection_files = _list_files('projection_features_*.json')
    # Map date->projections for quick lookups
    records_to_append = []
    for pf in projection_files:
        data = _load_json(pf)
        if not data or 'pitchers' not in data:
            continue
        date = data.get('date') or _extract_date_from_filename(pf)
        league_avg = None
        try:
            league_avg = data.get('pitchers', [{}])[0].get('adjusted_projections', {}).get('league_avg_k_rate')
        except Exception:
            pass
        for p in data['pitchers']:
            pid = str(p.get('pitcher_id') or '')
            if not pid:
                continue
            key = (date, pid)
            if key in existing:
                continue
            name = p.get('pitcher_name')
            pkey = _normalize_name(name) if name else None
            lines = p.get('lines', {}) or {}
            ks_line = _safe_number((lines.get('strikeouts') or {}).get('line'))
            outs_line = _safe_number((lines.get('outs') or {}).get('line'))
            over_odds_ks = (lines.get('strikeouts') or {}).get('over_odds')
            under_odds_ks = (lines.get('strikeouts') or {}).get('under_odds')
            over_odds_outs = (lines.get('outs') or {}).get('over_odds')
            under_odds_outs = (lines.get('outs') or {}).get('under_odds')
            adj = p.get('adjusted_projections', {})
            diffs = p.get('diffs', {})
            diffs_adj = p.get('diffs_adjusted', {})
            recs = p.get('recommendations', {})
            row = {
                'date': date,
                'pitcher_id': pid,
                'pitcher_name': name,
                'pitcher_key': pkey,
                'team': p.get('team'),
                'opponent': p.get('opponent'),
                'venue_home_team': p.get('venue_home_team'),
                'line_strikeouts': ks_line,
                'line_outs': outs_line,
                'proj_strikeouts': _safe_number(p.get('projected_strikeouts')),
                'proj_outs': _safe_number(p.get('projected_outs')),
                'adj_strikeouts': _safe_number(adj.get('strikeouts')),
                'adj_outs': _safe_number(adj.get('outs')),
                'k_factor': _safe_number(adj.get('k_factor')),
                'outs_factor': _safe_number(adj.get('outs_factor')),
                'opponent_k_rate': _safe_number(adj.get('opponent_k_rate')),
                'park_factor_used': _safe_number(adj.get('park_factor_used')),
                'recent_ip_per_start': _safe_number(adj.get('recent_ip_per_start')),
                'recent_ip_weighted': _safe_number(adj.get('recent_ip_weighted')),
                'league_avg_k_rate': _safe_number(adj.get('league_avg_k_rate') or league_avg),
                'edge_dir_ks': recs.get('strikeouts'),
                'edge_dir_outs': recs.get('outs'),
                'diff_ks': _safe_number(diffs.get('strikeouts')),
                'diff_outs': _safe_number(diffs.get('outs')),
                'diff_adj_ks': _safe_number(diffs_adj.get('strikeouts')),
                'diff_adj_outs': _safe_number(diffs_adj.get('outs')),
                'over_odds_ks': over_odds_ks,
                'under_odds_ks': under_odds_ks,
                'over_odds_outs': over_odds_outs,
                'under_odds_outs': under_odds_outs,
            }
            records_to_append.append(row)
    if not records_to_append:
        print("No new records to append.")
        return

    write_header = not os.path.exists(OUT_CSV)
    with open(OUT_CSV,'a',newline='') as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        if write_header:
            w.writeheader()
        for r in records_to_append:
            w.writerow(r)
    print(f"Appended {len(records_to_append)} new rows -> {OUT_CSV}")


def _safe_number(v):
    try:
        if v is None: return None
        if isinstance(v,(int,float)): return v
        s = str(v).strip()
        if s == '': return None
        return float(s)
    except Exception:
        return None

def _extract_date_from_filename(path: str):
    m = re.search(r'(20\d{2}_\d{2}_\d{2})', path)
    if m:
        d = m.group(1)
        return f"{d[0:4]}-{d[5:7]}-{d[8:10]}"
    return None

def _normalize_name(name: str) -> str:
    try:
        t = unicodedata.normalize('NFD', name)
        t = ''.join(ch for ch in t if unicodedata.category(ch) != 'Mn')
        return t.lower().strip()
    except Exception:
        return (name or '').lower().strip()

if __name__ == '__main__':
    build_dataset()
