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
    # Prefer promoted version if specified
    try:
        prom_path = os.path.join(MODEL_ROOT, 'promoted.json')
        if os.path.exists(prom_path):
            import json as _json
            with open(prom_path, 'r', encoding='utf-8') as f:
                doc = _json.load(f)
            ver = (doc or {}).get('version')
            if ver:
                cand = os.path.join(MODEL_ROOT, str(ver))
                if os.path.isdir(cand):
                    return cand
    except Exception:
        pass
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

def _build_features(
    stats: Dict[str, Any],
    team: Optional[str],
    opponent: Optional[str],
    lines: Optional[Dict[str, Any]] = None,
    adj: Optional[Dict[str, Any]] = None,
) -> Dict[str, float]:
    """Build inference features aligned with training FEATURE_COLS.

    Training uses DictVectorizer over these keys:
      - team/opponent/venue_home_team (as categorical flags "team=<name>")
      - line_strikeouts, line_outs, over/under odds per market
      - adj_strikeouts, adj_outs, k_factor, outs_factor, opponent_k_rate,
        park_factor_used, recent_ip_per_start, recent_ip_weighted,
        league_avg_k_rate
    We approximate missing values conservatively.
    """
    # Line/odds context (from today's markets)
    def _extract_line(mkt: str, key: str) -> Optional[float]:
        try:
            if not lines or mkt not in lines:
                return None
            v = lines[mkt].get(key)
            if v is None:
                return None
            s = str(v).strip()
            if s == '' or s.lower() == 'none':
                return None
            return float(s)
        except Exception:
            return None

    line_ks = _extract_line('strikeouts', 'line')
    line_outs = _extract_line('outs', 'line')
    over_odds_ks = _extract_line('strikeouts', 'over_odds')
    under_odds_ks = _extract_line('strikeouts', 'under_odds')
    over_odds_outs = _extract_line('outs', 'over_odds')
    under_odds_outs = _extract_line('outs', 'under_odds')

    # Recent workload approximation
    ip = _safe_float(stats.get('innings_pitched'))
    gs = _safe_float(stats.get('games_started'))
    ip_per_start = (ip / gs) if (ip > 0 and gs > 0) else 5.5
    ip_per_start = max(3.0, min(8.0, ip_per_start))

    # Derived adjusted projections fallback if none provided
    if adj is None:
        adj = {}
        try:
            ap = (stats.get('adjusted_projections') or {}) if isinstance(stats, dict) else {}
        except Exception:
            ap = {}
        # Use available adjusted fields if present, else fallback defaults
        adj['k_factor'] = _safe_float(ap.get('k_factor'), 1.0)
        adj['outs_factor'] = _safe_float(ap.get('outs_factor'), 1.0)
        adj['opponent_k_rate'] = _safe_float(ap.get('opponent_k_rate'))
        adj['park_factor_used'] = _safe_float(ap.get('park_factor_used'))
        adj['recent_ip_per_start'] = _safe_float(ap.get('recent_ip_per_start'), ip_per_start)
        adj['recent_ip_weighted'] = _safe_float(ap.get('recent_ip_weighted'), ip_per_start)
        adj['league_avg_k_rate'] = _safe_float(ap.get('league_avg_k_rate'), 0.2202)
        # Rough adj stat hints when not supplied
        k_rate = (_safe_float(stats.get('strikeouts')) / ip) if ip > 0 else 1.0
        adj['adj_strikeouts'] = k_rate * adj['recent_ip_per_start']
        adj['adj_outs'] = adj['recent_ip_per_start'] * 3.0

    feats: Dict[str, float] = {}
    # Numeric features present in training
    if line_ks is not None:
        feats['line_strikeouts'] = line_ks
    if line_outs is not None:
        feats['line_outs'] = line_outs
    if over_odds_ks is not None:
        feats['over_odds_ks'] = over_odds_ks
    if under_odds_ks is not None:
        feats['under_odds_ks'] = under_odds_ks
    if over_odds_outs is not None:
        feats['over_odds_outs'] = over_odds_outs
    if under_odds_outs is not None:
        feats['under_odds_outs'] = under_odds_outs

    for key in (
        'adj_strikeouts','adj_outs','k_factor','outs_factor','opponent_k_rate',
        'park_factor_used','recent_ip_per_start','recent_ip_weighted','league_avg_k_rate',
    ):
        v = adj.get(key) if isinstance(adj, dict) else None
        if v is not None:
            try:
                feats[key] = float(v)
            except Exception:
                pass

    # Categorical context must match training pattern: "team=<name>"
    if team:
        feats[f'team={str(team)}'] = 1.0
    if opponent:
        feats[f'opponent={str(opponent)}'] = 1.0
    # We don't always know venue_home_team here; omit if unknown.
    return feats

