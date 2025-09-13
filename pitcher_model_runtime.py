"""Runtime loader for pitcher prop models (optional).

Provides a light abstraction to load the latest per-market models from
models/pitcher_props/<version>/ and generate predictions from basic features.

If models or dependencies are unavailable, APIs return None and the caller
should fallback to heuristic projections.
"""
from __future__ import annotations
import os, json, glob
from typing import Dict, Any, Optional

try:
    import joblib  # type: ignore
except Exception:
    joblib = None  # type: ignore

MODEL_ROOT = os.path.join('models', 'pitcher_props')
MARKETS = ['strikeouts','outs','earned_runs','hits_allowed','walks']

def _latest_model_dir() -> Optional[str]:
    if not os.path.exists(MODEL_ROOT):
        return None
    dirs = [d for d in glob.glob(os.path.join(MODEL_ROOT, '*')) if os.path.isdir(d)]
    if not dirs:
        return None
    # Sort by mtime desc
    dirs.sort(key=lambda p: os.path.getmtime(p), reverse=True)
    return dirs[0]

def _safe_float(x, default=0.0):
    try:
        if x is None:
            return default
        return float(x)
    except Exception:
        return default

def _build_features(stats: Dict[str, Any], team: Optional[str], opponent: Optional[str]) -> Dict[str, float]:
    # Minimal, non-leaky features available at inference time
    ip = _safe_float(stats.get('innings_pitched'))
    gs = _safe_float(stats.get('games_started'))
    k = _safe_float(stats.get('strikeouts'))
    bb = _safe_float(stats.get('walks'))
    era = _safe_float(stats.get('era'), 4.2)
    whip = _safe_float(stats.get('whip'), 1.3)
    recent_pitches = _safe_float(stats.get('recent_pitches'))
    recent_outs = _safe_float(stats.get('recent_outs'))
    ppo = (recent_pitches / recent_outs) if recent_pitches > 0 and recent_outs > 0 else 0.0
    feats = {
        'ip': ip,
        'gs': gs,
        'k': k,
        'bb': bb,
        'era': era,
        'whip': whip,
        'recent_ppo': ppo,
    }
    # Simple string features as flags (hashed later or ignored by simple models)
    if team:
        feats[f'team_is_{team.lower().replace(" ","_")}'] = 1.0
    if opponent:
        feats[f'opp_is_{opponent.lower().replace(" ","_")}'] = 1.0
    return feats

class PitcherPropsModels:
    def __init__(self, base_dir: Optional[str] = None) -> None:
        self.base_dir = base_dir or _latest_model_dir()
        self.models: Dict[str, Any] = {}
        self.meta: Dict[str, Any] = {}
        self.available = False
        if self.base_dir and joblib is not None:
            try:
                meta_path = os.path.join(self.base_dir, 'metadata.json')
                if os.path.exists(meta_path):
                    with open(meta_path, 'r', encoding='utf-8') as f:
                        self.meta = json.load(f)
                for m in MARKETS:
                    path = os.path.join(self.base_dir, f'{m}_mean.joblib')
                    if os.path.exists(path):
                        self.models[m] = joblib.load(path)
                self.available = len(self.models) > 0
            except Exception:
                self.available = False

    def predict_means(self, stats: Dict[str, Any], team: Optional[str], opponent: Optional[str]) -> Optional[Dict[str, float]]:
        if not self.available:
            return None
        feats = _build_features(stats, team, opponent)
        # Convert feats dict to a fixed-order list for many sklearn models
        keys = sorted(feats.keys())
        X = [[feats[k] for k in keys]]
        out: Dict[str, float] = {}
        for m, model in self.models.items():
            try:
                y = model.predict(X)
                out[m] = float(y[0])
            except Exception:
                continue
        return out or None

_CACHED: Optional[PitcherPropsModels] = None

def load_models(force=False) -> Optional[PitcherPropsModels]:
    global _CACHED
    if force or _CACHED is None:
        _CACHED = PitcherPropsModels()
    return _CACHED if _CACHED and _CACHED.available else None
