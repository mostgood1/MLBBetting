"""Augment pitcher props dataset with realized outcomes targets.

Reads:
  - data/model_datasets/pitcher_props_history.csv
  - data/daily_bovada/pitcher_prop_realized_results.json

Writes:
  - data/model_datasets/pitcher_props_history_with_targets.csv

Targets added:
  - target_strikeouts, target_outs, target_walks, target_hits_allowed, target_earned_runs

Join keys:
  - (date, pitcher_key)

Note: pitcher_key comes from normalized pitcher_name saved by historical_pitcher_prop_dataset.py
"""
from __future__ import annotations
import os, csv, json
from typing import Dict, Any

DATA_DIR = os.path.join('data','model_datasets')
IN_CSV = os.path.join(DATA_DIR, 'pitcher_props_history.csv')
OUT_CSV = os.path.join(DATA_DIR, 'pitcher_props_history_with_targets.csv')
REALIZED = os.path.join('data','daily_bovada','pitcher_prop_realized_results.json')

MARKETS = ('strikeouts','outs','walks','hits_allowed','earned_runs')


def _read_rows(path: str):
    rows = []
    with open(path,'r',newline='') as f:
        r = csv.DictReader(f)
        for row in r:
            rows.append(row)
    return rows, r.fieldnames


def _write_rows(path: str, fieldnames, rows):
    with open(path,'w',newline='') as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for row in rows:
            w.writerow(row)


def _load_realized(path: str):
    if not os.path.exists(path):
        return {}
    try:
        with open(path,'r',encoding='utf-8') as f:
            doc = json.load(f)
    except Exception:
        return {}
    idx: Dict[tuple, Dict[str, Any]] = {}
    for it in doc.get('pitcher_market_outcomes', []) or []:
        date = it.get('date')
        pkey = it.get('pitcher_key') or it.get('pitcher')
        mkt = it.get('market')
        val = it.get('actual')
        if not date or not pkey or mkt not in MARKETS:
            continue
        idx.setdefault((date, pkey), {})[mkt] = val
    return idx


def main():
    if not os.path.exists(IN_CSV):
        print(f"❌ Missing input dataset: {IN_CSV}")
        return False
    rows, fields = _read_rows(IN_CSV)
    realized = _load_realized(REALIZED)
    added = [f'target_{m}' for m in MARKETS]
    out_fields = list(fields)
    for a in added:
        if a not in out_fields:
            out_fields.append(a)
    out_rows = []
    for r in rows:
        key = (r.get('date'), r.get('pitcher_key') or r.get('pitcher_name') or '')
        tgts = realized.get(key) or {}
        for m in MARKETS:
            r[f'target_{m}'] = tgts.get(m)
        out_rows.append(r)
    os.makedirs(DATA_DIR, exist_ok=True)
    _write_rows(OUT_CSV, out_fields, out_rows)
    print(f"Wrote targets dataset -> {OUT_CSV} ({len(out_rows)} rows)")
    return True


if __name__ == '__main__':
    main()
