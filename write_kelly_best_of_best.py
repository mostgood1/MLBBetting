#!/usr/bin/env python3
"""
Daily writer for Kelly "Best of Best" bets.
- Reads betting_recommendations_<DATE>.json and real_betting_lines_<DATE>.json from data/
- Computes Kelly percentage, suggested bet, and determines outcomes using final scores
- Appends normalized entries to data/kelly_betting_recommendations.json with deduping

Run without args to process yesterday; or pass --date YYYY-MM-DD.
"""

import json
import os
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Any

# Prefer local analyzer to load final scores and persist bundle
from comprehensive_historical_analysis import ComprehensiveHistoricalAnalyzer

BASE_PATH = Path(__file__).parent
DATA_DIR = BASE_PATH / 'data'
KELLY_FILE = DATA_DIR / 'kelly_betting_recommendations.json'

KELLY_START_DATE = '2025-08-27'


def _parse_args():
    import argparse
    p = argparse.ArgumentParser(description='Write Kelly Best of Best entries for a date')
    p.add_argument('--date', help='Target date YYYY-MM-DD (default: yesterday)')
    return p.parse_args()


def _american_to_profit_multiplier(odds: int) -> float:
    if odds is None:
        return 0.91  # default approx for -110
    if odds > 0:
        return odds / 100.0
    else:
        return 100.0 / abs(odds)


def _calc_kelly_fraction(p: float, odds: int) -> float:
    # If odds unknown, assume -110
    if odds is None:
        odds = -110
    b = _american_to_profit_multiplier(odds)
    q = 1 - p
    # Kelly for decimal b: f* = (bp - q) / b
    try:
        f = (b * p - q) / b
    except ZeroDivisionError:
        return 0.0
    return max(0.0, min(f, 0.25))


def _moneyline_pick_wins(pick: str, away: int, home: int) -> bool:
    if pick == 'away':
        return away > home
    if pick == 'home':
        return home > away
    return False


def _total_pick_wins(total_details: str, away: int, home: int) -> str:
    # Returns 'win' | 'loss' | 'push'
    try:
        parts = total_details.strip().split()
        if len(parts) < 2:
            return 'loss'
        side = parts[0].lower()  # over/under
        line = float(parts[1])
        total = away + home
        if total > line and side == 'over':
            return 'win'
        if total < line and side == 'under':
            return 'win'
        if abs(total - line) < 1e-9:
            return 'push'
        return 'loss'
    except Exception:
        return 'loss'


def _runline_pick_wins(details: str, away: int, home: int) -> bool:
    # details examples: "home -1.5", "away +1.5"
    try:
        parts = details.strip().split()
        if len(parts) < 2:
            return False
        side = parts[0].lower()
        line = float(parts[1])
        margin = home - away  # positive means home won by margin
        if side == 'home':
            return margin > line
        else:
            # away side wins with spread if away loses by less than |line| or wins outright
            return (-margin) > line
    except Exception:
        return False


def _normalize_game_key(game_key: str) -> str:
    # Accepts either "Away @ Home" or "Away_vs_Home"; returns "Away vs Home"
    if '_vs_' in game_key:
        a, h = game_key.split('_vs_')
        return f"{a} vs {h}"
    if ' @ ' in game_key:
        a, h = game_key.split(' @ ')
        return f"{a} vs {h}"
    if ' vs ' in game_key:
        return game_key
    return game_key.replace('_', ' ')


def _load_json(path: Path) -> Any:
    if not path.exists():
        return None
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def _save_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)


