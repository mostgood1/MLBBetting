import json

# Check betting recommendations file
with open('data/betting_recommendations_2025_08_26.json', 'r') as f:
    data = json.load(f)

print('Total games:', len(data.get('games', {})))

games_with_recs = []
for game_key, game_data in data.get('games', {}).items():
    if game_data.get('betting_recommendations'):
        games_with_recs.append(game_data)

print('Games with recommendations:', len(games_with_recs))

if games_with_recs:
    for i, game in enumerate(games_with_recs):
        print(f'Game {i+1}: {game["away_team"]} @ {game["home_team"]}')
        recs = game['betting_recommendations']
        print(f'  Has value_bets: {bool(recs.get("value_bets"))}')
        print(f'  Value bets count: {len(recs.get("value_bets", []))}')
        print(f'  Has recommendations: {bool(recs.get("recommendations"))}')
        print()
