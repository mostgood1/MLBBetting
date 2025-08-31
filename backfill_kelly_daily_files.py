#!/usr/bin/env python3
"""
Backfill per-day Kelly files from consolidated kelly_betting_recommendations.json
- Reads data/kelly_betting_recommendations.json
- Writes data/kelly_daily/YYYY/kelly_bets_YYYY_MM_DD.json per date
Usage: python backfill_kelly_daily_files.py [--since YYYY-MM-DD]
"""
import json
from collections import defaultdict
from pathlib import Path
from datetime import datetime

BASE_PATH = Path(__file__).parent
DATA_DIR = BASE_PATH / 'data'
KELLY_FILE = DATA_DIR / 'kelly_betting_recommendations.json'
DAILY_DIR = DATA_DIR / 'kelly_daily'


def load_json(path: Path):
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding='utf-8'))


def save_json(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding='utf-8')


def backfill(since: str | None = None) -> dict:
    entries = load_json(KELLY_FILE) or []
    by_date: dict[str, list] = defaultdict(list)
    for e in entries:
        d = e.get('date')
        if not d:
            continue
        if since and d < since:
            continue
        by_date[d].append(e)

    written = 0
    for d, items in by_date.items():
        dt = datetime.strptime(d, '%Y-%m-%d')
        out = DAILY_DIR / f"{dt.year}" / f"kelly_bets_{dt.strftime('%Y_%m_%d')}.json"
        save_json(out, items)
        written += 1
    return {"dates": len(by_date), "files_written": written}


if __name__ == '__main__':
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument('--since', help='Backfill only dates >= YYYY-MM-DD')
    args = p.parse_args()
    res = backfill(args.since)
    print(json.dumps(res))
