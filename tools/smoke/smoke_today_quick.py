import sys, os
from pathlib import Path

# Ensure project root is on sys.path
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app import app

if __name__ == "__main__":
    c = app.test_client()
    r = c.get('/api/today-games/quick?no_network=1')
    print('today_quick status:', r.status_code)
    js = r.get_json(silent=True) or {}
    print('count:', js.get('count'))
    g = (js.get('games') or [])[:3]
    for x in g:
        print(x.get('away_team'), '@', x.get('home_team'), '| pitchers:', x.get('away_pitcher'), 'vs', x.get('home_pitcher'))
