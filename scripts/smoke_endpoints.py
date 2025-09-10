import json
import os
from datetime import datetime

import requests

BASE = os.environ.get("BASE_URL", "http://127.0.0.1:5000")

def main():
    # Resolve Eastern today via backend to ensure parity
    r = requests.get(f"{BASE}/api/betting-recommendations/today", timeout=10)
    r.raise_for_status()
    recs = r.json().get("recommendations", [])
    print(f"Recommendations (today): {len(recs)} items")
    # Print a compact breakdown by type and confidence
    from collections import Counter
    types = Counter([str(x.get("type")).lower() for x in recs])
    confs = Counter([str(x.get("confidence")).upper() for x in recs])
    print("By type:", dict(types))
    print("By conf:", dict(confs))

    # Props snapshot for today
    today = requests.get(f"{BASE}/api/betting-recommendations/today").json().get("date")
    r2 = requests.get(f"{BASE}/api/pitcher-prop-plays?date={today}", timeout=10)
    r2.raise_for_status()
    js = r2.json()
    if js.get("mode") == "aggregate":
        plays = js.get("plays", [])
    else:
        plays = []
        plays_by_stat = js.get("plays", {})
        for stat, grp in (plays_by_stat or {}).items():
            for conf in ("HIGH","MEDIUM","LOW"):
                plays.extend(grp.get(conf, []))
    print(f"Pitcher props (today): {len(plays)} plays")
    by_stat = {}
    for p in plays:
        by_stat[p["stat"]] = by_stat.get(p["stat"], 0) + 1
    print("Props by stat:", by_stat)

if __name__ == "__main__":
    main()