class PitcherPropsModels:
    def __init__(self, base_dir: Optional[str] = None) -> None:
        self.base_dir = base_dir or _latest_model_dir()
        self.models: Dict[str, Any] = {}
        self.dv: Dict[str, Any] = {}
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
                    dv_path = os.path.join(self.base_dir, f'{m}_dv.joblib')
                    if os.path.exists(dv_path):
                        self.dv[m] = joblib.load(dv_path)
                self.available = len(self.models) > 0
            except Exception:
                self.available = False

    def predict_means(
        self,
        stats: Dict[str, Any],
        team: Optional[str],
        opponent: Optional[str],
        lines: Optional[Dict[str, Any]] = None,
        adj: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, float]]:
        if not self.available:
            return None
        feats = _build_features(stats, team, opponent, lines=lines, adj=adj)
        # Use per-market DictVectorizer if available; otherwise fallback simple ordering
        out: Dict[str, float] = {}
        for m, model in self.models.items():
            try:
                if m in self.dv and self.dv[m] is not None:
                    X = self.dv[m].transform([feats])
                    try:
                        # If feature vector has no active features, skip to avoid constant predictions
                        if hasattr(X, 'getnnz') and X.getnnz() == 0:
                            continue
                    except Exception:
                        pass
                else:
                    keys = sorted(feats.keys())
                    X = [[feats[k] for k in keys]]
                y = model.predict(X)
                out[m] = float(y[0])
            except Exception:
                continue
        return out or None

    def debug_features(
        self,
        stats: Dict[str, Any],
        team: Optional[str],
        opponent: Optional[str],
        lines: Optional[Dict[str, Any]] = None,
        adj: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Return raw feature dict and, per market, nnz and active feature names and prediction.
        Helps diagnose vectorizer mismatches causing constant outputs.
        """
        info: Dict[str, Any] = {}
        feats = _build_features(stats, team, opponent, lines=lines, adj=adj)
        info['features'] = feats
        per_market = {}
        for m, model in (self.models or {}).items():
            try:
                market_info: Dict[str, Any] = {}
                if m in self.dv and self.dv[m] is not None:
                    dv = self.dv[m]
                    X = dv.transform([feats])
                    nnz = None
                    active_features = []
                    try:
                        nnz = int(X.getnnz()) if hasattr(X, 'getnnz') else None
                        # Extract active feature names
                        idx = X.indices if hasattr(X, 'indices') else []
                        names = list(getattr(dv, 'get_feature_names_out', dv.get_feature_names)())
                        for i in idx:
                            if i < len(names):
                                active_features.append(names[i])
                    except Exception:
                        pass
                    y = model.predict(X)
                    market_info.update({'nnz': nnz, 'active_features': active_features[:25], 'prediction': float(y[0])})
                else:
                    keys = sorted(feats.keys())
                    X = [[feats[k] for k in keys]]
                    y = model.predict(X)
                    market_info.update({'active_features': keys[:25], 'prediction': float(y[0])})
                per_market[m] = market_info
            except Exception:
                continue
        info['per_market'] = per_market
        return info

_CACHED: Optional[PitcherPropsModels] = None

def load_models(force=False) -> Optional[PitcherPropsModels]:
    global _CACHED
    if force or _CACHED is None:
        _CACHED = PitcherPropsModels()
    return _CACHED if _CACHED and _CACHED.available else None
