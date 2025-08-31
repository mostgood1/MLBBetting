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
from typing import Dict, List, Any, Optional, Tuple

# Prefer local analyzer to load final scores and persist bundle
from comprehensive_historical_analysis import ComprehensiveHistoricalAnalyzer

BASE_PATH = Path(__file__).parent
DATA_DIR = BASE_PATH / 'data'
KELLY_FILE = DATA_DIR / 'kelly_betting_recommendations.json'
DAILY_KELLY_DIR = DATA_DIR / 'kelly_daily'

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


def _parse_american_odds(odds_val: Any) -> Optional[int]:
    """Parse American odds from str/int; returns int or None."""
    if odds_val is None:
        return None
    try:
        if isinstance(odds_val, (int, float)):
            return int(odds_val)
        s = str(odds_val).strip()
        if s.startswith('+'):
            s = s[1:]
        return int(s)
    except Exception:
        return None


def _parse_total_recommendation(rec: Dict[str, Any]) -> Tuple[Optional[str], Optional[float]]:
    """Extract (side, line) from a total-type recommendation."""
    side = None
    line_val: Optional[float] = None
    # Try structured fields first
    if rec.get('side'):
        side = str(rec['side']).title()
    if rec.get('line') is not None:
        try:
            line_val = float(rec['line'])
        except Exception:
            line_val = None
    if line_val is None and rec.get('total_line') is not None:
        try:
            line_val = float(rec['total_line'])
        except Exception:
            line_val = None
    if line_val is None and rec.get('betting_line') is not None:
        try:
            line_val = float(rec['betting_line'])
        except Exception:
            line_val = None

    # Parse from free-text recommendation if needed: e.g., "Under 9.0" or "Over 7.5"
    if (not side or line_val is None) and rec.get('recommendation'):
        try:
            parts = str(rec['recommendation']).strip().split()
            if len(parts) >= 2:
                side = side or parts[0].title()
                if line_val is None:
                    line_val = float(parts[1])
        except Exception:
            pass
    return side, line_val


def _normalize_team_for_lines(name: str) -> str:
    """Map shorthand or ambiguous team names to the full names used in real_betting_lines keys."""
    if not name:
        return name
    mapping = {
        # Common aliases to sportsbook-style names
        "Athletics": "Oakland Athletics",
        "A's": "Oakland Athletics",
        "Guardians": "Cleveland Guardians",
        "Indians": "Cleveland Guardians",
        "White Sox": "Chicago White Sox",
        "Red Sox": "Boston Red Sox",
        "D-backs": "Arizona Diamondbacks",
        "Dbacks": "Arizona Diamondbacks",
        "Yanks": "New York Yankees",
        "Yankees": "New York Yankees",
        "Mets": "New York Mets",
        "Pads": "San Diego Padres",
        "Cards": "St. Louis Cardinals",
        "Bravos": "Atlanta Braves",
        "Dodgers": "Los Angeles Dodgers",
        "Angels": "Los Angeles Angels",
        "Rays": "Tampa Bay Rays",
        "Nats": "Washington Nationals",
        "D-Backs": "Arizona Diamondbacks",
    }
    return mapping.get(name, name)


