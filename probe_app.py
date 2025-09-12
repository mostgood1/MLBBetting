import os, sys, traceback
os.environ['FLASK_ENV'] = 'production'
try:
    import app
    c = app.app.test_client()
    r = c.get('/')
    print('GET / ->', r.status_code, 'bytes:', len(r.data))
    for ep in ['/api/test-route', '/api/debug-routes', '/api/pitcher-props/unified']:
        rr = c.get(ep)
        print(ep, '->', rr.status_code, 'bytes:', len(rr.data))
except Exception as e:
    print('Probe error:', e)
    traceback.print_exc()
    sys.exit(1)
