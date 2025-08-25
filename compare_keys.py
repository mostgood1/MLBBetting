#!/usr/bin/env python3

from app_betting_integration import get_app_betting_recommendations
import requests

# Get unified engine keys
print("=== UNIFIED ENGINE KEYS ===")
raw, frontend = get_app_betting_recommendations()
unified_keys = list(raw.keys())
for i, key in enumerate(unified_keys):
    print(f"{i+1:2d}. '{key}'")

print(f"\nUnified engine has {len(unified_keys)} games with recommendations")

# Get API response
print("\n=== API GAME KEYS ===")
try:
    response = requests.get('http://localhost:5000/api/today-games')
    if response.status_code == 200:
        data = response.json()
        if 'games' in data:
            api_games = data['games']
            api_keys = []
            for i, game in enumerate(api_games):
                away_team = game.get('away_team', '')
                home_team = game.get('home_team', '')
                api_key = f"{away_team} @ {home_team}"
                api_keys.append(api_key)
                print(f"{i+1:2d}. '{api_key}'")
            
            print(f"\nAPI has {len(api_keys)} games")
            
            # Compare keys
            print("\n=== KEY COMPARISON ===")
            unified_set = set(unified_keys)
            api_set = set(api_keys)
            
            missing_in_api = unified_set - api_set
            missing_in_unified = api_set - unified_set
            matching = unified_set & api_set
            
            print(f"Matching keys: {len(matching)}")
            for key in sorted(matching):
                print(f"  ✅ '{key}'")
            
            if missing_in_api:
                print(f"\nIn unified but not in API: {len(missing_in_api)}")
                for key in sorted(missing_in_api):
                    print(f"  ❌ '{key}'")
            
            if missing_in_unified:
                print(f"\nIn API but not in unified: {len(missing_in_unified)}")
                for key in sorted(missing_in_unified):
                    print(f"  ⚠️  '{key}'")
    
except Exception as e:
    print(f"Error: {e}")
