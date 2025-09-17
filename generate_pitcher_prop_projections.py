#!/usr/bin/env python3
"""Generate pitcher prop projections & recommendations.

Enhancements:
  - Dynamic edge threshold via env var PITCHER_PROPS_EDGE_THRESHOLD (default 0.5)
  - Expected Value + probability estimates per side using simple normal model
  - Include American odds for Over/Under when available
"""
import os, math, json, unicodedata
from datetime import datetime
from typing import Dict, Any, List
try:
    from pitcher_model_runtime import load_models
except Exception:
    load_models = None  # type: ignore

DEFAULT_EDGE_THRESHOLD = float(os.environ.get('PITCHER_PROPS_EDGE_THRESHOLD', 0.5))
DEFAULT_PITCHES_PER_OUT = 5.1
BLEND_KS = float(os.environ.get('PITCHER_PROPS_BLEND_KS', 0.35))  # weight toward market line for strikeouts
BLEND_OUTS = float(os.environ.get('PITCHER_PROPS_BLEND_OUTS', 0.25))  # weight toward market line for outs
SKEW_SCALE_KS = float(os.environ.get('PITCHER_PROPS_SKEW_SCALE_KS', 0.6))  # how much to adjust line toward favored side
SKEW_SCALE_OUTS = float(os.environ.get('PITCHER_PROPS_SKEW_SCALE_OUTS', 0.4))

# Enhanced pitch count modeling parameters
RECENT_WINDOW_INNINGS = 30  # innings for weighted recent form if available
MIN_IP_FOR_STABILITY = 20
MAX_PITCHES_PER_OUT = 5.8
MIN_PITCHES_PER_OUT = 4.6

STD_FACTORS = {  # crude historical dispersion approximations; may be overridden by calibration
    'strikeouts': 1.2,
    'outs': 2.0,
    'hits_allowed': 1.5,
    'walks': 1.0,
    'earned_runs': 1.2
}
KELLY_CAP = float(os.environ.get('PITCHER_PROPS_KELLY_CAP', 0.1))  # 10% default cap
OPPONENT_FACTORS_FILE = os.path.join('data', 'enhanced_features.json')
VOLATILITY_FILE = os.path.join('data', 'daily_bovada', 'pitcher_prop_volatility.json')
REALIZED_RESULTS_FILE = os.path.join('data', 'daily_bovada', 'pitcher_prop_realized_results.json')
CALIBRATION_FILE = os.path.join('data','daily_bovada','pitcher_prop_calibration_meta.json')

def normalize_name(name: str) -> str:
    try:
        text = unicodedata.normalize('NFD', name)
        text = ''.join(ch for ch in text if unicodedata.category(ch) != 'Mn')
        return text.lower().strip()
    except Exception:
        return name.lower().strip()

def load_json(path: str):
    if not os.path.exists(path):
        return None
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return None

