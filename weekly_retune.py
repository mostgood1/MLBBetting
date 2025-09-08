"""Weekly retuning helper script.

Uses last 7 completed days (excluding today if games still in progress) to run the
comprehensive optimization in a constrained window. Produces a timestamped
config and a comparison summary vs current active comprehensive_optimized_config.json.
"""
from datetime import datetime, timedelta
import json
import os
from comprehensive_model_retuner import AdvancedModelRetuner
from typing import Dict, Any, List

DATA_DIR = "data"


def get_last_completed_days(n: int = 7):
    today = datetime.now().date()
    # Assume yesterday is last completed; adjust if final_scores for today exist
    days = []
    cursor = today - timedelta(days=1)
    while len(days) < n:
        days.append(cursor)
        cursor -= timedelta(days=1)
    return list(reversed(days))  # chronological


def load_existing_config(path: str):
    if not os.path.exists(path):
        return None
    try:
        with open(path, 'r') as f:
            return json.load(f)
    except Exception:
        return None


def extract_key_metrics(cfg: dict):
    if not cfg:
        return {}
    meta = cfg.get("optimization_metadata", {})
    perf = meta.get("performance_metrics", {})
    eng = cfg.get("engine_parameters", {})
    return {
        "optimization_date": meta.get("optimization_date"),
        "games_analyzed": meta.get("games_analyzed"),
        "home_accuracy": perf.get("home_accuracy"),
        "total_runs_mae": perf.get("total_runs_mae"),
        "scoring_bias": perf.get("scoring_bias"),
        "home_bias": perf.get("home_bias"),
        "base_lambda": eng.get("base_lambda"),
        "home_field_advantage": eng.get("home_field_advantage"),
        "total_scoring_adjustment": eng.get("total_scoring_adjustment"),
        "run_environment": eng.get("run_environment"),
    }


 # -------------------- Utility Functions (moved above main) --------------------

