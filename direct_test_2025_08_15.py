#!/usr/bin/env python3
"""
Direct unified betting engine run for 2025-08-15
"""
import sys
import os
sys.path.append('.')

from unified_betting_engine import UnifiedBettingEngine

# Create engine for 2025-08-15
engine = UnifiedBettingEngine()
engine.current_date = '2025-08-15'
engine.betting_lines_path = 'data/real_betting_lines_2025_08_15.json'
engine.output_path = 'data/betting_recommendations_2025_08_15_DIRECT.json'

print(f"🎯 Running unified engine directly for {engine.current_date}")
print(f"📊 Output file: {engine.output_path}")

# Generate recommendations
result = engine.generate_recommendations()

# Count recommendations
total_recs = 0
for game in result['games'].values():
    total_recs += len(game.get('value_bets', []))

print(f"✅ Generated {total_recs} recommendations")

# Show some recommendations
count = 0
for game_key, game in result['games'].items():
    if game.get('value_bets'):
        for rec in game['value_bets']:
            print(f"  {game_key}: {rec['recommendation']} (EV: {rec['expected_value']:.3f})")
            count += 1
            if count >= 5:  # Show first 5
                break
        if count >= 5:
            break

print(f"🎯 File saved to: {engine.output_path}")
print("This shows what the regeneration script SHOULD be producing!")