def project_pitcher(pitcher: str, stats: Dict[str, Any], opponent: str | None = None, lines: Dict[str, Any] | None = None) -> Dict[str, float]:
    """Project per-market means for a pitcher.

    Heuristic baseline is always computed; if models are available we override
    only the markets they predict (e.g., strikeouts/outs), keeping the rest.
    """
    # Heuristic baseline first
    innings_pitched = float(stats.get('innings_pitched', 0) or 0)
    games_started = int(stats.get('games_started', 0) or 0)
    strikeouts = float(stats.get('strikeouts', 0) or 0)
    walks = float(stats.get('walks', 0) or 0)
    era = float(stats.get('era', 4.2) or 4.2)
    whip = float(stats.get('whip', 1.3) or 1.3)
    # Additional fields if present
    pitches_thrown = float(stats.get('pitches_thrown', 0) or 0)
    recent_pitches = float(stats.get('recent_pitches', 0) or 0)
    recent_outs = float(stats.get('recent_outs', 0) or 0)
    avg_pitches_per_out = None
    if pitches_thrown > 0 and innings_pitched > 0:
        try:
            avg_pitches_per_out = pitches_thrown / (innings_pitched * 3)
        except Exception:
            avg_pitches_per_out = None
    if recent_pitches > 0 and recent_outs > 0:
        try:
            recent_ppo = recent_pitches / recent_outs
            if avg_pitches_per_out:
                # Weighted blend favoring recent form modestly
                avg_pitches_per_out = 0.65 * avg_pitches_per_out + 0.35 * recent_ppo
            else:
                avg_pitches_per_out = recent_ppo
        except Exception:
            pass
    if avg_pitches_per_out is None:
        avg_pitches_per_out = DEFAULT_PITCHES_PER_OUT
    avg_pitches_per_out = max(MIN_PITCHES_PER_OUT, min(MAX_PITCHES_PER_OUT, avg_pitches_per_out))
    ip_per_start = 5.5
    if games_started > 0 and innings_pitched > 0:
        try:
            ip_per_start = max(3.5, min(7.5, innings_pitched / games_started))
        except Exception:
            pass
    outs = round(ip_per_start * 3, 1)
    k_per_inning = (strikeouts / innings_pitched) if innings_pitched > 0 else 0.95
    # Opponent adjustment: if tough lineup reduce K rate & extend ER, hits; if weak increase Ks
    if opponent:
        okey = opponent.lower().replace('_',' ')
        oinfo = OPP_CONTEXT.get(okey)
        if oinfo:
            strength = oinfo.get('strength', 0)
            # Cap strength influence
            strength = max(-1.0, min(1.0, strength))
            k_per_inning *= (1 - 0.12*strength)  # strong offense lowers pitcher K rate
            era *= (1 + 0.18*strength)          # strong offense inflates ERA expectation
            whip *= (1 + 0.10*strength)
    ks = round(k_per_inning * ip_per_start, 1)
    er_per_inning = era / 9.0
    er = round(er_per_inning * ip_per_start, 1)
    bb_per_inning = (walks / innings_pitched) if innings_pitched > 0 else 0.35
    hits_per_inning = max(0.1, whip - bb_per_inning)
    ha = round(hits_per_inning * ip_per_start, 1)
    # Pitch count: scaled by customized pitches per out, with opponent strength influencing workload risk
    opponent_factor = 0.0
    if opponent:
        okey = opponent.lower().replace('_',' ')
        oinfo = OPP_CONTEXT.get(okey)
        if oinfo:
            opponent_factor = max(-0.15, min(0.15, -0.08 * oinfo.get('strength', 0)))  # tough offense -> slight downward adjustment
    adjusted_pitches_per_out = avg_pitches_per_out * (1 + opponent_factor)
    pitch_count = round(outs * adjusted_pitches_per_out, 0)
    base = {'outs': outs,'strikeouts': ks,'earned_runs': er,'hits_allowed': ha,'walks': round(bb_per_inning * ip_per_start, 1),'pitch_count': pitch_count}

    # Attempt model-based overrides
    try:
        if load_models is not None:
            models = load_models()
            team = str(stats.get('team') or '') or None
            if models is not None:
                pred = models.predict_means(stats, team, opponent, lines=lines)
                if pred and isinstance(pred, dict):
                    if 'outs' in pred and pred['outs'] is not None:
                        base['outs'] = round(float(pred['outs']), 1)
                    if 'strikeouts' in pred and pred['strikeouts'] is not None:
                        base['strikeouts'] = round(float(pred['strikeouts']), 1)
                    # Recompute pitch_count if outs changed
                    ppo = DEFAULT_PITCHES_PER_OUT
                    try:
                        pitches_thrown = float(stats.get('pitches_thrown') or 0)
                        ip = float(stats.get('innings_pitched') or 0)
                        if pitches_thrown > 0 and ip > 0:
                            ppo = max(MIN_PITCHES_PER_OUT, min(MAX_PITCHES_PER_OUT, pitches_thrown/(ip*3)))
                    except Exception:
                        pass
                    base['pitch_count'] = round(base['outs'] * ppo, 0)
    except Exception:
        # If anything goes wrong, keep heuristic base
        pass

    # Market-informed blending: pull projections modestly toward market lines with odds skew
    try:
        if isinstance(lines, dict) and lines:
            # Helper to compute over probability from American odds
            def _prob(v):
                try:
                    if v is None:
                        return None
                    return american_to_prob(v)
                except Exception:
                    return None
            # Strikeouts
            mkt = lines.get('strikeouts') if isinstance(lines.get('strikeouts'), dict) else None
            if mkt and 'line' in mkt and base.get('strikeouts') is not None:
                try:
                    line_val = float(mkt.get('line'))
                    p_over = _prob(mkt.get('over_odds'))
                    p_under = _prob(mkt.get('under_odds'))
                    skew = 0.0
                    if p_over is not None and p_under is not None:
                        # Normalize to sum to ~1 in case of vig
                        s = p_over + p_under
                        if s > 0:
                            p_over_n = p_over / s
                            skew = p_over_n - 0.5
                    target = line_val + (skew * SKEW_SCALE_KS)
                    w = max(0.0, min(1.0, BLEND_KS))
                    base['strikeouts'] = round((1-w) * float(base['strikeouts']) + w * target, 2)
                except Exception:
                    pass
            # Outs
            mkt = lines.get('outs') if isinstance(lines.get('outs'), dict) else None
            if mkt and 'line' in mkt and base.get('outs') is not None:
                try:
                    line_val = float(mkt.get('line'))
                    p_over = _prob(mkt.get('over_odds'))
                    p_under = _prob(mkt.get('under_odds'))
                    skew = 0.0
                    if p_over is not None and p_under is not None:
                        s = p_over + p_under
                        if s > 0:
                            p_over_n = p_over / s
                            skew = p_over_n - 0.5
                    target = line_val + (skew * SKEW_SCALE_OUTS)
                    w = max(0.0, min(1.0, BLEND_OUTS))
                    base['outs'] = round((1-w) * float(base['outs']) + w * target, 2)
                except Exception:
                    pass
            # Recompute pitch_count after outs blending using best available ppo estimate
            try:
                ppo = DEFAULT_PITCHES_PER_OUT
                pitches_thrown = float(stats.get('pitches_thrown') or 0)
                ip = float(stats.get('innings_pitched') or 0)
                if pitches_thrown > 0 and ip > 0:
                    ppo = max(MIN_PITCHES_PER_OUT, min(MAX_PITCHES_PER_OUT, pitches_thrown/(ip*3)))
                base['pitch_count'] = round(base.get('outs', outs) * ppo, 0)
            except Exception:
                pass
    except Exception:
        pass

    return base

