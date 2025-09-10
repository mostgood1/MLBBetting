#!/usr/bin/env python3
"""
Force a refetch of today's (or a provided date's) Bovada pitcher prop lines
and write them to data/daily_bovada/bovada_pitcher_props_YYYY_MM_DD.json.

Also optionally commit the updated files to git.

Usage:
  python tools/refetch_bovada_props.py [--date YYYY-MM-DD] [--git-commit]
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
    """Infer business date from latest games_*.json, else today."""
    candidates = [f for f in os.listdir(DATA_DIR) if f.startswith('games_') and f.endswith('.json')]
    if candidates:
        candidates.sort(key=lambda f: os.path.getmtime(os.path.join(DATA_DIR, f)), reverse=True)
        m = re.search(r"games_(\d{4}-\d{2}-\d{2})\.json", candidates[0])
        if m:
            return m.group(1)
    return datetime.now().strftime('%Y-%m-%d')


def load_games(date_iso: str):
    path = os.path.join(DATA_DIR, f'games_{date_iso}.json')
    if not os.path.exists(path):
        return []
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def normalize_name(name: str) -> str:
    import unicodedata
    base = ''.join(c for c in unicodedata.normalize('NFD', (name or '').strip()) if unicodedata.category(c) != 'Mn')
    return re.sub(r"\s+", " ", base).lower()


def extract_pitcher_names(games):
    names = []
    for g in games:
        for k in ['away_pitcher', 'home_pitcher', 'away_probable_pitcher', 'home_probable_pitcher']:
            v = (g or {}).get(k)
            if v and v.strip() and v.lower() not in { 'tbd', 'probable', 'unknown' }:
                if v not in names:
                    names.append(v)
    return names


def refetch(date_iso: str, pitcher_names):
    # Import locally
    sys.path.append(ROOT)
    from pitcher_projections import fetch_bovada_pitcher_props
    # Clear cache by reloading module globals
    import pitcher_projections as pp
    pp._BOVADA_CACHE = {}
    pp._BOVADA_CACHE_EXPIRY = 0.0
    props = fetch_bovada_pitcher_props(pitcher_names=pitcher_names)
    date_us = date_iso.replace('-', '_')
    out_path = os.path.join(DAILY_BOVADA_DIR, f'bovada_pitcher_props_{date_us}.json')
    # Sanity
    count = len(props or {})
    print(f"Refetched Bovada props for {date_iso}: pitchers={count} -> {out_path}")
    return out_path, count


def git_commit(paths, date_iso: str):
    try:
        files = [p for p in paths if os.path.exists(p)]
        if not files:
            print("Nothing to commit.")
            return
        subprocess.run(["git", "add", *files], cwd=ROOT, check=True)
        msg = f"chore(data): update Bovada pitcher props for {date_iso}"
        subprocess.run(["git", "commit", "-m", msg], cwd=ROOT, check=True)
        # Push is optional; if it fails, don't crash the script
        try:
            subprocess.run(["git", "push"], cwd=ROOT, check=True)
            print("Pushed changes to remote.")
        except Exception as e:
            print(f"Note: git push skipped/failed: {e}")
    except subprocess.CalledProcessError as e:
        print(f"git commit failed: {e}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--date', dest='date', help='YYYY-MM-DD date; defaults to inferred business date')
    ap.add_argument('--git-commit', action='store_true', help='Add/commit/push updated files')
    args = ap.parse_args()

    date_iso = args.date or infer_date()
    os.makedirs(DAILY_BOVADA_DIR, exist_ok=True)
    games = load_games(date_iso)
    pitchers = extract_pitcher_names(games)
    out_path, count = refetch(date_iso, pitchers)

    # Include matching report if exists
    date_us = date_iso.replace('-', '_')
    match_report = os.path.join(DAILY_BOVADA_DIR, f'matching_report_{date_us}.json')
    to_commit = [out_path]
    if os.path.exists(match_report):
        to_commit.append(match_report)

    if args.git_commit:
        git_commit(to_commit, date_iso)

    # Brief exit code semantics
    if count == 0:
        sys.exit(3)


if __name__ == '__main__':
    main()
