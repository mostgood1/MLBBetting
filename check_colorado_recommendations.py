import json

print("=== CHECKING COLORADO GAME_RECOMMENDATIONS ===")

# Load betting recommendations file
with open('data/betting_recommendations_2025_08_26.json', 'r') as f:
    betting_data = json.load(f)

# Check Colorado game
betting_game_key = "Colorado Rockies_vs_Houston Astros"
if betting_game_key in betting_data['games']:
    game_recommendations = betting_data['games'][betting_game_key]
    
    print(f"✅ Found game_recommendations for {betting_game_key}")
    print(f"Type: {type(game_recommendations)}")
    print(f"Keys: {list(game_recommendations.keys())}")
    
    # Check recommendations array
    if 'recommendations' in game_recommendations:
        recs = game_recommendations['recommendations']
        print(f"\nRecommendations array:")
        print(f"  Length: {len(recs)}")
        for i, rec in enumerate(recs):
            print(f"  {i+1}. {rec}")
    
    # Check if it has any meaningful recommendations
    meaningful_recs = []
    if 'recommendations' in game_recommendations:
        for rec in game_recommendations['recommendations']:
            if isinstance(rec, dict) and rec.get('recommendation') != 'No recommendations':
                meaningful_recs.append(rec)
    
    print(f"\nMeaningful recommendations: {len(meaningful_recs)}")
    if meaningful_recs:
        for rec in meaningful_recs:
            print(f"  - {rec}")
    else:
        print("  No meaningful recommendations found")
        
    # This explains why convert_betting_recommendations_to_frontend_format returns None
    print(f"\nThis is why convert_betting_recommendations_to_frontend_format returns None for Colorado")
    print(f"The old format handler only converts actual betting recommendations, not 'No recommendations'")
else:
    print(f"❌ {betting_game_key} not found in betting recommendations file")
