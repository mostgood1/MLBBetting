import json
import os
import sys
from pathlib import Path

# Ensure we import the Flask app by adding project root to sys.path
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from app import app

def main():
    client = app.test_client()

    # Hit unified light (nocache) to force build and meta snapshot write
    r = client.get('/api/pitcher-props/unified?light=1&nocache=1')
    assert r.status_code == 200, f"unified light failed: {r.status_code}"
    data = r.get_json() or {}
    meta = data.get('meta') or {}
    pitchers = meta.get('pitchers') or 0
    markets_total = meta.get('markets_total') or 0
    print(f"Unified light: pitchers={pitchers} markets_total={markets_total} synthesized={meta.get('synthesized')} source_date={meta.get('source_date')}")

    # Verify meta file exists
    date_str = str(data.get('date'))
    sdate = date_str.replace('-', '_')
    meta_dir = Path('data')/ 'daily_bovada'
    light_meta = meta_dir / f'unified_light_meta_{sdate}.json'
    assert light_meta.exists(), f"Expected meta file not found: {light_meta}"
    with open(light_meta, 'r', encoding='utf-8') as f:
        mdoc = json.load(f)
    print(f"Light meta file: pitchers={mdoc.get('pitchers')} covered={mdoc.get('covered_pitchers')} cov%={mdoc.get('coverage_percent')}")

    # Spotlight health should now be available
    h = client.get('/api/props/spotlight-health')
    assert h.status_code == 200, f"spotlight-health failed: {h.status_code}"
    hjson = h.get_json() or {}
    print(f"Spotlight-health: available={hjson.get('available')} pitchers={hjson.get('pitchers')} source_date={hjson.get('source_date')}")
    assert hjson.get('available') is True, 'expected spotlight-health available after unified build'

    # Props progress should read from cache or meta file
    p = client.get('/api/props/progress')
    assert p.status_code == 200, f"props-progress failed: {p.status_code}"
    pjson = p.get_json() or {}
    print(f"Props-progress: source={pjson.get('source')} coverage={((pjson.get('data') or {}).get('coverage_percent'))}%")

if __name__ == '__main__':
    main()
