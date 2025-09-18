import sys
from pathlib import Path

# Ensure project root is on sys.path
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app import app

if __name__ == "__main__":
    c = app.test_client()
    r = c.get('/api/prediction/Chicago Cubs/Pittsburgh Pirates?date=2025-09-17')
    print('status', r.status_code)
    js = r.get_json(silent=True) or {}
    print('has-factors', 'factors' in js)
    print('weather', (js.get('factors') or {}).get('weather_park'))
    print('form', js.get('team_form') is not None)
