import json, os, sys
# Ensure project root is on sys.path so 'app' can be imported when running from scripts/
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
from app import app

client = app.test_client()

# Test today's opportunities
resp1 = client.get('/api/todays-opportunities')
try:
    j1 = resp1.get_json() or {}
except Exception:
    j1 = {}
data1 = j1.get('data', {}) if isinstance(j1, dict) else {}
ops = data1.get('opportunities', [])
print('TODAYS_OPP', resp1.status_code, 'total=', data1.get('total_opportunities'), 'unique=', len(ops), 'date=', data1.get('date'))

# Test historical Kelly performance
resp2 = client.get('/api/historical-kelly-performance')
try:
    j2 = resp2.get_json() or {}
except Exception:
    j2 = {}
print('HIST_KELLY', resp2.status_code, 'fallback=', j2.get('fallback'), 'summary_keys=', list((j2.get('data') or {}).get('summary', {}).keys()))

# Optional: ensure yesterday exists
from datetime import datetime, timedelta
yday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
daily = (j2.get('data') or {}).get('daily_performance', {})
print('YDAY_PRESENT', yday in daily)
