#!/usr/bin/env python3
"""
Monitor today's Bovada pitcher props coverage and attempt to fill gaps.

Behavior:
- Check coverage vs. starters found in data/games_YYYY-MM-DD.json
- If coverage < threshold or specific starters missing, force a refetch.
- Optionally git-commit the updated snapshot so local and repo stay in sync.

Usage:
  python tools/monitor_bovada_props.py [--date YYYY-MM-DD] [--min-cover 0.75] [--git-commit]
"""
import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(ROOT, 'data')
DAILY_BOVADA_DIR = os.path.join(DATA_DIR, 'daily_bovada')


def infer_date() -> str:
    candidates = [f for f in os.listdir(DATA_DIR) if f.startswith('games_') and f.endswith('.json')]
    if candidates:
        candidates.sort(key=lambda f: os.path.getmtime(os.path.join(DATA_DIR, f)), reverse=True)
        m = re.search(r"games_(\d{4}-\d{2}-\d{2})\.json", candidates[0])
        if m:
            return m.group(1)
    return datetime.now().strftime('%Y-%m-%d')


def load_json(path: str):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def load_games(date_iso: str):
    path = os.path.join(DATA_DIR, f'games_{date_iso}.json')
    return load_json(path) if os.path.exists(path) else []


def normalize_name(name: str) -> str:
    import unicodedata
    base = ''.join(c for c in unicodedata.normalize('NFD', (name or '').strip()) if unicodedata.category(c) != 'Mn')
    return re.sub(r"\s+", " ", base).lower()


def starters_from_games(games):
    s = []
    for g in games:
        for k in ['away_pitcher', 'home_pitcher', 'away_probable_pitcher', 'home_probable_pitcher']:
            v = (g or {}).get(k)
            if v and v.strip() and v.lower() not in {'tbd', 'probable', 'unknown'}:
                if v not in s:
                    s.append(v)
    return s


def read_current_props(date_iso: str):
    date_us = date_iso.replace('-', '_')
    path = os.path.join(DAILY_BOVADA_DIR, f'bovada_pitcher_props_{date_us}.json')
    if os.path.exists(path):
        data = load_json(path)
        props = (data or {}).get('pitcher_props', {})
        return path, props
    return path, {}


def refetch(date_iso: str, pitcher_names):
    sys.path.append(ROOT)
    from pitcher_projections import fetch_bovada_pitcher_props
    import pitcher_projections as pp
    pp._BOVADA_CACHE = {}
    pp._BOVADA_CACHE_EXPIRY = 0.0
    props = fetch_bovada_pitcher_props(pitcher_names=pitcher_names)
    date_us = date_iso.replace('-', '_')
    out_path = os.path.join(DAILY_BOVADA_DIR, f'bovada_pitcher_props_{date_us}.json')
    print(f"Refetched Bovada props for {date_iso}: pitchers={len(props)} -> {out_path}")
    return out_path, props


def git_commit(paths, date_iso: str):
    try:
        files = [p for p in paths if os.path.exists(p)]
        if not files:
            return
        subprocess.run(["git", "add", *files], cwd=ROOT, check=True)
        msg = f"chore(data): refresh Bovada props for {date_iso}"
        subprocess.run(["git", "commit", "-m", msg], cwd=ROOT, check=True)
        try:
            subprocess.run(["git", "push"], cwd=ROOT, check=True)
        except Exception as e:
            print(f"Note: git push skipped/failed: {e}")
    except subprocess.CalledProcessError as e:
        print(f"git commit failed: {e}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--date', dest='date', help='YYYY-MM-DD date; defaults to inferred business date')
    ap.add_argument('--min-cover', type=float, default=0.75, help='Minimum coverage ratio before auto-refetch')
    ap.add_argument('--git-commit', action='store_true', help='Commit updated snapshot')
    args = ap.parse_args()

    date_iso = args.date or infer_date()
    os.makedirs(DAILY_BOVADA_DIR, exist_ok=True)
    games = load_games(date_iso)
    starters = starters_from_games(games)
    path, props = read_current_props(date_iso)
    present = set(props.keys())
    norm_starters = [normalize_name(n) for n in starters]
    have = sum(1 for n in norm_starters if n in present)
    total = len(norm_starters) or 1
    cover = have / total
    print(f"Coverage for {date_iso}: {have}/{total} = {cover:.0%}")
    to_commit = []
    if cover < args.min_cover:
        print("Coverage below threshold; refetching...")
        out_path, new_props = refetch(date_iso, starters)
        to_commit.append(out_path)
        props = new_props
        present = set(props.keys())
        have = sum(1 for n in norm_starters if n in present)
        cover = have / total
        print(f"Coverage after refetch: {have}/{total} = {cover:.0%}")
    # Always include matching report if exists
    date_us = date_iso.replace('-', '_')
    rep = os.path.join(DAILY_BOVADA_DIR, f'matching_report_{date_us}.json')
    if os.path.exists(rep):
        to_commit.append(rep)
    if args.git_commit and to_commit:
        git_commit(to_commit, date_iso)


if __name__ == '__main__':
    main()
