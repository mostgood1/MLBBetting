import sys, os
from pathlib import Path

# Ensure project root is on sys.path
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app import app

if __name__ == "__main__":
    c = app.test_client()
    r = c.get('/api/pitcher-props/unified?light=1&timings=1&date=2025-09-16')
    print('unified status:', r.status_code)
    js = r.get_json(silent=True) or {}
    print('pitchers:', (js.get('meta') or {}).get('pitchers'))
    print('light_mode:', (js.get('meta') or {}).get('light_mode'))
    d = js.get('data') or {}
    non_null = sum(1 for v in d.values() if v.get('live_pitches') is not None)
    print('live_pitches_non_null:', non_null)
