#!/usr/bin/env python3
"""
Recompute today's pitcher projections (force refresh) so the backend snapshot
includes latest Bovada lines.

Writes to data/daily_bovada/pitcher_projections_update_YYYY_MM_DD.json
and auxiliary validation files.

Usage:
  python tools/rebuild_pitcher_projections.py [--git-commit]
"""
import argparse
import json
import os
import subprocess
from datetime import datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(ROOT, 'data')
DAILY_BOVADA_DIR = os.path.join(DATA_DIR, 'daily_bovada')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--git-commit', action='store_true', help='Commit updated projection snapshot(s)')
    args = ap.parse_args()

    import sys
    sys.path.append(ROOT)
    from pitcher_projections import compute_pitcher_projections
    res = compute_pitcher_projections(include_lines=True, force_refresh=True)
    date_iso = res.get('date') or datetime.utcnow().strftime('%Y-%m-%d')
    date_us = date_iso.replace('-', '_')
    paths = [
        os.path.join(DAILY_BOVADA_DIR, f'pitcher_projections_update_{date_us}.json'),
        os.path.join(DAILY_BOVADA_DIR, f'matching_report_{date_us}.json'),
        os.path.join(DAILY_BOVADA_DIR, f'projection_features_{date_us}.json'),
        os.path.join(DAILY_BOVADA_DIR, f'adjustment_summary_{date_us}.json'),
        os.path.join(DAILY_BOVADA_DIR, f'pitcher_validation_{date_us}.json'),
    ]
    print(f"Rebuilt pitcher projections for {date_iso}. Snapshot(s) saved.")
    if args.git_commit:
        try:
            files = [p for p in paths if os.path.exists(p)]
            if files:
                subprocess.run(["git", "add", *files], cwd=ROOT, check=True)
                msg = f"chore(data): rebuild pitcher projections (force) for {date_iso}"
                subprocess.run(["git", "commit", "-m", msg], cwd=ROOT, check=True)
                try:
                    subprocess.run(["git", "push"], cwd=ROOT, check=True)
                except Exception as e:
                    print(f"Note: git push skipped/failed: {e}")
        except subprocess.CalledProcessError as e:
            print(f"git commit failed: {e}")


if __name__ == '__main__':
    main()
