import requests

print("Testing API call...")
try:
    response = requests.get('http://localhost:5000/api/today-games')
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"Games returned: {len(data.get('games', []))}")
        
        # Count games with betting recommendations
        games_with_recs = 0
        total_recs = 0
        if 'games' in data:
            for game in data['games']:
                betting_recs = game.get('betting_recommendations')
                if betting_recs and isinstance(betting_recs, dict):
                    value_bets = betting_recs.get('value_bets', [])
                    if value_bets:
                        games_with_recs += 1
                        total_recs += len(value_bets)
        
        print(f"Games with betting recommendations: {games_with_recs}")
        print(f"Total betting recommendations: {total_recs}")
    else:
        print(f"Error: {response.status_code}")
except Exception as e:
    print(f"Error: {e}")
