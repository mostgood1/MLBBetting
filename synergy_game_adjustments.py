#!/usr/bin/env python3
"""Pitcher -> Game Synergy Adjustments (Phase 4)

Builds game-level adjusted win probabilities & totals incorporating pitcher
distribution insights (earned runs mean/std) producing deltas vs baseline.

Output file:
  data/daily_bovada/pitcher_game_synergy_<DATE>.json

Structure:
{
  "date": "YYYY-MM-DD",
  "built_at": ISO_TS,
  "games": {
     game_key: {
        "away_team": str,
        "home_team": str,
        "away_pitcher": str,
        "home_pitcher": str,
        "baseline": {"away_win_prob": f, "home_win_prob": f, "predicted_total": f},
        "adjusted": {same keys},
        "deltas": {"away_win_prob": d, "home_win_prob": d, "predicted_total": d}
     }
  },
  "summary": {"games": n, "avg_total_delta": f, "max_wp_delta": f}
}
"""
from __future__ import annotations
import os, json, math, unicodedata
from datetime import datetime
from typing import Dict, Any, Tuple

PREDICTIONS_FILE = os.path.join('data','unified_predictions_cache.json')
DIST_DIR = os.path.join('data','daily_bovada')

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

def extract_games_for_date(pred_doc: dict, date_str: str) -> Dict[str, Any]:
    if not isinstance(pred_doc, dict):
        return {}
    if date_str in pred_doc:
        # direct key
        entry = pred_doc[date_str]
    elif 'predictions_by_date' in pred_doc and date_str in pred_doc['predictions_by_date']:
        entry = pred_doc['predictions_by_date'][date_str]
    else:
        return {}
    if isinstance(entry, dict) and 'games' in entry and isinstance(entry['games'], dict):
        return entry['games']
    if isinstance(entry, dict):
        return entry
    return {}

def pitcher_er_stats(dist_doc: dict, pitcher_name: str) -> Tuple[float, float]:
    if not pitcher_name or not isinstance(dist_doc, dict):
        return (2.5, 1.0)  # fallback mean, std
    pk = normalize_name(pitcher_name)
    p = dist_doc.get('pitchers', {}).get(pk, {})
    er = p.get('earned_runs')
    if isinstance(er, dict):
        mean = er.get('mean')
        # attempt std from shape/scale if gamma else approximate from mean
        shape = er.get('shape'); scale = er.get('scale')
        if isinstance(shape,(int,float)) and isinstance(scale,(int,float)) and shape>0 and scale>0:
            var = shape * (scale ** 2)
            std = math.sqrt(var)
        else:
            std = max(0.5, math.sqrt(mean) if isinstance(mean,(int,float)) else 1.0)
        if isinstance(mean,(int,float)) and isinstance(std,(int,float)):
            return (float(mean), float(std))
    return (2.5, 1.0)

def adjust_game(baseline_total: float, away_wp: float, home_wp: float, away_er: Tuple[float,float], home_er: Tuple[float,float]):
    away_mean, away_std = away_er
    home_mean, home_std = home_er
    # Total adjustment: combine std & mean shifts
    total_adj = (away_std + home_std) / 8.0  # variability influence
    mean_component = ((away_mean + home_mean) - 5.0) / 20.0  # relative to nominal combined 5 ER baseline
    adjusted_total = round(baseline_total + total_adj + mean_component, 2)
    # Win prob adjustment: damp favorite if favorite std >> opponent
    favorite_is_away = away_wp > home_wp
    fav_std = away_std if favorite_is_away else home_std
    dog_std = home_std if favorite_is_away else away_std
    wp_shift = 0.0
    if fav_std - dog_std > 0.7:
        wp_shift = min(0.03, (fav_std - dog_std) * 0.015)
    # Underdog pitcher strength bonus if mean ER < opponent by 0.6+ (stability)
    und_bonus = 0.0
    if favorite_is_away:
        if home_mean + 0.6 < away_mean:
            und_bonus = min(0.02, (away_mean - home_mean - 0.6) * 0.01)
    else:
        if away_mean + 0.6 < home_mean:
            und_bonus = min(0.02, (home_mean - away_mean - 0.6) * 0.01)
    if favorite_is_away:
        away_wp_adj = max(0.5, away_wp - wp_shift - und_bonus)
        home_wp_adj = 1 - away_wp_adj
    else:
        home_wp_adj = max(0.5, home_wp - wp_shift - und_bonus)
        away_wp_adj = 1 - home_wp_adj
    return adjusted_total, away_wp_adj, home_wp_adj