def american_to_profit_mult(odds: str):
    try:
        o = int(str(odds).replace('+',''))
        if o > 0:
            return o/100.0
        else:
            return 100.0/abs(o)
    except Exception:
        return None

def american_to_prob(odds: str):
    try:
        o = int(str(odds).replace('+',''))
        if o > 0:
            return 100/(o+100)
        else:
            return abs(o)/(abs(o)+100)
    except Exception:
        return None

def normal_cdf(x: float):
    return 0.5*(1+math.erf(x/math.sqrt(2)))

def load_volatility():
    data = load_json(VOLATILITY_FILE) or {}
    return data if isinstance(data, dict) else {}

VOL_CACHE = load_volatility()

def dynamic_std(market: str, pitcher_key: str, base: float) -> float:
    try:
        p = VOL_CACHE.get(pitcher_key, {})
        adj = p.get(market)
        if adj and isinstance(adj, dict):
            # store historical variance estimate -> std
            hv = adj.get('var')
            if hv is not None and hv >= 0:
                return max(0.4, min(3.5, hv ** 0.5))
    except Exception:
        pass
    return base

def over_probability(proj: float, line: float, market: str, pitcher_key: str = ''):
    base = CALIB_OVERRIDES.get(market) or STD_FACTORS.get(market, 1.5)
    std = dynamic_std(market, pitcher_key, base)
    return 1 - normal_cdf((line - proj)/std)

