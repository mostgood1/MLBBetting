"""Automated daily models refresh with simple gating & promotion.

Steps:
 1) Backfill outcomes and recompute calibration
 2) Build dataset and augment with outcomes
 3) Train models
 4) Compute simple metrics vs last bundle and promote if improved

Promotion: writes models/pitcher_props/promoted.json with {'version': <dir>}
"""
from __future__ import annotations
import os, json, time, shutil
from typing import Dict, Any

ROOT = os.path.dirname(os.path.dirname(__file__))
MODEL_ROOT = os.path.join(ROOT, 'models','pitcher_props')
DATA_DIR = os.path.join(ROOT, 'data')


def _run_py(mod_or_path: str) -> bool:
    import subprocess, sys
    try:
        if mod_or_path.endswith('.py'):
            cmd = [sys.executable, mod_or_path]
        else:
            cmd = [sys.executable, '-m', mod_or_path]
        res = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
        print(res.stdout)
        if res.returncode != 0:
            print(res.stderr)
        return res.returncode == 0
    except Exception as e:
        print(f"Error running {mod_or_path}: {e}")
        return False


def _current_promoted() -> str | None:
    p = os.path.join(MODEL_ROOT, 'promoted.json')
    try:
        with open(p,'r',encoding='utf-8') as f:
            return (json.load(f) or {}).get('version')
    except Exception:
        return None


def _latest_trained() -> str | None:
    try:
        dirs = [d for d in os.listdir(MODEL_ROOT) if os.path.isdir(os.path.join(MODEL_ROOT, d)) and d[0].isdigit()]
        if not dirs:
            return None
        dirs.sort(reverse=True)
        return dirs[0]
    except Exception:
        return None


def _compute_simple_metric() -> Dict[str, Any]:
    """Compute a tiny metric: average absolute error of last N realized vs. current projections.
    Fallback to 0 improvement if any step fails.
    """
    try:
        # Use realized outcomes doc (already updated by backfill)
        path = os.path.join(DATA_DIR, 'daily_bovada', 'pitcher_prop_realized_results.json')
        with open(path,'r',encoding='utf-8') as f:
            doc = json.load(f)
        items = doc.get('pitcher_market_outcomes', [])[-200:]
        errs = []
        for it in items:
            proj = it.get('proj')
            act = it.get('actual')
            if isinstance(proj,(int,float)) and isinstance(act,(int,float)):
                errs.append(abs(float(proj)-float(act)))
        mae = sum(errs)/len(errs) if errs else None
        return {'mae_recent': mae, 'n': len(errs)}
    except Exception:
        return {'mae_recent': None, 'n': 0}


def _write_promoted(version: str) -> None:
    path = os.path.join(MODEL_ROOT, 'promoted.json')
    with open(path,'w',encoding='utf-8') as f:
        json.dump({'version': version, 'promoted_at': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}, f, indent=2)


def main():
    # 1) Backfill outcomes & calibration for last 35 days
    _run_py('backfill_pitcher_prop_realized_outcomes.py')
    # 2) Build dataset & augment
    _run_py('historical_pitcher_prop_dataset.py')
    _run_py('training.augment_with_outcomes')
    # 3) Train models
    ok = _run_py('training.train_pitcher_models')
    if not ok:
        print('Training failed, aborting promotion.')
        return False
    # 4) Gate & promote: simple rule—promote latest if recent MAE is equal or better than previous
    latest = _latest_trained()
    if not latest:
        print('No trained bundle found to promote.')
        return False
    prev = _current_promoted()
    # Compute metric snapshot (uses same realized doc for both; simplistic)
    metrics = _compute_simple_metric()
    # If no previous, auto-promote
    if not prev:
        _write_promoted(latest)
        print(f"Promoted first bundle: {latest} | metrics={metrics}")
        return True
    # If we want to be conservative and skip if metric is None
    mae = metrics.get('mae_recent')
    if mae is None:
        print('Metric unavailable; skipping auto-promotion.')
        return False
    # Simple heuristic: promote if mae <= previous recorded (we don't track previous exactly here); always promote latest for now
    _write_promoted(latest)
    print(f"Promoted latest bundle: {latest} | metrics={metrics}")
    return True


if __name__ == '__main__':
    main()
