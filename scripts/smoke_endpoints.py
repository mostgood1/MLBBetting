import json
import os
import sys
from pathlib import Path
from datetime import datetime
from collections import Counter

import requests

BASE = os.environ.get("BASE_URL", "http://127.0.0.1:5000")


def _network_mode_available() -> bool:
    try:
        r = requests.get(f"{BASE}/api-test", timeout=3)
        return r.status_code in (200, 404)
    except Exception:
        return False


def _fetch_json_network(path: str, timeout: int = 10):
    url = f"{BASE}{path}" if not path.startswith("http") else path
    r = requests.get(url, timeout=timeout)
    r.raise_for_status()
    return r.json()


def _fetch_json_test_client(client, path: str):
    resp = client.get(path)
    if resp.status_code != 200:
        raise RuntimeError(f"Test client GET {path} -> {resp.status_code}")
    return resp.get_json()


def main():
    try_network = _network_mode_available()
    if try_network:
        try:
            today_payload = _fetch_json_network("/api/betting-recommendations/today")
            recs = today_payload.get("recommendations", [])
            print(f"Recommendations (today): {len(recs)} items")
            print("By type:", dict(Counter([str(x.get("type")).lower() for x in recs])))
            print("By conf:", dict(Counter([str(x.get("confidence")).upper() for x in recs])))
            today = today_payload.get("date")
            js = _fetch_json_network(f"/api/pitcher-prop-plays?date={today}")
        except Exception as e:
            print(f"Network mode failed ({e}); falling back to Flask test_client...")
            try_network = False
    if not try_network:
        # Fallback to Flask test_client without a running server
        # Ensure repository root is on sys.path for 'import app'
        repo_root = str(Path(__file__).resolve().parents[1])
        if repo_root not in sys.path:
            sys.path.insert(0, repo_root)
        from app import app as flask_app

        with flask_app.test_client() as client:
            today_payload = _fetch_json_test_client(client, "/api/betting-recommendations/today")
            recs = today_payload.get("recommendations", [])
            print(f"Recommendations (today): {len(recs)} items")
            print("By type:", dict(Counter([str(x.get("type")).lower() for x in recs])))
            print("By conf:", dict(Counter([str(x.get("confidence")).upper() for x in recs])))

            today = today_payload.get("date")
            js = _fetch_json_test_client(client, f"/api/pitcher-prop-plays?date={today}")

    if js.get("mode") == "aggregate":
        plays = js.get("plays", [])
    else:
        plays = []
        plays_by_stat = js.get("plays", {})
        for stat, grp in (plays_by_stat or {}).items():
            for conf in ("HIGH", "MEDIUM", "LOW"):
                plays.extend(grp.get(conf, []))
    print(f"Pitcher props (today): {len(plays)} plays")
    by_stat = {}
    for p in plays:
        stat = p.get("stat")
        if stat:
            by_stat[stat] = by_stat.get(stat, 0) + 1
    print("Props by stat:", by_stat)


if __name__ == "__main__":
    main()