def build_game_synergy(date_str: str):
    pred_doc = load_json(PREDICTIONS_FILE)
    if not pred_doc:
        return None
    games = extract_games_for_date(pred_doc, date_str)
    dist_path = os.path.join(DIST_DIR, f'pitcher_prop_distributions_{date_str.replace('-', '_')}.json')
    dist_doc = load_json(dist_path) or {}
    out_games = {}
    total_deltas = []
    wp_deltas = []
    for gkey, g in games.items():
        preds = g.get('predictions', {}) if isinstance(g, dict) else {}
        away_wp = preds.get('away_win_prob'); home_wp = preds.get('home_win_prob'); total = preds.get('predicted_total_runs')
        if not (isinstance(away_wp,(int,float)) and isinstance(home_wp,(int,float)) and isinstance(total,(int,float))):
            continue
        away_pitcher = g.get('pitcher_info', {}).get('away_pitcher_name') or g.get('away_pitcher')
        home_pitcher = g.get('pitcher_info', {}).get('home_pitcher_name') or g.get('home_pitcher')
        if not away_pitcher or not home_pitcher:
            continue
        away_er = pitcher_er_stats(dist_doc, away_pitcher)
        home_er = pitcher_er_stats(dist_doc, home_pitcher)
        adj_total, adj_away_wp, adj_home_wp = adjust_game(total, away_wp, home_wp, away_er, home_er)
        out_games[gkey] = {
            'away_team': g.get('away_team'),
            'home_team': g.get('home_team'),
            'away_pitcher': away_pitcher,
            'home_pitcher': home_pitcher,
            'baseline': {'away_win_prob': away_wp, 'home_win_prob': home_wp, 'predicted_total': total},
            'adjusted': {'away_win_prob': adj_away_wp, 'home_win_prob': adj_home_wp, 'predicted_total': adj_total},
            'deltas': {
                'away_win_prob': round(adj_away_wp - away_wp, 4),
                'home_win_prob': round(adj_home_wp - home_wp, 4),
                'predicted_total': round(adj_total - total, 3)
            }
        }
        total_deltas.append(adj_total - total)
        wp_deltas.append(abs(adj_away_wp - away_wp))
    if not out_games:
        return None
    avg_total_delta = round(sum(abs(d) for d in total_deltas)/len(total_deltas), 3) if total_deltas else 0.0
    max_wp_delta = round(max(wp_deltas), 4) if wp_deltas else 0.0
    doc = {
        'date': date_str,
        'built_at': datetime.utcnow().isoformat(),
        'games': out_games,
        'summary': {
            'games': len(out_games),
            'avg_total_abs_delta': avg_total_delta,
            'max_win_prob_delta': max_wp_delta
        }
    }
    path = os.path.join(DIST_DIR, f'pitcher_game_synergy_{date_str.replace('-', '_')}.json')
    tmp = path + '.tmp'
    os.makedirs(DIST_DIR, exist_ok=True)
    with open(tmp,'w',encoding='utf-8') as f:
        json.dump(doc,f,indent=2)
    os.replace(tmp,path)
    return doc

def main():
    from datetime import datetime as _dt
    date_str = _dt.utcnow().strftime('%Y-%m-%d')
    doc = build_game_synergy(date_str)
    if doc:
        print(f"Built synergy for {date_str}: {doc['summary']}")
    else:
        print("No synergy doc built (missing data or no games)")

if __name__ == '__main__':
    main()