def compute_ev(proj: float, line: float, market: str, over_odds: str, under_odds: str, pitcher_key: str):
    if line is None:
        return None
    p_over = over_probability(proj, line, market, pitcher_key)
    p_under = 1 - p_over
    over_mult = american_to_profit_mult(over_odds) if over_odds else None
    under_mult = american_to_profit_mult(under_odds) if under_odds else None
    ev_over = ev_under = None
    if over_mult is not None:
        ev_over = p_over * over_mult - (1-p_over)
    if under_mult is not None:
        ev_under = p_under * under_mult - (1-p_under)
    return p_over, ev_over, ev_under

def build_team_map(games_data) -> Dict[str, Dict[str, str]]:
    mapping = {}
    if isinstance(games_data, list):
        iterable = games_data
    else:
        iterable = games_data.get('games', {}).values() if isinstance(games_data, dict) else []
    for g in iterable:
        away_p = g.get('away_pitcher') or g.get('away_pitcher_name') or g.get('pitcher_info', {}).get('away_pitcher_name')
        home_p = g.get('home_pitcher') or g.get('home_pitcher_name') or g.get('pitcher_info', {}).get('home_pitcher_name')
        away_team = g.get('away_team')
        home_team = g.get('home_team')
        if away_p and away_team and home_team:
            mapping[normalize_name(away_p)] = {'team': away_team, 'opponent': home_team}
        if home_p and away_team and home_team:
            mapping[normalize_name(home_p)] = {'team': home_team, 'opponent': away_team}
    return mapping

def kelly_fraction(p: float, odds: str):
    try:
        o = int(str(odds).replace('+',''))
        if o > 0:
            b = o/100.0
        else:
            b = 100.0/abs(o)
        q = 1-p
        f = (b*p - q)/b
        if f < 0:
            return 0.0
        return min(f, KELLY_CAP)
    except Exception:
        return 0.0

def load_opponent_context():
    data = load_json(OPPONENT_FACTORS_FILE) or {}
    team_ratings = data.get('team_ratings', {}) if isinstance(data, dict) else {}
    ctx = {}
    for team, meta in team_ratings.items():
        try:
            elo = float(meta.get('elo_rating', 1500))
            games = int(meta.get('games_played', 0) or 0)
            # Derive rough offensive strength scalar: >1500 => tougher matchup
            strength = (elo - 1500)/400.0  # ~ +/-1.25 at extremes
            recent_form = float(meta.get('recent_form', 0) or 0)
            # Decay: recent_form modifies strength modestly
            strength += (recent_form/100.0)*0.15
            ctx[team.lower().replace('_',' ')] = {
                'elo': elo,
                'games': games,
                'strength': strength
            }
        except Exception:
            continue
    return ctx

def load_calibration_overrides():
    meta = load_json(CALIBRATION_FILE) or {}
    mk = meta.get('markets', {}) if isinstance(meta, dict) else {}
    overrides = {}
    for m, info in mk.items():
        if isinstance(info, dict) and 'suggested_std' in info:
            overrides[m] = info['suggested_std']
    return overrides

CALIB_OVERRIDES = load_calibration_overrides()
OPP_CONTEXT = load_opponent_context()

