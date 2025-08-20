modules = [
    'engines.ultra_fast_engine', 'admin_tuning', 'continuous_auto_tuning', 'team_assets_utils',
    'live_mlb_data', 'comprehensive_betting_performance_tracker', 'monitoring_system',
    'performance_tracking', 'memory_optimizer', 'monitoring_history', 'app_betting_integration',
    'daily_betting_lines_automation', 'fetch_todays_starters', 'fix_betting_recommendations',
    'complete_daily_automation'
]

missing = []
import sys
import os
# Ensure project root is importable when this script lives in tools/
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

for m in modules:
    try:
        __import__(m)
    except Exception as e:
        missing.append((m, str(e)))

print('IMPORT_CHECK_RESULTS')
for m, err in missing:
    print(m + ': ' + err)
print('END_IMPORT_CHECK')