def aggregate_roi_metrics(last_days: List[datetime.date]) -> Dict[str, Any]:
    """Compute ROI by bet type & confidence using betting_recommendations + final_scores.

    Assumptions:
      - Stake sizing fixed: HIGH=100, MEDIUM=50, LOW=25
      - American odds determine payout (standard US odds)
      - Push returns stake (profit 0)
    """
    stake_by_conf = { 'high': 100.0, 'medium': 50.0, 'low': 25.0 }
    # Aggregation containers
    by_conf: Dict[str, Dict[str, float]] = {}
    by_type_conf: Dict[str, Dict[str, Dict[str, float]]] = {}

    def init_conf(d: Dict[str, float]):
        d.setdefault('bets', 0)
        d.setdefault('wins', 0)
        d.setdefault('losses', 0)
        d.setdefault('pushes', 0)
        d.setdefault('total_stake', 0.0)
        d.setdefault('total_profit', 0.0)

    for d in last_days:
        date_us = d.strftime('%Y_%m_%d')
        date_dash = d.strftime('%Y-%m-%d')
        rec_path = os.path.join(DATA_DIR, f'betting_recommendations_{date_us}.json')
        scores_path = os.path.join(DATA_DIR, f'final_scores_{date_us}.json')
        if not os.path.exists(rec_path) or not os.path.exists(scores_path):
            continue
        try:
            with open(rec_path, 'r') as f:
                rec_data = json.load(f)
            with open(scores_path, 'r') as f:
                score_data = json.load(f)
        except Exception:
            continue

        # Normalize final scores into list of dicts
        games_scores = []
        if isinstance(score_data, dict):
            gobj = score_data.get('games', score_data)
            if isinstance(gobj, dict):
                for gk, g in gobj.items():
                    games_scores.append({
                        'away_team': g.get('away_team') or (gk.split(' vs ')[0] if ' vs ' in gk else None),
                        'home_team': g.get('home_team') or (gk.split(' vs ')[1] if ' vs ' in gk else None),
                        'away_score': g.get('away_score', 0),
                        'home_score': g.get('home_score', 0)
                    })
            elif isinstance(gobj, list):
                games_scores = gobj
        elif isinstance(score_data, list):
            games_scores = score_data

        # Build lookup
        score_lookup = {}
        for g in games_scores:
            try:
                key = f"{g['away_team']}__{g['home_team']}".lower()
                score_lookup[key] = g
            except Exception:
                continue

        games = rec_data.get('games', {})
        for game_id, gdata in games.items():
            away = gdata.get('away_team')
            home = gdata.get('home_team')
            if not away or not home:
                continue
            key = f"{away}__{home}".lower()
            score = score_lookup.get(key)
            if not score:
                continue  # can't settle
            total_runs = 0
            try:
                total_runs = int(score.get('away_score', 0)) + int(score.get('home_score', 0))
            except Exception:
                continue
            home_won = int(score.get('home_score', 0)) > int(score.get('away_score', 0))

            value_bets = gdata.get('value_bets', []) or []
            for vb in value_bets:
                conf = str(vb.get('confidence', '')).lower()
                bet_type = vb.get('type', 'unknown')
                if conf not in stake_by_conf:
                    continue
                stake = stake_by_conf[conf]
                rec_str = vb.get('recommendation', '')
                american = str(vb.get('american_odds', '')).strip()
                # Normalize american odds
                if american and american[0] not in ['+','-']:
                    try:
                        # treat bare number as positive odds
                        int_val = int(american)
                        if int_val > 0:
                            american = f"+{int_val}"
                        else:
                            american = str(int_val)
                    except Exception:
                        american = '+100'

                # Determine outcome
                result = None  # 'win','loss','push'
                if bet_type == 'total':
                    line_val = None
                    if rec_str:
                        parts = rec_str.split()
                        # Expect Over 9.5 or Under 8.5
                        if len(parts) >= 2:
                            side = parts[0].lower()
                            try:
                                line_val = float(parts[1])
                            except Exception:
                                line_val = None
                            if line_val is not None:
                                if total_runs == line_val:
                                    result = 'push'
                                elif side == 'over':
                                    result = 'win' if total_runs > line_val else 'loss'
                                elif side == 'under':
                                    result = 'win' if total_runs < line_val else 'loss'
                    if result is None:
                        continue  # skip if parse failed
                elif bet_type == 'moneyline':
                    # Recommendation like "Texas Rangers ML"
                    team_pick = rec_str.replace(' ML','').strip()
                    if not team_pick:
                        continue
                    # Determine winner
                    winner = home if home_won else away
                    loser = away if home_won else home
                    if team_pick == winner:
                        result = 'win'
                    elif team_pick == loser:
                        result = 'loss'
                    else:
                        continue  # mismatch / unknown
                else:
                    continue  # unsupported bet type for ROI

                # Compute profit
                profit = 0.0
                if result == 'win':
                    profit = payout_profit(stake, american)
                elif result == 'loss':
                    profit = -stake
                elif result == 'push':
                    profit = 0.0

                # Aggregate by confidence
                c_entry = by_conf.setdefault(conf, {})
                init_conf(c_entry)
                c_entry['bets'] += 1
                c_entry['total_stake'] += stake
                c_entry['total_profit'] += profit
                key_map = {'win':'wins','loss':'losses','push':'pushes'}
                c_entry[key_map[result]] += 1  # wins/losses/pushes

                # Aggregate by bet type & confidence
                t_conf = by_type_conf.setdefault(bet_type, {}).setdefault(conf, {})
                init_conf(t_conf)
                t_conf['bets'] += 1
                t_conf['total_stake'] += stake
                t_conf['total_profit'] += profit
                t_conf[key_map[result]] += 1
        # end games loop

    # Finalize ROI ratios
    for conf, d in by_conf.items():
        if d['total_stake']:
            d['roi'] = round(d['total_profit'] / d['total_stake'], 4)
            d['efficiency'] = round(d['total_profit'] / (d['total_stake'] ** 0.5), 6)
        else:
            d['roi'] = 0.0
            d['efficiency'] = 0.0
    for btype, conf_map in by_type_conf.items():
        for conf, d in conf_map.items():
            if d['total_stake']:
                d['roi'] = round(d['total_profit'] / d['total_stake'], 4)
                d['efficiency'] = round(d['total_profit'] / (d['total_stake'] ** 0.5), 6)
            else:
                d['roi'] = 0.0
                d['efficiency'] = 0.0

    # Kelly vs Fixed Stake comparison (approximation using same outcomes but different staking)
    # Fixed stake: treat every bet as LOW stake for baseline
    total_kelly_profit = 0.0
    total_fixed_profit = 0.0
    total_kelly_stake = 0.0
    total_fixed_stake = 0.0
    # Recompute quickly by iterating again
    for d in last_days:
        date_us = d.strftime('%Y_%m_%d')
        rec_path = os.path.join(DATA_DIR, f'betting_recommendations_{date_us}.json')
        scores_path = os.path.join(DATA_DIR, f'final_scores_{date_us}.json')
        if not (os.path.exists(rec_path) and os.path.exists(scores_path)):
            continue
        try:
            with open(rec_path,'r') as f: rec_data = json.load(f)
            with open(scores_path,'r') as f: score_data = json.load(f)
        except Exception:
            continue
        games_scores = []
        if isinstance(score_data, dict):
            gobj = score_data.get('games', score_data)
            if isinstance(gobj, dict):
                for gk,g in gobj.items():
                    games_scores.append({
                        'away_team': g.get('away_team') or (gk.split(' vs ')[0] if ' vs ' in gk else None),
                        'home_team': g.get('home_team') or (gk.split(' vs ')[1] if ' vs ' in gk else None),
                        'away_score': g.get('away_score', 0),
                        'home_score': g.get('home_score', 0)
                    })
            elif isinstance(gobj, list):
                games_scores = gobj
        elif isinstance(score_data, list):
            games_scores = score_data
        score_lookup = {}
        for g in games_scores:
            try:
                k = f"{g['away_team']}__{g['home_team']}".lower()
                score_lookup[k] = g
            except Exception:
                continue
        games = rec_data.get('games', {})
        for _, gdata in games.items():
            away = gdata.get('away_team'); home = gdata.get('home_team')
            if not away or not home: continue
            score = score_lookup.get(f"{away}__{home}".lower())
            if not score: continue
            total_runs = int(score.get('away_score',0)) + int(score.get('home_score',0))
            home_won = int(score.get('home_score',0)) > int(score.get('away_score',0))
            for vb in gdata.get('value_bets', []) or []:
                conf = str(vb.get('confidence','')).lower()
                if conf not in stake_by_conf: continue
                bet_type = vb.get('type','')
                rec_str = vb.get('recommendation','')
                american = str(vb.get('american_odds','')).strip()
                if american and american[0] not in ['+','-']:
                    try:
                        iv = int(american); american = f"+{iv}" if iv>0 else str(iv)
                    except Exception:
                        american = '+100'
                result = None
                if bet_type == 'total':
                    parts = rec_str.split()
                    if len(parts)>=2:
                        side = parts[0].lower()
                        try: line_val = float(parts[1])
                        except: line_val=None
                        if line_val is not None:
                            if total_runs == line_val: result='push'
                            elif side=='over': result='win' if total_runs>line_val else 'loss'
                            elif side=='under': result='win' if total_runs<line_val else 'loss'
                elif bet_type=='moneyline':
                    team_pick = rec_str.replace(' ML','').strip()
                    winner = home if home_won else away
                    loser = away if home_won else home
                    if team_pick==winner: result='win'
                    elif team_pick==loser: result='loss'
                if result is None: continue
                kelly_stake = stake_by_conf[conf]
                fixed_stake = stake_by_conf['low']  # baseline
                if result=='win':
                    kelly_profit = payout_profit(kelly_stake, american)
                    fixed_profit = payout_profit(fixed_stake, american)
                elif result=='loss':
                    kelly_profit = -kelly_stake
                    fixed_profit = -fixed_stake
                else:
                    kelly_profit = fixed_profit = 0.0
                total_kelly_profit += kelly_profit
                total_fixed_profit += fixed_profit
                total_kelly_stake += kelly_stake
                total_fixed_stake += fixed_stake
    kelly_comp = None
    if total_kelly_stake>0 and total_fixed_stake>0:
        kelly_comp = {
            'kelly_profit': round(total_kelly_profit,2),
            'kelly_stake': round(total_kelly_stake,2),
            'kelly_roi': round(total_kelly_profit/total_kelly_stake,4),
            'fixed_profit': round(total_fixed_profit,2),
            'fixed_stake': round(total_fixed_stake,2),
            'fixed_roi': round(total_fixed_profit/total_fixed_stake,4)
        }

    return {
        'by_confidence': by_conf,
        'by_type_confidence': by_type_conf,
        'stake_model': stake_by_conf,
        'days': [d.isoformat() for d in last_days],
        'kelly_comparison': kelly_comp
    }


