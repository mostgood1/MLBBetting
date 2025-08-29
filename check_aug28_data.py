#!/usr/bin/env python3
"""
Quick script to check August 28 data issues
"""

import json
from pathlib import Path

def check_aug28_data():
    cache_file = Path("data/unified_predictions_cache.json")
    
    if not cache_file.exists():
        print("Cache file not found!")
        return
    
    with open(cache_file, 'r') as f:
        data = json.load(f)
    
    aug28_data = data.get('2025-08-28', {})
    print(f"August 28 data keys: {list(aug28_data.keys())}")
    
    if 'games' in aug28_data:
        games = aug28_data['games']
        print(f"Number of games: {len(games)}")
        
        if games:
            sample_game = games[0]
            print(f"Sample game keys: {list(sample_game.keys())}")
            print(f"Sample predicted_total: {sample_game.get('predicted_total', 'N/A')}")
            print(f"Sample home_prob: {sample_game.get('home_prob', 'N/A')}")
            print(f"Sample away_prob: {sample_game.get('away_prob', 'N/A')}")
            
            # Check if any games have non-zero predicted_total
            valid_predictions = [g for g in games if g.get('predicted_total', 0) > 0]
            print(f"Games with valid predictions: {len(valid_predictions)}")
    
    # Also check recent dates
    recent_dates = ['2025-08-26', '2025-08-27', '2025-08-28']
    for date in recent_dates:
        date_data = data.get(date, {})
        games = date_data.get('games', [])
        valid_preds = len([g for g in games if g.get('predicted_total', 0) > 0])
        print(f"{date}: {len(games)} games, {valid_preds} with valid predictions")

if __name__ == "__main__":
    check_aug28_data()
