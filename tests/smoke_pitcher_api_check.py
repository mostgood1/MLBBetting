import os, json
from app import app

DATE = '2025-09-11'

def main():
    client = app.test_client()

    # 1) /api/pitcher-props/current
    r = client.get(f"/api/pitcher-props/current?date={DATE}")
    assert r.status_code == 200, r.data
    doc = r.get_json()
    assert doc.get('success') is True
    pp = doc.get('pitcher_props') or {}
    assert 'john_doe' in pp, f"expected john_doe in pitcher_props keys: {list(pp.keys())[:5]}"

    # 2) /api/pitcher-props/line-history
    r2 = client.get(f"/api/pitcher-props/line-history?date={DATE}")
    assert r2.status_code == 200
    hist = r2.get_json()
    assert hist.get('success') is True and hist.get('count', 0) >= 1

    # 3) /api/pitcher-props/unified
    r3 = client.get(f"/api/pitcher-props/unified?date={DATE}")
    assert r3.status_code == 200
    uni = r3.get_json()
    assert uni.get('success') is True
    data = uni.get('data') or {}
    assert 'john_doe' in data, f"expected john_doe in unified data keys: {list(data.keys())[:5]}"

    print('OK: pitcher props API smoke checks passed')

if __name__ == '__main__':
    main()
