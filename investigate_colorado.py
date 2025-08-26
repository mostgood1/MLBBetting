import requests
import json

print("=== COLORADO ROCKIES @ HOUSTON ASTROS INVESTIGATION ===")

# Test main API
print("\n1. MAIN API (/api/today-games)")
response = requests.get('http://127.0.0.1:5000/api/today-games')
data = response.json()

colorado_game = None
for game in data.get('games', []):
    if game.get('away_team') == 'Colorado Rockies' and game.get('home_team') == 'Houston Astros':
        colorado_game = game
        break

if colorado_game:
    print("✅ Found Colorado game in main API")
    betting_recs = colorado_game.get('betting_recommendations')
    if betting_recs:
        print(f"✅ Has betting recommendations: {len(betting_recs.get('value_bets', []))} value bets")
        print(f"Game ID: {colorado_game.get('game_id')}")
        print(f"Betting recs keys: {list(betting_recs.keys())}")
        print(f"Summary: {betting_recs.get('summary')}")
    else:
        print("❌ No betting recommendations")
else:
    print("❌ Colorado game not found in main API")

# Test prediction API
print("\n2. PREDICTION API (/api/prediction/...)")
response = requests.get('http://127.0.0.1:5000/api/prediction/Colorado%20Rockies/Houston%20Astros?date=2025-08-26')
data = response.json()

if data.get('success'):
    betting_recs = data.get('betting_recommendations')
    if betting_recs:
        print("✅ Has betting recommendations in prediction API")
        print(f"Value bets: {len(betting_recs.get('value_bets', []))}")
        print(f"Summary: {betting_recs.get('summary')}")
    else:
        print("❌ No betting recommendations in prediction API")
        print(f"betting_recommendations value: {betting_recs}")
else:
    print(f"❌ Prediction API error: {data.get('error')}")

# Check the betting file directly
print("\n3. BETTING RECOMMENDATIONS FILE")
with open('data/betting_recommendations_2025_08_26.json', 'r') as f:
    file_data = json.load(f)

# Look for Colorado game in file
colorado_keys = []
for key in file_data.get('games', {}).keys():
    if 'Colorado' in key and 'Houston' in key:
        colorado_keys.append(key)

if colorado_keys:
    print(f"✅ Found Colorado keys in file: {colorado_keys}")
    for key in colorado_keys:
        game_data = file_data['games'][key]
        if 'recommendations' in game_data:
            recs = game_data['recommendations']
            print(f"Key: {key}")
            print(f"Recommendations: {len(recs)} items")
            for rec in recs:
                if isinstance(rec, dict) and rec.get('recommendation') != 'No recommendations':
                    print(f"  - {rec}")
else:
    print("❌ No Colorado keys found in file")
