import json

print('=== UNIFIED CACHE ===')
with open('data/unified_predictions_cache.json', 'r') as f:
    cache = json.load(f)
    
if '2025-08-26' in cache.get('predictions_by_date', {}):
    games = cache['predictions_by_date']['2025-08-26']
    print(f'Cache has {len(games)} games for 2025-08-26')
    
    games_with_betting = 0
    for game in games:
        if game.get('betting_recommendations'):
            games_with_betting += 1
            print(f'Game: {game["away_team"]} @ {game["home_team"]} has betting recommendations')
            # Show structure
            betting_recs = game['betting_recommendations']
            print(f'  Value bets: {len(betting_recs.get("value_bets", []))}')
            print(f'  Best bet: {betting_recs.get("best_bet", {}).get("recommendation", "None")}')
    
    print(f'Games with betting in cache: {games_with_betting}')
else:
    print('No games for 2025-08-26 in cache')
