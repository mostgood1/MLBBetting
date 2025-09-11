import sys
sys.path.append(r"c:\Users\mostg\OneDrive\Coding\MLB-Betting")
import json
import traceback

try:
    import app as m
    c = m.app.test_client()
    r = c.get('/api/pitcher-props/unified')
    print('STATUS', r.status_code)
    j = r.get_json()
    if not isinstance(j, dict):
        print('JSON_PARSE_FAIL', type(j))
    else:
        meta = j.get('meta', {})
        data = j.get('data', {})
        print('SUCCESS', j.get('success'), 'PITCHERS', meta.get('pitchers'), 'MARKETS', meta.get('markets_total'))
        print('SAMPLE_KEYS', list((data or {}).keys())[:10])
except Exception as e:
    print('ERROR', e)
    traceback.print_exc()