def main():
    date_str = datetime.now().strftime('%Y-%m-%d')
    date_us = date_str.replace('-', '_')
    props_path = os.path.join('data', 'daily_bovada', f'bovada_pitcher_props_{date_us}.json')
    stats_path = os.path.join('data', 'master_pitcher_stats.json')
    games_path = os.path.join('data', f'games_{date_str}.json')
    out_path = os.path.join('data', 'daily_bovada', f'pitcher_prop_recommendations_{date_us}.json')

    props_data = load_json(props_path) or {}
    pitcher_props = props_data.get('pitcher_props', {}) if isinstance(props_data, dict) else {}
    stats_data = load_json(stats_path) or {}
    if 'pitcher_data' in stats_data:
        stats_data = stats_data['pitcher_data']
    elif 'refresh_info' in stats_data and 'pitcher_data' in stats_data['refresh_info']:
        stats_data = stats_data['refresh_info']['pitcher_data']
    games_data = load_json(games_path) or []
    team_map = build_team_map(games_data)

    recommendations: List[Dict[str, Any]] = []

    # Index stats by name once
    by_name = {}
    for pid, pdata in stats_data.items():
        name = str(pdata.get('name','')).strip()
        if name:
            by_name[normalize_name(name)] = pdata

    for p_key, markets in pitcher_props.items():
        st = by_name.get(p_key, {})
        team_info = team_map.get(p_key, {'team': None, 'opponent': None})
        opponent = team_info.get('opponent')
        proj = project_pitcher(p_key, st, opponent, lines=markets)
        plays = []
        for market_key in ['strikeouts', 'outs', 'hits_allowed', 'walks', 'earned_runs']:
            mkt = markets.get(market_key)
            if not isinstance(mkt, dict):
                continue
            line_val = mkt.get('line')
            if line_val is None:
                continue
            proj_val = proj.get(market_key)
            if proj_val is None:
                continue
            edge = round(proj_val - float(line_val), 2)
            side = None
            if edge >= DEFAULT_EDGE_THRESHOLD:
                side = 'OVER'
            elif edge <= -DEFAULT_EDGE_THRESHOLD:
                side = 'UNDER'
            p_over, ev_over, ev_under = compute_ev(proj_val, line_val, market_key, mkt.get('over_odds'), mkt.get('under_odds'), p_key)
            if side:
                selected_ev = ev_over if side == 'OVER' else ev_under
                # Kelly sizing (prob use p_over for OVER else 1-p_over)
                if p_over is not None:
                    if side == 'OVER':
                        kelly = kelly_fraction(p_over, mkt.get('over_odds'))
                    else:
                        kelly = kelly_fraction(1-p_over, mkt.get('under_odds'))
                else:
                    kelly = 0.0
                confidence = 'HIGH' if abs(edge) >= 1.5 else ('MEDIUM' if abs(edge) >= 1.0 else 'LOW')
                plays.append({
                    'market': market_key,
                    'side': side,
                    'line': line_val,
                    'proj': proj_val,
                    'edge': edge,
                    'confidence': confidence,
                    'p_over': round(p_over,3) if p_over is not None else None,
                    'ev_over': round(ev_over,3) if ev_over is not None else None,
                    'ev_under': round(ev_under,3) if ev_under is not None else None,
                    'selected_ev': round(selected_ev,3) if selected_ev is not None else None,
                    'over_odds': mkt.get('over_odds'),
                    'under_odds': mkt.get('under_odds'),
                    'kelly_fraction': round(kelly,4)
                })
        if plays:
            recommendations.append({
                'pitcher_key': p_key,
                'pitcher': p_key,
                'team': team_info['team'],
                'opponent': team_info['opponent'],
                'opponent_strength': OPP_CONTEXT.get((team_info.get('opponent') or '').lower().replace('_',' '), {}).get('strength'),
                'projections': proj,
                'plays': plays
            })
    payload = {'date': date_str,'generated_at': datetime.utcnow().isoformat(),'edge_threshold_used': DEFAULT_EDGE_THRESHOLD,'kelly_cap': KELLY_CAP,'blend': {'ks': BLEND_KS, 'outs': BLEND_OUTS, 'skew_scale_ks': SKEW_SCALE_KS, 'skew_scale_outs': SKEW_SCALE_OUTS},'count': len(recommendations),'recommendations': recommendations}
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(payload, f, indent=2)
    print(f"Saved pitcher prop recommendations: {out_path} (plays for {len(recommendations)} pitchers)")
    return True

if __name__ == '__main__':
    main()