def payout_profit(stake: float, american: str) -> float:
    """Return profit (excluding returned stake) for a winning wager at given American odds."""
    try:
        if not american:
            return stake  # assume even
        american = american.strip()
        if american[0] == '+':
            val = int(american[1:])
            return stake * (val / 100.0)
        elif american[0] == '-':
            val = int(american[1:])
            return stake * (100.0 / val)
        else:
            # treat as positive
            val = int(american)
            if val > 0:
                return stake * (val / 100.0)
            else:
                val = abs(val)
                return stake * (100.0 / val) if val else stake
    except Exception:
        return stake


def update_optimization_history(last_days: List[datetime.date], new_cfg: Dict[str, Any], roi_metrics: Dict[str, Any]):
    """Append latest optimization snapshot to rolling 4-week history file."""
    history_path = os.path.join(DATA_DIR, 'optimization_history.json')
    history: List[Dict[str, Any]] = []
    if os.path.exists(history_path):
        try:
            with open(history_path, 'r') as f:
                history = json.load(f)
                if not isinstance(history, list):
                    history = []
        except Exception:
            history = []

    meta = (new_cfg or {}).get('optimization_metadata', {})
    perf = meta.get('performance_metrics', {})
    event = {
        'timestamp': meta.get('optimization_date'),
        'window_start': last_days[0].isoformat(),
        'window_end': last_days[-1].isoformat(),
        'games_analyzed': meta.get('games_analyzed'),
        'performance': perf,
        'roi_metrics': roi_metrics
    }
    history.append(event)

    # Keep only events within last 28 days (4-week) or last 40 entries as hard cap
    try:
        cutoff = datetime.now() - timedelta(days=28)
        filtered = []
        for ev in history:
            ts = ev.get('timestamp')
            dt_obj = None
            if ts:
                try:
                    dt_obj = datetime.fromisoformat(ts)
                except Exception:
                    dt_obj = None
            if dt_obj is None or dt_obj >= cutoff:
                filtered.append(ev)
        history = filtered[-40:]
    except Exception:
        # Fallback: enforce length only
        history = history[-40:]

    try:
        with open(history_path, 'w') as f:
            json.dump(history, f, indent=2)
    except Exception:
        pass

