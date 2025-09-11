#!/usr/bin/env python3
"""Backfill historical pitcher prop realized outcomes & refresh calibration.

Walks backward over recent days (default 30) loading:
  - bovada props file (bovada_pitcher_props_<DATE>.json)
  - recommendations file (pitcher_prop_recommendations_<DATE>.json)
  - boxscore cache (boxscore_cache_<DATE>.json) OR generic boxscore_cache.json
and produces pitcher market realized results appended into
  data/daily_bovada/pitcher_prop_realized_results.json

After updating realized results, recomputes calibration meta (avg absolute error -> suggested std) and writes
  pitcher_prop_calibration_meta.json

Run:
  python backfill_pitcher_prop_realized_outcomes.py --days 45 --start 2025-08-10

Args:
  --days N            Number of trailing days from today (business date) to process
  --start YYYY-MM-DD  Optional explicit start date (inclusive) instead of days
  --end YYYY-MM-DD    Optional explicit end date (inclusive)
  --dry-run           Do not write files, just print summary
"""
import os, json, argparse, unicodedata
from datetime import datetime, timedelta
from typing import Dict, Any, List

VOL_FILE = os.path.join('data','daily_bovada','pitcher_prop_volatility.json')
REALIZED_FILE = os.path.join('data','daily_bovada','pitcher_prop_realized_results.json')
CALIB_FILE = os.path.join('data','daily_bovada','pitcher_prop_calibration_meta.json')
BASE_DIR = os.path.join('data','daily_bovada')

MARKETS = ('strikeouts','outs','walks','hits_allowed','earned_runs')

# ------------- Helpers ------------

def normalize_name(name: str) -> str:
    try:
        t = unicodedata.normalize('NFD', name)
        t = ''.join(ch for ch in t if unicodedata.category(ch) != 'Mn')
        return t.lower().strip()
    except Exception:
        return (name or '').lower().strip()

