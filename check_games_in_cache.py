import json

with open('data/unified_predictions_cache.json', 'r') as f:
    cache = json.load(f)

print('=== CACHE GAMES STRUCTURE ===')
if '2025-08-26' in cache['predictions_by_date']:
    day_data = cache['predictions_by_date']['2025-08-26']
    
    if 'games' in day_data:
        games = day_data['games']
        print(f'Number of games: {len(games)}')
        
        games_with_betting = 0
        for game_key, game_data in games.items():
            if 'betting_recommendations' in game_data:
                games_with_betting += 1
                print(f'\nGame: {game_data.get("away_team")} @ {game_data.get("home_team")}')
                print(f'  HAS BETTING RECOMMENDATIONS!')
                betting_recs = game_data['betting_recommendations']
                if 'value_bets' in betting_recs:
                    print(f'  Value bets: {len(betting_recs["value_bets"])}')
                    for i, bet in enumerate(betting_recs['value_bets']):
                        print(f'    {i+1}. {bet.get("recommendation", "N/A")}')
        
        print(f'\nTotal games with betting recommendations: {games_with_betting}')
        
        if games_with_betting == 0:
            # Show structure of first game
            first_game_key = list(games.keys())[0]
            first_game = games[first_game_key]
            print(f'\nSample game structure:')
            print(f'Keys: {list(first_game.keys())}')
    else:
        print('No games key found')
