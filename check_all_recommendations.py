import json

with open('data/betting_recommendations_2025_08_26.json', 'r') as f:
    data = json.load(f)

print('=== BETTING RECOMMENDATIONS FILE ===')
games_with_recs = []
for game_key, game_data in data.get('games', {}).items():
    if game_data.get('betting_recommendations'):
        games_with_recs.append(game_data)

print(f'Total games with recommendations in file: {len(games_with_recs)}')

for i, game in enumerate(games_with_recs):
    print(f'\nGame {i+1}: {game["away_team"]} @ {game["home_team"]}')
    recs = game['betting_recommendations']
    if 'value_bets' in recs:
        print(f'  Value bets: {len(recs["value_bets"])}')
        for j, bet in enumerate(recs['value_bets']):
            print(f'    {j+1}. {bet.get("recommendation", "N/A")} ({bet.get("confidence", "N/A")})')
    if 'best_bet' in recs:
        print(f'  Best bet: {recs["best_bet"].get("recommendation", "N/A")}')
        
if len(games_with_recs) == 0:
    print('\nNo games with recommendations found in the file!')
    print('File structure:')
    print(f'Top level keys: {list(data.keys())}')
    if 'games' in data:
        print(f'Number of games: {len(data["games"])}')
        sample_game = list(data['games'].values())[0]
        print(f'Sample game keys: {list(sample_game.keys())}')
