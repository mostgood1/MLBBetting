import sys, os
from pathlib import Path

# Ensure project root is on sys.path
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app import app

if __name__ == "__main__":
    c = app.test_client()
    # Query the target date with light payload and allow_fallback
    r = c.get('/api/pitcher-props/unified?light=1&allow_fallback=1&timings=1&date=2025-09-20')
    print('unified status:', r.status_code)
    js = r.get_json(silent=True) or {}
    meta = js.get('meta') or {}
    print('pitchers:', meta.get('pitchers'))
    print('light_mode:', meta.get('light_mode'))
    print('markets_total:', meta.get('markets_total'))
    d = js.get('data') or {}
    non_null = sum(1 for v in d.values() if (v.get('markets') or {}))
    print('pitchers_with_markets:', non_null)
