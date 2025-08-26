import requests
import json

print("=== TRACING COLORADO GAME DATA SOURCES ===")

# Let me check what's in the unified cache for Colorado
with open('data/unified_predictions_cache.json', 'r') as f:
    cache = json.load(f)

if '2025-08-26' in cache['predictions_by_date']:
    games = cache['predictions_by_date']['2025-08-26']['games']
    
    print(f"\n1. UNIFIED CACHE - Total games: {len(games)}")
    
    colorado_cache_game = None
    for game_key, game_data in games.items():
        if game_data.get('away_team') == 'Colorado Rockies' and game_data.get('home_team') == 'Houston Astros':
            colorado_cache_game = game_data
            print(f"✅ Found Colorado in cache with key: {game_key}")
            
            # Check if it has betting recommendations in cache
            if 'betting_recommendations' in game_data:
                betting_recs = game_data['betting_recommendations']
                print(f"✅ Has betting_recommendations in cache: {type(betting_recs)}")
                if isinstance(betting_recs, dict):
                    print(f"Cache betting_recs keys: {list(betting_recs.keys())}")
                    if 'value_bets' in betting_recs:
                        print(f"Cache value_bets count: {len(betting_recs['value_bets'])}")
            else:
                print("❌ No betting_recommendations in cache")
            break
    
    if not colorado_cache_game:
        print("❌ Colorado game not found in cache")
        print("Available games in cache:")
        for game_key, game_data in list(games.items())[:5]:
            print(f"  - {game_data.get('away_team')} @ {game_data.get('home_team')}")

# Check if there's a unified betting recommendations file
print("\n2. CHECKING FOR UNIFIED BETTING RECOMMENDATIONS")
try:
    with open('data/unified_betting_recommendations.json', 'r') as f:
        unified_data = json.load(f)
    print(f"✅ Found unified betting recommendations file")
    if 'games' in unified_data:
        print(f"Unified file has {len(unified_data['games'])} games")
        for key in unified_data['games'].keys():
            if 'Colorado' in key:
                print(f"Found Colorado key in unified: {key}")
except FileNotFoundError:
    print("❌ No unified betting recommendations file found")
