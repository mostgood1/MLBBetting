import os, sys
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from app import app
from utils.name_normalization import normalize_name

TARGET = 'colin rea'
TARGET_ID = '607067'

if __name__ == '__main__':
    with app.test_client() as c:
        resp = c.get('/api/pitcher-props/live-stats')
        print('status', resp.status_code)
        data = resp.get_json()
        ls = data.get('live_stats', {}) if data else {}
        by_id = data.get('live_stats_by_id', {}) if data else {}
        tkey = normalize_name(TARGET)
        print('has name', tkey in ls)
        if tkey in ls:
            print('entry', ls[tkey])
        print('has id', TARGET_ID in by_id)
        if TARGET_ID in by_id:
            print('by_id entry', by_id[TARGET_ID])
        print('counts', len(ls), len(by_id))
