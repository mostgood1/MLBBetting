import json
import sys
from pathlib import Path

# Ensure project root is on sys.path
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app import app

if __name__ == "__main__":
    c = app.test_client()

    # Test rolling ROI metrics
    r = c.get('/api/optimization/roi-metrics/rolling?days=7')
    print('roi status:', r.status_code)
    js = r.get_json(silent=True) or {}
    print('roi success:', js.get('success'))
    print('window dates_used:', (js.get('window') or {}).get('dates_used'))
    print('has_metrics:', js.get('roi_metrics') is not None)

    # Test latest betting recommendations fallback
    r2 = c.get('/api/betting-recommendations/latest')
    print('latest recs status:', r2.status_code)
    j2 = r2.get_json(silent=True) or {}
    print('latest date_used:', j2.get('date_used'))
    print('recs count:', len(j2.get('recommendations') or []))
    if (j2.get('recommendations') or []):
        sample = (j2.get('recommendations') or [])[:3]
        print('sample:', json.dumps(sample, ensure_ascii=False))
