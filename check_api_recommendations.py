import requests
import json

response = requests.get('http://127.0.0.1:5000/api/today-games')
data = response.json()

print('=== API RESPONSE ANALYSIS ===')
total_games = len(data.get('games', []))
print(f'Total games in API: {total_games}')

games_with_betting = []
for i, game in enumerate(data.get('games', [])):
    if game.get('betting_recommendations') and game.get('betting_recommendations', {}).get('value_bets'):
        games_with_betting.append((i, game))

print(f'Games with betting recommendations in API: {len(games_with_betting)}')

for i, (game_index, game) in enumerate(games_with_betting):
    print(f'\nAPI Game {i+1} (index {game_index}): {game["away_team"]} @ {game["home_team"]}')
    recs = game['betting_recommendations']
    print(f'  Value bets: {len(recs.get("value_bets", []))}')
    for j, bet in enumerate(recs.get('value_bets', [])):
        print(f'    {j+1}. {bet.get("recommendation", "N/A")}')

# Also check games without betting recommendations
games_without_betting = []
for i, game in enumerate(data.get('games', [])):
    betting_recs = game.get('betting_recommendations')
    if not betting_recs or not betting_recs.get('value_bets'):
        games_without_betting.append((i, game))

print(f'\nGames WITHOUT betting recommendations: {len(games_without_betting)}')
if len(games_without_betting) > 0:
    print('Sample games without betting:')
    for i, (game_index, game) in enumerate(games_without_betting[:3]):
        print(f'  {game["away_team"]} @ {game["home_team"]} (betting_recommendations: {game.get("betting_recommendations")})')
