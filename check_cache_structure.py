import json

with open('data/unified_predictions_cache.json', 'r') as f:
    cache = json.load(f)

print('=== CACHE STRUCTURE ===')
if '2025-08-26' in cache['predictions_by_date']:
    data = cache['predictions_by_date']['2025-08-26']
    print(f'Data type: {type(data)}')
    print(f'Keys: {list(data.keys())}')
    
    games_with_betting = 0
    for game_key, game_data in data.items():
        print(f'\nGame: {game_key}')
        print(f'Game data type: {type(game_data)}')
        if isinstance(game_data, dict):
            if 'betting_recommendations' in game_data:
                games_with_betting += 1
                print(f'  HAS BETTING RECOMMENDATIONS!')
                betting_recs = game_data['betting_recommendations']
                print(f'  Value bets: {len(betting_recs.get("value_bets", []))}')
            else:
                print(f'  No betting recommendations key')
    
    print(f'\nTotal games with betting recommendations: {games_with_betting}')
