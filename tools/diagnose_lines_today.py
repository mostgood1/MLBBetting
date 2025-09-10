#!/usr/bin/env python3
"""
Quick diagnostics for today's betting lines and pitcher prop matching.

Reports:
- Games missing real betting lines (moneyline/total/run line) keys.
- Starters missing Bovada pitcher props.

Usage: python tools/diagnose_lines_today.py [YYYY-MM-DD]
If date not provided, will try to infer from latest games_*.json in data/.
"""
import json
import os
import re
import sys
from datetime import datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(ROOT, 'data')
DAILY_BOVADA_DIR = os.path.join(DATA_DIR, 'daily_bovada')


def _strip_accents(s: str) -> str:
    import unicodedata
    return ''.join(c for c in unicodedata.normalize('NFD', s or '') if unicodedata.category(c) != 'Mn')


def normalize_name(name: str) -> str:
    base = _strip_accents((name or '').strip()).lower()
    # collapse whitespace
    return re.sub(r"\s+", " ", base)


def normalize_team_name(team_name: str) -> str:
    # Use the canonical normalizer if available, with a safe fallback
    try:
        sys.path.append(ROOT)
        from team_name_normalizer import normalize_team_name as _canon
        return _canon((team_name or '').replace('_', ' ').strip())
    except Exception:
        return (team_name or '').replace('_', ' ').strip()


def infer_date() -> str:
    # Prefer business date from existing games file if present
    candidates = [f for f in os.listdir(DATA_DIR) if f.startswith('games_') and f.endswith('.json')]
    if not candidates:
        # Fallback to today
        return datetime.now().strftime('%Y-%m-%d')
    # Sort by mtime desc
    candidates.sort(key=lambda f: os.path.getmtime(os.path.join(DATA_DIR, f)), reverse=True)
    # Extract date from filename
    m = re.search(r"games_(\d{4}-\d{2}-\d{2})\.json", candidates[0])
    if m:
        return m.group(1)
    # Alternate underscore date
    m = re.search(r"games_(\d{4}_\d{2}_\d{2})\.json", candidates[0])
    if m:
        d = m.group(1).replace('_', '-')
        return d
    return datetime.now().strftime('%Y-%m-%d')


def load_json(path: str):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def main():
    date_str = sys.argv[1] if len(sys.argv) > 1 else infer_date()
    date_us = date_str.replace('-', '_')

    games_path = os.path.join(DATA_DIR, f'games_{date_str}.json')
    if not os.path.exists(games_path):
        print(f"ERROR: Missing {games_path}")
        sys.exit(2)
    games = load_json(games_path)

    lines_path = os.path.join(DATA_DIR, f'real_betting_lines_{date_us}.json')
    lines = None
    if os.path.exists(lines_path):
        lines = load_json(lines_path)
    else:
        print(f"WARN: Missing {lines_path}; will treat as no lines loaded")
        lines = {"lines": {}}

    bovada_path = os.path.join(DAILY_BOVADA_DIR, f'bovada_pitcher_props_{date_us}.json')
    props = None
    if os.path.exists(bovada_path):
        props = load_json(bovada_path)
    else:
        print(f"WARN: Missing {bovada_path}")
        props = {"pitcher_props": {}}

    line_keys = set((lines or {}).get('lines', {}).keys())
    props_pitchers = set((props or {}).get('pitcher_props', {}).keys())

    missing_game_lines = []
    missing_pitcher_props = []

    for g in games:
        away = normalize_team_name(g.get('away_team', ''))
        home = normalize_team_name(g.get('home_team', ''))
        key = f"{away} @ {home}"
        if key not in line_keys:
            missing_game_lines.append({
                'game': key,
                'game_time': g.get('game_time'),
            })
        # pitchers
        ap = normalize_name(g.get('away_pitcher', '') or g.get('away_probable_pitcher', ''))
        hp = normalize_name(g.get('home_pitcher', '') or g.get('home_probable_pitcher', ''))
        if ap and ap != 'tbd' and ap not in props_pitchers:
            missing_pitcher_props.append({'pitcher': g.get('away_pitcher', ''), 'team': away, 'game': key})
        if hp and hp != 'tbd' and hp not in props_pitchers:
            missing_pitcher_props.append({'pitcher': g.get('home_pitcher', ''), 'team': home, 'game': key})

    print(f"\nDiagnostics for {date_str}")
    print(f"Games: {len(games)} | Lines loaded: {len(line_keys)} | Pitcher props: {len(props_pitchers)}")

    if missing_game_lines:
        print(f"\nGames missing real betting lines ({len(missing_game_lines)}):")
        for m in missing_game_lines:
            print(f" - {m['game']} at {m['game_time']}")
    else:
        print("\nAll games have real betting lines keys present.")

    if missing_pitcher_props:
        print(f"\nStarters missing Bovada pitcher props ({len(missing_pitcher_props)}):")
        for m in missing_pitcher_props:
            print(f" - {m['pitcher']} ({m['team']}) in {m['game']}")
    else:
        print("\nAll listed starters have Bovada pitcher props.")


if __name__ == '__main__':
    main()