def build_kelly_entries_for_date(date_str: str) -> List[Dict[str, Any]]:
    # Load input data
    date_underscore = date_str.replace('-', '_')
    bets_path = DATA_DIR / f"betting_recommendations_{date_underscore}.json"
    lines_path = DATA_DIR / f"real_betting_lines_{date_underscore}.json"

    bets = _load_json(bets_path) or {}
    lines = _load_json(lines_path) or {}

    games = bets.get('games', {}) if isinstance(bets, dict) else {}

    # Load final scores via analyzer (fetches or caches automatically)
    analyzer = ComprehensiveHistoricalAnalyzer()
    final_scores = analyzer.load_final_scores_for_date(date_str) or {}

    results: List[Dict[str, Any]] = []

    for game_key, game_data in games.items():
        # Determine a normalized key to find final scores
        away = game_data.get('away_team') or game_key.split(' @ ')[0] if ' @ ' in game_key else ''
        home = game_data.get('home_team') or game_key.split(' @ ')[1] if ' @ ' in game_key else ''
        norm_key_vs = f"{away} vs {home}" if away and home else _normalize_game_key(game_key)
        fs = final_scores.get(norm_key_vs) or final_scores.get(f"{home} vs {away}")
        away_score = (fs or {}).get('away_score')
        home_score = (fs or {}).get('home_score')

        recs = game_data.get('betting_recommendations', {})
        if not isinstance(recs, dict):
            continue

        # Inspect supported bet types
        for rtype, rec in recs.items():
            try:
                if not isinstance(rec, dict):
                    continue
                # Only include if Kelly fraction is present or computable
                kf = rec.get('kelly_fraction')
                odds = rec.get('odds') or rec.get('american_odds')
                # Pull probability based on type for Kelly calc if needed
                win_prob = None
                bet_type = None
                bet_details = None

                if rtype == 'moneyline':
                    bet_type = 'Moneyline'
                    side = rec.get('pick') or rec.get('side')
                    if not side:
                        continue
                    bet_details = side
                    win_prob = rec.get('win_probability')
                elif rtype == 'total':
                    bet_type = 'Over/Under'
                    side = 'Over' if rec.get('recommendation', '').upper().startswith('OVER') or rec.get('side', '').lower() == 'over' else 'Under'
                    line = rec.get('line') or rec.get('total_line') or rec.get('betting_line')
                    if not line:
                        continue
                    bet_details = f"{side} {line}"
                    win_prob = rec.get('over_probability') if side.lower() == 'over' else rec.get('under_probability')
                elif rtype == 'run_line':
                    bet_type = 'Run Line'
                    side = rec.get('side') or rec.get('pick')
                    line = rec.get('line')
                    if not side or line is None:
                        continue
                    bet_details = f"{side} {line}"
                    win_prob = rec.get('cover_probability')
                else:
                    continue

                if kf is None:
                    if isinstance(win_prob, (int, float)):
                        # If stored as 0..1 or percentage
                        p = float(win_prob)
                        if p > 1:
                            p = p / 100.0
                        kf = _calc_kelly_fraction(p, int(odds) if odds is not None else None)
                    else:
                        continue
                else:
                    # Might be provided in 0..1
                    if kf > 1.0:
                        # Already percent 0..100? scale
                        kf = kf / 100.0

                # Filter for "Best of Best" – require at least 10% Kelly
                if kf < 0.10:
                    continue

                # Suggested bet using $1000 notional bankroll, cap at $200
                suggested = int(min(round(kf * 1000 / 10) * 10, 200))
                if suggested < 10:
                    suggested = 10

                outcome = 'pending'
                profit_loss = 0.0
                roi = 0.0
                if isinstance(away_score, int) and isinstance(home_score, int):
                    if bet_type == 'Moneyline':
                        won = _moneyline_pick_wins(bet_details.lower(), away_score, home_score)
                        outcome = 'win' if won else 'loss'
                    elif bet_type == 'Over/Under':
                        res = _total_pick_wins(bet_details, away_score, home_score)
                        if res == 'push':
                            outcome = 'push'
                        else:
                            outcome = 'win' if res == 'win' else 'loss'
                    elif bet_type == 'Run Line':
                        won = _runline_pick_wins(bet_details, away_score, home_score)
                        outcome = 'win' if won else 'loss'

                    if outcome == 'win':
                        mult = _american_to_profit_multiplier(int(odds) if odds is not None else -110)
                        profit_loss = suggested * mult
                    elif outcome == 'loss':
                        profit_loss = -suggested
                    else:
                        profit_loss = 0.0
                    roi = (profit_loss / suggested * 100.0) if suggested > 0 else 0.0

                results.append({
                    'date': date_str,
                    'game': _normalize_game_key(game_key),
                    'bet_type': bet_type,
                    'bet_details': bet_details,
                    'confidence': round(kf, 3),  # decimal 0..1
                    'kelly_percentage': round(kf * 100, 1),
                    'recommended_bet': suggested,
                    'odds': int(odds) if odds is not None else -110,
                    'outcome': outcome,
                    'profit_loss': round(profit_loss, 2),
                    'roi': round(roi, 2)
                })
            except Exception:
                # Skip malformed entries
                continue

    return results


def write_for_date(date_str: str) -> Dict[str, Any]:
    if date_str < KELLY_START_DATE:
        return {'success': True, 'written': 0, 'skipped_reason': 'before_start_date'}

    new_entries = build_kelly_entries_for_date(date_str)

    existing: List[Dict[str, Any]] = []
    if KELLY_FILE.exists():
        try:
            existing = _load_json(KELLY_FILE) or []
        except Exception:
            existing = []

    # Dedup by (date, game, bet_type, bet_details)
    sig = {(e.get('date'), e.get('game'), e.get('bet_type'), e.get('bet_details')) for e in existing}
    appended = 0
    for e in new_entries:
        key = (e.get('date'), e.get('game'), e.get('bet_type'), e.get('bet_details'))
        if key in sig:
            continue
        existing.append(e)
        sig.add(key)
        appended += 1

    _save_json(KELLY_FILE, existing)
    return {'success': True, 'written': appended, 'total': len(existing)}


def main():
    args = _parse_args()
    if args.date:
        target_date = args.date
    else:
        # Yesterday by default
        target_date = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')

    result = write_for_date(target_date)
    print(json.dumps({'date': target_date, **result}))
    return 0 if result.get('success') else 1


if __name__ == '__main__':
    raise SystemExit(main())
