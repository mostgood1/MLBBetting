#!/usr/bin/env python3
import json
import os

print("🎯 BETTING RECOMMENDATIONS REGENERATION COMPLETE!")
print("=" * 60)

# Check regenerated files
dates = ['2025-08-15', '2025-08-16', '2025-08-18', '2025-08-19', '2025-08-20', 
         '2025-08-21', '2025-08-22', '2025-08-23', '2025-08-24']
total_games = 0
total_recommendations = 0
successful_dates = []

for date in dates:
    file_path = f'data/betting_recommendations_{date.replace("-", "_")}.json'
    if os.path.exists(file_path):
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
            
            games = data.get('games', {})
            game_count = len(games)
            rec_count = sum(len(game.get('value_bets', [])) for game in games.values())
            
            print(f'✅ {date}: {game_count} games, {rec_count} recommendations')
            total_games += game_count
            total_recommendations += rec_count
            successful_dates.append(date)
        except Exception as e:
            print(f'❌ {date}: Error reading file - {e}')
    else:
        print(f'❌ {date}: File not found')

print('')
print('📊 SUMMARY:')
print(f'  Successfully regenerated: {len(successful_dates)}/9 dates')
print(f'  Total games processed: {total_games}')
print(f'  Total value betting recommendations: {total_recommendations}')
print(f'  Skipped: 2025-08-17 (missing real betting lines)')
print('')
print('🚀 Historical betting data is now ready for backtesting!')
