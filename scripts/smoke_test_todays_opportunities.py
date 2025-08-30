import sys, threading, time, os
import requests

# Ensure repo root on path
repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, repo_root)

import app as mlb


def run_app():
    mlb.app.run(debug=False, host='127.0.0.1', port=5055)


if __name__ == '__main__':
    th = threading.Thread(target=run_app, daemon=True)
    th.start()

    # Wait for server to be up
    for _ in range(40):
        try:
            r = requests.get('http://127.0.0.1:5055/api/test-route', timeout=1)
            if r.status_code == 200:
                break
        except Exception:
            time.sleep(0.25)

    # Default thresholds
    r = requests.get('http://127.0.0.1:5055/api/todays-opportunities', timeout=20)
    print('default_status', r.status_code)
    print('default_total', r.json().get('data', {}).get('total_opportunities'))

    # Relaxed thresholds
    r2 = requests.get('http://127.0.0.1:5055/api/todays-opportunities?minKelly=3&minConf=LOW', timeout=20)
    print('relaxed_status', r2.status_code)
    print('relaxed_total', r2.json().get('data', {}).get('total_opportunities'))

    # Show a few example bets
    ops = (r2.json().get('data', {}).get('opportunities') or [])[:5]
    for o in ops:
        print('sample', o.get('bet_type'), o.get('bet_details'), o.get('kelly_percentage'), o.get('odds'))
