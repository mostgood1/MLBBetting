#!/usr/bin/env python3
import json

# Check which dates need regeneration
dates = ['2025-08-15', '2025-08-16', '2025-08-19', '2025-08-20']

print("Checking earlier dates for recommendations:")
print("=" * 50)

for date in dates:
    file_path = f'data/betting_recommendations_{date.replace("-", "_")}.json'
    try:
        with open(file_path, 'r') as f:
            data = json.load(f)
        
        games = data.get('games', {})
        if games:
            first_game = list(games.values())[0]
            has_value_bets = 'value_bets' in first_game
            total_recs = sum(len(game.get('value_bets', [])) for game in games.values()) if has_value_bets else 0
            
            format_type = "New" if has_value_bets else "Old"
            print(f'{date}: {format_type} format, {total_recs} recommendations')
        else:
            print(f'{date}: No games found')
    except Exception as e:
        print(f'{date}: Error - {e}')

print("\nDates that need regeneration (Old format or 0 recommendations):")
print("These dates should get more recommendations with the fixed EV calculation!")
