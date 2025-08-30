from comprehensive_historical_analysis import ComprehensiveHistoricalAnalyzer
import json, os

an=ComprehensiveHistoricalAnalyzer()
for date in ['2025-08-22','2025-08-23']:
    p=an.load_predictions_for_date(date)
    print(date, 'games', len(p))
    path=os.path.join('c:/Users/mostg/OneDrive/Coding/MLB-Betting/data', f'betting_recommendations_{date.replace("-","_")}.json')
    data=json.load(open(path))
    cnt=0
    for g in (data.get('games') or {}).values():
        cnt+=len(an.extract_game_recommendations(g))
    print(date, 'extracted_recs', cnt)