def _find_real_totals_for_game(lines_data: Dict[str, Any], away_team: str, home_team: str) -> Tuple[Optional[float], Optional[int], Optional[int]]:
    """Given the real_betting_lines JSON and teams, return (line, over_odds, under_odds) if found.
    Tries multiple key formats and basic normalization.
    """
    if not isinstance(lines_data, dict):
        return None, None, None
    book_lines = lines_data.get('lines') if 'lines' in lines_data else lines_data
    if not isinstance(book_lines, dict):
        return None, None, None

    a = _normalize_team_for_lines(away_team)
    h = _normalize_team_for_lines(home_team)

    candidate_keys = [
        f"{a} @ {h}",
        f"{away_team} @ {home_team}",
        f"{a} at {h}",
        f"{away_team} at {home_team}",
        f"{away_team} @ {h}",
        f"{a} @ {home_team}",
    ]

    game_obj = None
    for k in candidate_keys:
        if k in book_lines:
            game_obj = book_lines.get(k)
            break

    # Heuristic fallback: scan for a key containing both team tokens
    if game_obj is None:
        for k, v in book_lines.items():
            if isinstance(k, str) and (a in k or away_team in k) and (h in k or home_team in k):
                game_obj = v
                break

    if not isinstance(game_obj, dict):
        return None, None, None

    # Prefer explicit total_runs structure
    if 'total_runs' in game_obj and isinstance(game_obj['total_runs'], dict):
        tr = game_obj['total_runs']
        line = tr.get('line')
        over = tr.get('over')
        under = tr.get('under')
        try:
            return (float(line) if line is not None else None,
                    int(over) if over is not None else None,
                    int(under) if under is not None else None)
        except Exception:
            return (line if isinstance(line, (int, float)) else None,
                    over if isinstance(over, int) else None,
                    under if isinstance(under, int) else None)

    # Markets fallback: find a totals market and capture a line with both over/under odds
    for m in game_obj.get('markets', []) if isinstance(game_obj.get('markets'), list) else []:
        if m.get('key') == 'totals':
            over_out = None
            under_out = None
            for out in m.get('outcomes', []) or []:
                nm = str(out.get('name', '')).lower()
                if 'over' in nm:
                    over_out = out
                elif 'under' in nm:
                    under_out = out
            if over_out and under_out:
                try:
                    line = float(over_out.get('point')) if over_out.get('point') is not None else None
                except Exception:
                    line = None
                try:
                    over = int(over_out.get('price')) if over_out.get('price') is not None else None
                except Exception:
                    over = None
                try:
                    under = int(under_out.get('price')) if under_out.get('price') is not None else None
                except Exception:
                    under = None
                return line, over, under

    return None, None, None


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

    candidates: List[Dict[str, Any]] = []

    for game_key, game_data in games.items():
        # Determine a normalized key to find final scores
        away = game_data.get('away_team') or game_key.split(' @ ')[0] if ' @ ' in game_key else ''
        home = game_data.get('home_team') or game_key.split(' @ ')[1] if ' @ ' in game_key else ''
        norm_key_vs = f"{away} vs {home}" if away and home else _normalize_game_key(game_key)
        fs = final_scores.get(norm_key_vs) or final_scores.get(f"{home} vs {away}")
        away_score = (fs or {}).get('away_score')
        home_score = (fs or {}).get('home_score')

        # Unified handling: prefer detailed mapping under 'betting_recommendations', otherwise accept arrays
        if isinstance(game_data.get('betting_recommendations'), dict):
            rec_iter = []
            for rtype, rec in game_data['betting_recommendations'].items():
                if isinstance(rec, dict):
                    rec_copy = dict(rec)
                    rec_copy['type'] = rtype
                    rec_iter.append(rec_copy)
        else:
            rec_iter = []
            vb = game_data.get('value_bets') or []
            if isinstance(vb, list):
                rec_iter.extend(vb)
            recs = game_data.get('recommendations') or []
            if isinstance(recs, list):
                rec_iter.extend(recs)

        # Inspect supported bet types
        for rec in rec_iter:
            try:
                if not isinstance(rec, dict):
                    continue
                rtype = str(rec.get('type', '')).lower()
                # Best of Best: focus on totals only for now (support common aliases)
                if rtype not in ('total', 'totals', 'over_under', 'over/under'):
                    continue

                bet_type = 'Over/Under'
                side, line = _parse_total_recommendation(rec)
                if not side or line is None:
                    continue
                # Cross-check with REAL market totals and odds; override rec line if real exists
                real_line = None
                real_over = None
                real_under = None
                try:
                    # Use teams from current game_data for best matching
                    away_name = game_data.get('away_team') or ''
                    home_name = game_data.get('home_team') or ''
                    real_line, real_over, real_under = _find_real_totals_for_game(lines, away_name, home_name)
                except Exception:
                    pass

                use_line = real_line if real_line is not None else line
                bet_details = f"{side} {use_line}"

                # Pull probability
                win_prob = rec.get('win_probability')
                if win_prob is None:
                    # Side-specific fields if present
                    if str(side).lower() == 'over':
                        win_prob = rec.get('over_probability')
                    else:
                        win_prob = rec.get('under_probability')

                # Only include if Kelly fraction is present or computable
                # Prefer explicit kelly_fraction (0..1) or kelly_bet_size (percent 0..100)
                kf = rec.get('kelly_fraction')
                odds = rec.get('odds') or rec.get('american_odds')
                # Prefer real market odds for the chosen side if available
                if str(side).lower() == 'under' and real_under is not None:
                    odds = real_under
                elif str(side).lower() == 'over' and real_over is not None:
                    odds = real_over
                odds_int = _parse_american_odds(odds)
                if kf is None:
                    # Check for kelly_bet_size in percent
                    kbs = rec.get('kelly_bet_size')
                    if isinstance(kbs, (int, float)):
                        kf = float(kbs) / 100.0
                    else:
                        if isinstance(win_prob, (int, float)):
                            p = float(win_prob)
                            if p > 1:
                                p = p / 100.0
                            kf = _calc_kelly_fraction(p, odds_int if odds_int is not None else -110)
                        else:
                            continue
                else:
                    # Might be provided in 0..1 or 0..100
                    if kf > 1.0:
                        kf = kf / 100.0

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

                # Suggested bet sizing aligned with UI rules:
                # base_unit = $100, cap at 25% Kelly -> max $100, round to $10, floor $10 if >0
                base_unit = 100
                kelly_cap = 0.25
                sized = base_unit * max(0.0, min(kf / kelly_cap, 1.0))
                suggested = int(round(sized / 10.0) * 10)
                if suggested == 0 and sized > 0:
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

                candidates.append({
                    'date': date_str,
                    'game': _normalize_game_key(game_key),
                    'bet_type': bet_type,
                    'bet_details': bet_details,
                    'confidence': round(kf, 3),  # decimal 0..1
                    'kelly_percentage': round(kf * 100, 1),
                    'recommended_bet': suggested,
                    'odds': odds_int if odds_int is not None else -110,
                    'outcome': outcome,
                    'profit_loss': round(profit_loss, 2),
                    'roi': round(roi, 2)
                })
            except Exception:
                # Skip malformed entries
                continue
    # Best of Best cap: keep top 4 entries by Kelly percentage
    candidates.sort(key=lambda e: e.get('kelly_percentage', 0), reverse=True)
    results = candidates[:4]
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

    # Also persist a daily file for historical analysis convenience
    try:
        # Organize by year for cleanliness: data/kelly_daily/YYYY/kelly_bets_YYYY_MM_DD.json
        dt = datetime.strptime(date_str, '%Y-%m-%d')
        year_dir = DAILY_KELLY_DIR / f"{dt.year}"
        year_dir.mkdir(parents=True, exist_ok=True)
        daily_path = year_dir / f"kelly_bets_{dt.strftime('%Y_%m_%d')}.json"
        _save_json(daily_path, new_entries)
        daily_written = len(new_entries)
    except Exception as e:
        daily_written = 0
    return {'success': True, 'written': appended, 'total': len(existing), 'daily_written': daily_written}


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