def main():
    print("🏁 Weekly Retune Starting")
    last_days = get_last_completed_days(7)
    print("Using days:", ", ".join(d.strftime('%Y-%m-%d') for d in last_days))

    existing_cfg_path = os.path.join(DATA_DIR, 'comprehensive_optimized_config.json')
    old_cfg = load_existing_config(existing_cfg_path)
    old_metrics = extract_key_metrics(old_cfg)

    # Run retuner restricted to 7 days
    retuner = AdvancedModelRetuner(data_dir=DATA_DIR)
    retuner.run_comprehensive_optimization(days_back=7)

    # Load new config
    new_cfg = load_existing_config(os.path.join(DATA_DIR, 'comprehensive_optimized_config.json'))
    new_metrics = extract_key_metrics(new_cfg)

    # Aggregate ROI metrics
    roi_metrics = aggregate_roi_metrics(last_days)

    if new_cfg is not None:
        meta = new_cfg.setdefault('optimization_metadata', {})
        meta['roi_metrics'] = roi_metrics
        with open(os.path.join(DATA_DIR, 'comprehensive_optimized_config.json'), 'w') as f:
            json.dump(new_cfg, f, indent=2)

    update_optimization_history(last_days, new_cfg, roi_metrics)

    comparison = {
        "window_start": last_days[0].isoformat(),
        "window_end": last_days[-1].isoformat(),
        "previous": old_metrics,
        "new": new_metrics,
        "roi_metrics": roi_metrics,
    }

    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    out_file = os.path.join(DATA_DIR, f"weekly_retune_comparison_{ts}.json")
    with open(out_file, 'w') as f:
        json.dump(comparison, f, indent=2)
    print(f"📄 Comparison saved: {out_file}")
    print("Previous vs New Metrics:")
    print(json.dumps(comparison, indent=2))

if __name__ == '__main__':
    main()