def load_json(path: str):
    if not os.path.exists(path):
        return None
    try:
        with open(path,'r',encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return None

def save_json_atomic(path: str, obj):
    tmp = path + '.tmp'
    with open(tmp,'w',encoding='utf-8') as f:
        json.dump(obj,f,indent=2)
    os.replace(tmp,path)

# ------------- Realized outcome extraction ------------

def extract_box_pitching(box_doc):
    out = {}
    def walk(o):
        if isinstance(o, dict):
            person = o.get('person') if isinstance(o.get('person'), dict) else None
            position = o.get('position') if isinstance(o.get('position'), dict) else None
            stats = o.get('stats') if isinstance(o.get('stats'), dict) else None
            if person and position and position.get('abbreviation') == 'P' and stats and isinstance(stats.get('pitching'), dict):
                name = (person.get('fullName') or person.get('name') or '').strip()
                if name:
                    k = normalize_name(name)
                    pitching = stats.get('pitching')
                    outs = None
                    ip = pitching.get('inningsPitched') or pitching.get('innings_pitched') or pitching.get('ip')
                    if ip is not None:
                        try:
                            if isinstance(ip,(int,float)):
                                whole = int(ip)
                                frac = round((ip - whole)+1e-8,1)
                                extra = 1 if abs(frac-0.1)<1e-6 else (2 if abs(frac-0.2)<1e-6 else 0)
                                outs = whole*3+extra
                            else:
                                s=str(ip)
                                if '.' in s:
                                    w,f = s.split('.')
                                    whole=int(w); frac=int(f or '0')
                                    extra=1 if frac==1 else (2 if frac==2 else 0)
                                    outs = whole*3+extra
                                else:
                                    outs=int(float(s))*3
                        except Exception:
                            outs=None
                    out[k] = {
                        'strikeouts': pitching.get('strikeOuts') or pitching.get('strikeouts'),
                        'walks': pitching.get('baseOnBalls') or pitching.get('walks'),
                        'hits_allowed': pitching.get('hits'),
                        'earned_runs': pitching.get('earnedRuns'),
                        'outs': outs
                    }
            for v in o.values():
                walk(v)
        elif isinstance(o, list):
            for it in o:
                walk(it)
    walk(box_doc)
    return out

# ------------- Calibration recompute ------------

def recompute_calibration(realized_doc):
    calib = {'updated': datetime.utcnow().isoformat(), 'markets': {}}
    # Collect all prediction vs. realized pairs if present (not always stored historically)
    # We'll approximate by comparing recommendation line vs. realized result (less precise than full projection set)
    for pm in realized_doc.get('pitcher_market_outcomes', []):
        mk = pm.get('market')
        if mk not in MARKETS:
            continue
        line = pm.get('line')
        realized = pm.get('actual')
        proj = pm.get('proj')  # if projections had been stored later
        if line is None or realized is None:
            continue
        # If we have projection use that, otherwise treat line as expectation (gives 0 edge, but still variance sense)
        ref = proj if isinstance(proj,(int,float)) else line
        try:
            err = abs(float(ref) - float(realized))
        except Exception:
            continue
        arr = calib['markets'].setdefault(mk, {}).setdefault('errors', [])
        arr.append(err)
    for mk, mdoc in calib['markets'].items():
        errs = mdoc.get('errors') or []
        if not errs:
            continue
        avg_err = sum(errs)/len(errs)
        suggested = max(0.4, min(3.5, avg_err*1.25))
        mdoc.clear()
        mdoc.update({'avg_abs_error': round(avg_err,3), 'suggested_std': suggested, 'sample_size': len(errs)})
    return calib

# ------------- Main process ------------

def process_day(date_str: str, realized_doc: dict, dry_run: bool=False):
    safe = date_str.replace('-', '_')
    props_path = os.path.join(BASE_DIR, f'bovada_pitcher_props_{safe}.json')
    rec_path = os.path.join(BASE_DIR, f'pitcher_prop_recommendations_{safe}.json')
    box_path = os.path.join('data', f'boxscore_cache_{safe}.json')
    if not os.path.exists(box_path):
        box_path = os.path.join('data','boxscore_cache.json')
    props = load_json(props_path) or {}
    recs = load_json(rec_path) or {}
    box = load_json(box_path) or {}
    box_pitch = extract_box_pitching(box)

    pitcher_props = props.get('pitcher_props', {}) if isinstance(props, dict) else {}
    rec_list = recs.get('recommendations', []) if isinstance(recs, dict) else []
    # Map pitcher->market->line for quick lookup
    lines = {}
    for p_key, mkts in pitcher_props.items():
        for mk, mv in mkts.items():
            if isinstance(mv, dict) and mv.get('line') is not None:
                lines.setdefault(p_key, {})[mk] = mv.get('line')

    # Build outcomes per recommendation (avoid duplicates)
    for r in rec_list:
        p_name = normalize_name(r.get('pitcher') or r.get('name') or '')
        mk = r.get('market')
        if mk not in MARKETS:
            continue
        key = (p_name, mk, date_str)
        # Skip if already present
        if any((o.get('pitcher_key'), o.get('market'), o.get('date')) == key for o in realized_doc.get('pitcher_market_outcomes', [])):
            continue
        line = None
        if p_name in lines and mk in lines[p_name]:
            line = lines[p_name][mk]
        # Actual
        bs = box_pitch.get(p_name, {})
        actual = bs.get(mk)
        # For outs could be None; we already normalized
        outcome = {
            'date': date_str,
            'pitcher_key': p_name,
            'market': mk,
            'line': line,
            'actual': actual,
            'proj': r.get('proj_value'),
            'side': r.get('side'),
            'edge': r.get('edge'),
            'odds_over': r.get('over_odds'),
            'odds_under': r.get('under_odds')
        }
        realized_doc.setdefault('pitcher_market_outcomes', []).append(outcome)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--days', type=int, default=30, help='Trailing days to backfill (ignored if --start provided)')
    ap.add_argument('--start', type=str, help='Explicit start date YYYY-MM-DD')
    ap.add_argument('--end', type=str, help='Explicit end date YYYY-MM-DD (defaults to yesterday)')
    ap.add_argument('--dry-run', action='store_true')
    args = ap.parse_args()

    today = datetime.now().date()
    end = datetime.strptime(args.end, '%Y-%m-%d').date() if args.end else (today - timedelta(days=1))

    if args.start:
        start = datetime.strptime(args.start, '%Y-%m-%d').date()
    else:
        start = end - timedelta(days=args.days-1)

    if start > end:
        raise SystemExit('Start date after end date')

    # Load existing realized doc
    realized = load_json(REALIZED_FILE) or {'games': [], 'pitcher_market_outcomes': []}

    cur = start
    processed = 0
    while cur <= end:
        ds = cur.strftime('%Y-%m-%d')
        process_day(ds, realized, dry_run=args.dry_run)
        processed += 1
        cur += timedelta(days=1)

    # Recompute calibration
    calib = recompute_calibration(realized)

    if args.dry_run:
        print(f"[DRY RUN] Processed {processed} days; outcomes={len(realized.get('pitcher_market_outcomes', []))}")
        print(json.dumps(calib, indent=2))
        return

    os.makedirs(BASE_DIR, exist_ok=True)
    save_json_atomic(REALIZED_FILE, realized)
    save_json_atomic(CALIB_FILE, calib)
    print(f"Backfill complete. Days={processed} outcomes={len(realized.get('pitcher_market_outcomes', []))}")

if __name__ == '__main__':
    main()
