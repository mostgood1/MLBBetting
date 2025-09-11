#!/usr/bin/env python3
"""Build pitcher outcome distributions (Phase 1 Synergy Layer).

Reads latest pitcher prop recommendations + underlying projections/volatility
artifacts to construct lightweight parametric distributions for key markets.

Outputs file:
  data/daily_bovada/pitcher_prop_distributions_<DATE>.json

Structure:
{
  "date": "YYYY-MM-DD",
  "built_at": ISO_TS,
  "pitchers": {
     "pitcher_key": {
        "outs": {"mean": float, "std": float, "dist": "normal", "p_ge": {"18":0.42,...}},
        "strikeouts": {"mean": float, "dist": "poisson", "lambda": float, "p_ge": {"6":0.31,...}},
        "earned_runs": {"mean": float, "dist": "gamma", "shape": k, "scale": theta},
        ...
     }
  }
}

Only a handful of tail probabilities are pre-computed (config below) to keep file small.
These distributions are approximate and will be refined in later phases.
"""
from __future__ import annotations
import os, json, math, unicodedata
from datetime import datetime
from typing import Dict, Any

BASE_DIR = os.path.join('data','daily_bovada')
VOLATILITY_FILE = os.path.join(BASE_DIR,'pitcher_prop_volatility.json')
CALIBRATION_FILE = os.path.join(BASE_DIR,'pitcher_prop_calibration_meta.json')

STD_BASE = {
    'outs': 2.0,
    'strikeouts': 1.2,
    'earned_runs': 1.2,
    'hits_allowed': 1.5,
    'walks': 1.0
}

OUTS_PROB_THRESH = [15, 18, 21, 24]
K_PROB_THRESH = [4,5,6,7,8,9]

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

def normal_cdf(x: float):
    return 0.5*(1+math.erf(x/math.sqrt(2)))

def poisson_sf(k: int, lam: float) -> float:
    """P(X >= k) for Poisson(lambda) using tail complement simple sum.
    For moderate lambda (<20) direct summation acceptable.
    """
    if k <= 0:
        return 1.0
    # Compute P(X < k)
    p = math.exp(-lam)
    acc = p
    for i in range(1, k):
        p *= lam / i
        acc += p
    return max(0.0, 1.0 - acc)

def dynamic_std(market: str, pitcher_key: str, base: float, vol_doc: dict, calib_doc: dict) -> float:
    # Calibration suggestion first
    try:
        cval = calib_doc.get('markets',{}).get(market,{}).get('suggested_std')
        if isinstance(cval,(int,float)) and cval>0:
            base = cval
    except Exception:
        pass
    try:
        pv = vol_doc.get(pitcher_key,{}).get(market)
        if isinstance(pv, dict) and pv.get('var') is not None:
            v = pv['var']
            if isinstance(v,(int,float)) and v>=0:
                # combine: average of base^2 and var (line derived) then sqrt
                combined = 0.5*(base*base) + 0.5*float(v)
                return max(0.4, min(4.0, combined**0.5))
    except Exception:
        pass
    return base

