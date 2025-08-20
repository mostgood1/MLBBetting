import json
import traceback

# Import the Flask app by file path and use the test client to call a safe endpoint
import importlib.util
from pathlib import Path

app_path = Path(__file__).parent.parent / 'app.py'
if not app_path.exists():
    print('ERROR: app.py not found at', app_path)
    raise SystemExit(1)

try:
    spec = importlib.util.spec_from_file_location('mlb_app', str(app_path))
    mlb_app = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mlb_app)
    app = getattr(mlb_app, 'app')
except Exception as e:
    print('ERROR importing app by path:', e)
    traceback.print_exc()
    raise SystemExit(1)

client = app.test_client()

try:
    resp = client.get('/api/betting-test')
    print('STATUS', resp.status_code)
    try:
        data = resp.get_json()
        print('JSON_KEYS', list(data.keys()) if isinstance(data, dict) else str(type(data)))
        print('SAMPLE_DATA', json.dumps(data.get('sample_data', {}), indent=2))
    except Exception as e:
        print('ERROR parsing JSON response:', e)
        print(resp.get_data(as_text=True))
except Exception as e:
    print('REQUEST ERROR:', e)
    traceback.print_exc()
    raise SystemExit(1)
