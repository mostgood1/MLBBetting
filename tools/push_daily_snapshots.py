#!/usr/bin/env python3
"""Push today's (or a given date) props and recommendations snapshots to the web app via the existing ingest bridge.

Usage:
  # env must be set
  #   WEB_BASE_URL=https://<your-app>
  #   PITCHER_SSE_INGEST_TOKEN=<token>
  python tools/push_daily_snapshots.py --date 2025-09-12 --verbose

If --date is omitted, uses today in UTC.

This uses tools.pitcher_sse_worker_bridge.send_events to post a batch with:
  - { type: 'props_snapshot', date, doc }
  - { type: 'recommendations_snapshot', date, doc }

It skips any missing files.
"""
import os
import json
import argparse
from datetime import datetime
import sys
from pathlib import Path
import importlib

# Ensure repository root is on sys.path so we can import tools.pitcher_sse_worker_bridge
try:
    REPO_ROOT = Path(__file__).resolve().parents[1]
    if str(REPO_ROOT) not in sys.path:
        sys.path.insert(0, str(REPO_ROOT))
except Exception:
    pass

_BRIDGE_AVAILABLE = True
def _lazy_bridge_send():
    try:
        mod = importlib.import_module('tools.pitcher_sse_worker_bridge')
        return getattr(mod, 'send_events')
    except Exception:
        print("[push_daily_snapshots] Bridge unavailable. Set WEB_BASE_URL and PITCHER_SSE_INGEST_TOKEN.")
        return None

DATA_DIR = os.path.join('data', 'daily_bovada')


def load_json(path: str):
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--date', help='Date (YYYY-MM-DD). Defaults to today (UTC).')
    ap.add_argument('--verbose', action='store_true')
    ap.add_argument('--base', help='Override WEB_BASE_URL (e.g., https://your-app)')
    ap.add_argument('--token', help='Override PITCHER_SSE_INGEST_TOKEN')
    ap.add_argument('--token-file', help='Path to file containing ingest token (alternative to --token)')
    ap.add_argument('--props-only', action='store_true', help='Only send props snapshot')
    ap.add_argument('--recs-only', action='store_true', help='Only send recommendations snapshot')
    ap.add_argument('--split', action='store_true', help='Send snapshots in separate POSTs')
    args = ap.parse_args()
    # Optional overrides for env so the bridge picks them up
    if args.base:
        os.environ['WEB_BASE_URL'] = args.base
    if args.token:
        os.environ['PITCHER_SSE_INGEST_TOKEN'] = args.token
    if args.token_file:
        os.environ['PITCHER_SSE_INGEST_TOKEN_FILE'] = args.token_file

    # Import bridge after setting env
    bridge_send = _lazy_bridge_send()
    if bridge_send is None:
        return 1

    date_str = args.date or datetime.utcnow().strftime('%Y-%m-%d')
    tag = date_str.replace('-', '_')

    props_path = os.path.join(DATA_DIR, f'bovada_pitcher_props_{tag}.json')
    recs_path = os.path.join(DATA_DIR, f'pitcher_prop_recommendations_{tag}.json')

    props_doc = load_json(props_path)
    recs_doc = load_json(recs_path)

    if args.verbose:
        print(f"[push_daily_snapshots] date={date_str}")
        print(f"  props: {props_path} exists={bool(props_doc)} size={os.path.getsize(props_path) if os.path.exists(props_path) else 0}")
        print(f"  recs:  {recs_path} exists={bool(recs_doc)} size={os.path.getsize(recs_path) if os.path.exists(recs_path) else 0}")

    events = []
    if not args.recs_only and props_doc and isinstance(props_doc, dict):
        events.append({'type': 'props_snapshot', 'date': date_str, 'doc': props_doc})
    if not args.props_only and recs_doc and isinstance(recs_doc, dict):
        events.append({'type': 'recommendations_snapshot', 'date': date_str, 'doc': recs_doc})

    if not events:
        print('[push_daily_snapshots] Nothing to send (missing docs).')
        return 2

    # Optional warmup to reduce cold-start latency
    web_base = os.environ.get('WEB_BASE_URL', '').rstrip('/')
    if web_base:
        import urllib.request
        try:
            urllib.request.urlopen(web_base + '/api/health/props-stream-stats', timeout=8).read(1)
        except Exception:
            pass

    ok = False
    if args.split and len(events) > 1:
        parts = []
        for ev in events:
            if bridge_send([ev]):
                parts.append(True)
            else:
                parts.append(False)
        ok = all(parts)
    else:
        ok = bridge_send(events)

    if ok:
        print('[push_daily_snapshots] Sent snapshots successfully.')
        return 0
    else:
        print('[push_daily_snapshots] Failed to send snapshots. Ensure WEB_BASE_URL and ingest token (env or file) are set and valid.')
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