def build_distributions(date_str: str) -> Dict[str, Any]:
    safe_date = date_str.replace('-','_')
    rec_path = os.path.join(BASE_DIR, f'pitcher_prop_recommendations_{safe_date}.json')
    rec_doc = load_json(rec_path) or {}
    recommendations = rec_doc.get('recommendations') or []
    # Index by pitcher -> aggregate projection values per market (some redundancy per market entry)
    pitchers: Dict[str, Dict[str, Any]] = {}
    for r in recommendations:
        name = r.get('pitcher') or r.get('name')
        if not name:
            continue
        p_key = normalize_name(name)
        market = r.get('market')
        proj = r.get('proj_value') or r.get('proj')
        if market and isinstance(proj,(int,float)):
            entry = pitchers.setdefault(p_key, {'name': name, 'proj': {}})
            # prefer first projection per market (or average if multiple appear)
            if market in entry['proj']:
                entry['proj'][market] = 0.5*(entry['proj'][market] + float(proj))
            else:
                entry['proj'][market] = float(proj)

    vol_doc = load_json(VOLATILITY_FILE) or {}
    calib_doc = load_json(CALIBRATION_FILE) or {}

    out_pitchers = {}
    for p_key, info in pitchers.items():
        proj_map = info['proj']
        p_out = {}
        # OUTS (normal approximate truncated at 0..27)
        if 'outs' in proj_map:
            mean_outs = proj_map['outs']
            std_outs = dynamic_std('outs', p_key, STD_BASE['outs'], vol_doc, calib_doc)
            p_ge = {str(k): 1 - normal_cdf((k - 0.5 - mean_outs)/std_outs) for k in OUTS_PROB_THRESH}
            p_out['outs'] = {'mean': round(mean_outs,2), 'std': round(std_outs,3), 'dist':'normal', 'p_ge': {k: round(v,3) for k,v in p_ge.items()}}
        # STRIKEOUTS (poisson or normal if lambda>12)
        if 'strikeouts' in proj_map:
            mean_k = max(0.1, proj_map['strikeouts'])
            if mean_k <= 12:
                lam = mean_k
                p_ge = {str(k): round(poisson_sf(k, lam),3) for k in K_PROB_THRESH}
                p_out['strikeouts'] = {'mean': round(mean_k,2), 'dist':'poisson', 'lambda': round(lam,3), 'p_ge': p_ge}
            else:
                std_k = dynamic_std('strikeouts', p_key, STD_BASE['strikeouts'], vol_doc, calib_doc)
                p_ge = {str(k): round(1 - normal_cdf((k-0.5-mean_k)/std_k),3) for k in K_PROB_THRESH}
                p_out['strikeouts'] = {'mean': round(mean_k,2), 'std': round(std_k,3), 'dist':'normal', 'p_ge': p_ge}
        # EARNED RUNS (gamma)
        if 'earned_runs' in proj_map:
            mean_er = max(0.05, proj_map['earned_runs'])
            std_er = dynamic_std('earned_runs', p_key, STD_BASE['earned_runs'], vol_doc, calib_doc)
            var_er = max(0.01, std_er**2)
            shape = (mean_er**2)/var_er if var_er>0 else 1.0
            scale = mean_er/shape if shape>0 else mean_er
            p_out['earned_runs'] = {'mean': round(mean_er,2), 'dist':'gamma', 'shape': round(shape,3), 'scale': round(scale,3)}
        # HITS ALLOWED (poisson)
        if 'hits_allowed' in proj_map:
            lam = max(0.2, proj_map['hits_allowed'])
            p_out['hits_allowed'] = {'mean': round(lam,2), 'dist':'poisson', 'lambda': round(lam,3)}
        # WALKS (poisson)
        if 'walks' in proj_map:
            lam = max(0.05, proj_map['walks'])
            p_out['walks'] = {'mean': round(lam,2), 'dist':'poisson', 'lambda': round(lam,3)}
        if p_out:
            out_pitchers[p_key] = p_out

    doc = {
        'date': date_str,
        'built_at': datetime.utcnow().isoformat(),
        'pitcher_count': len(out_pitchers),
        'pitchers': out_pitchers
    }
    return doc

def save_distributions(doc: Dict[str, Any]):
    date_str = doc.get('date') or 'unknown'
    safe = str(date_str).replace('-','_')
    os.makedirs(BASE_DIR, exist_ok=True)
    path = os.path.join(BASE_DIR, f'pitcher_prop_distributions_{safe}.json')
    tmp = path + '.tmp'
    with open(tmp,'w',encoding='utf-8') as f:
        json.dump(doc,f,indent=2)
    os.replace(tmp,path)
    return path

def build_and_save_distributions(date_str: str):
    doc = build_distributions(date_str)
    return save_distributions(doc)

def main():  # manual run
    from datetime import datetime as _dt
    date_str = _dt.utcnow().strftime('%Y-%m-%d')
    path = build_and_save_distributions(date_str)
    print(f"Built distributions for {date_str} -> {path}")

if __name__ == '__main__':
    main()
