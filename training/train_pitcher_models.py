"""Train pitcher prop models (per market) and save artifacts for runtime.

Usage:
  python -m training.train_pitcher_models

Inputs:
  - data/model_datasets/pitcher_props_history.csv (built by historical_pitcher_prop_dataset.py)

Outputs:
  - models/pitcher_props/<version>/strikeouts_mean.joblib, outs_mean.joblib, ...
  - models/pitcher_props/<version>/metadata.json

This is a minimal, dependency-light trainer using scikit-learn's GradientBoostingRegressor.
If sklearn or joblib are not available, the script exits gracefully.
"""
from __future__ import annotations
import os, json, time
from typing import Dict, Any, List, Optional

DATASET = os.path.join('data','model_datasets','pitcher_props_history_with_targets.csv')
MODEL_ROOT = os.path.join('models','pitcher_props')

MARKETS = {
    'strikeouts': {
        'line_col': 'line_strikeouts',
        'proj_col': 'proj_strikeouts',
    'target_col': 'target_strikeouts',
    },
    'outs': {
        'line_col': 'line_outs',
        'proj_col': 'proj_outs',
    'target_col': 'target_outs',
    }
}

FEATURE_COLS = [
    # Basic identifying context
    'team','opponent','venue_home_team',
    # Lines and odds context
    'line_strikeouts','line_outs','over_odds_ks','under_odds_ks','over_odds_outs','under_odds_outs',
    # Existing engineered features from historical builder (if present)
    'adj_strikeouts','adj_outs','k_factor','outs_factor','opponent_k_rate','park_factor_used',
    'recent_ip_per_start','recent_ip_weighted','league_avg_k_rate',
]

def _read_csv_rows(path: str) -> List[Dict[str, Any]]:
    import csv
    rows: List[Dict[str, Any]] = []
    with open(path,'r',newline='') as f:
        r = csv.DictReader(f)
        for row in r:
            rows.append(row)
    return rows

def _to_float(x: Any) -> Optional[float]:
    try:
        if x is None:
            return None
        s = str(x).strip()
        if s == '' or s.lower() == 'none':
            return None
        return float(s)
    except Exception:
        return None

def _prepare_xy(rows: List[Dict[str, Any]], market: str):
    from sklearn.feature_extraction import DictVectorizer
    import numpy as np
    cfg = MARKETS[market]
    # Build examples where the market line exists
    examples: List[Dict[str, Any]] = []
    y_vals: List[float] = []
    for r in rows:
        line = _to_float(r.get(cfg['line_col']))
        target = _to_float(r.get(cfg['target_col']))
        # Fallback to projection column if realized target missing
        if target is None:
            target = _to_float(r.get(cfg['proj_col']))
        if line is None or target is None:
            continue
        feat: Dict[str, Any] = {}
        for col in FEATURE_COLS:
            v = r.get(col)
            fv = _to_float(v)
            if fv is not None:
                feat[col] = fv
            else:
                # keep some categorical context
                if v and col in ('team','opponent','venue_home_team'):
                    feat[f'{col}={str(v)}'] = 1.0
        examples.append(feat)
        y_vals.append(float(target))
    if not examples:
        return None, None, None
    dv = DictVectorizer(sparse=True)
    X = dv.fit_transform(examples)
    y = np.array(y_vals, dtype=float)
    return X, y, dv

def train_and_save(version_dir: str, market: str, X, y, dv) -> bool:
    from sklearn.ensemble import GradientBoostingRegressor
    import joblib
    # Simple GBM for mean
    model = GradientBoostingRegressor(random_state=42, n_estimators=300, max_depth=3, learning_rate=0.05)
    model.fit(X, y)
    # Save
    os.makedirs(version_dir, exist_ok=True)
    joblib.dump(model, os.path.join(version_dir, f'{market}_mean.joblib'))
    joblib.dump(dv, os.path.join(version_dir, f'{market}_dv.joblib'))
    return True

def main():
    # Soft import checks
    try:
        import sklearn  # type: ignore
        import joblib  # type: ignore
    except Exception:
        print('❌ Missing dependencies (scikit-learn, joblib). Install to train models.')
        return False
    if not os.path.exists(DATASET):
        print(f'❌ Dataset not found: {DATASET}. Build it first.')
        return False
    rows = _read_csv_rows(DATASET)
    if not rows:
        print('❌ Empty dataset.')
        return False
    version = time.strftime('%Y%m%d_%H%M%S')
    version_dir = os.path.join(MODEL_ROOT, version)
    trained: List[str] = []
    for m in MARKETS.keys():
        X, y, dv = _prepare_xy(rows, m)
        if X is None:
            print(f'⚠️ No training rows for market: {m}')
            continue
        ok = train_and_save(version_dir, m, X, y, dv)
        if ok:
            trained.append(m)
    if not trained:
        print('❌ No models trained')
        return False
    meta = {
        'version': version,
        'trained_markets': trained,
        'dataset': os.path.relpath(DATASET).replace('\\','/'),
        'created_at': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
        'notes': 'Initial minimal GBM models; targets use proj_* columns as placeholders.'
    }
    os.makedirs(version_dir, exist_ok=True)
    with open(os.path.join(version_dir, 'metadata.json'),'w',encoding='utf-8') as f:
        json.dump(meta, f, indent=2)
    print(f'✅ Trained markets: {trained} -> {version_dir}')
    return True

if __name__ == '__main__':
    main()
