import sys, threading, time, os
import requests

repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, repo_root)

import app as mlb


def run_app():
    mlb.app.run(debug=False, host='127.0.0.1', port=5056)


if __name__ == '__main__':
    th = threading.Thread(target=run_app, daemon=True)
    th.start()

    for _ in range(40):
        try:
            r = requests.get('http://127.0.0.1:5056/api/test-route', timeout=1)
            if r.status_code == 200:
                break
        except Exception:
            time.sleep(0.25)

    r1 = requests.get('http://127.0.0.1:5056/api/roi-summary', timeout=30)
    r2 = requests.get('http://127.0.0.1:5056/api/system-performance-overview', timeout=60)
    print('roi_status', r1.status_code)
    print('sys_status', r2.status_code)

    roi = r1.json().get('data', {})
    sysov = r2.json().get('data', {})

    # Sum from dailyPerformance (dict of date -> row)
    dp = sysov.get('dailyPerformance', {}) or {}
    rows = list(dp.values()) if isinstance(dp, dict) else list(dp)
    invested = sum((row or {}).get('invested', 0) or 0 for row in rows)
    net = sum((row or {}).get('net_profit', 0) or 0 for row in rows)
    roi_pct = (net / invested * 100) if invested else 0

    print('card_invested', roi.get('total_investment'))
    print('card_net', roi.get('net_profit'))
    print('card_roi_pct', roi.get('roi_percentage'))
    print('table_invested', round(invested, 2))
    print('table_net', round(net, 2))
    print('table_roi_pct', round(roi_pct, 2))
