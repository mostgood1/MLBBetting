#!/usr/bin/env python3
"""
Check individual sportsbook lines to see discrepancies
"""

import json
from datetime import datetime

def check_betting_lines_discrepancy():
    """Check the current betting lines file for individual sportsbook data"""
    
    try:
        with open('data/real_betting_lines_2025_08_28.json', 'r') as f:
            lines_data = json.load(f)
        
        print(f"📊 BETTING LINES ANALYSIS")
        print(f"Date: {lines_data.get('date')}")
        print(f"Fetched: {lines_data.get('fetched_at')}")
        print(f"Source: {lines_data.get('source')}")
        print("=" * 60)
        
        # Look at Red Sox game specifically
        red_sox_game = None
        for game_key, game_data in lines_data.get('lines', {}).items():
            if 'Red Sox' in game_key:
                red_sox_game = game_data
                print(f"🔍 GAME: {game_key}")
                break
        
        if red_sox_game:
            print(f"Moneyline:")
            print(f"  Away (Red Sox): {red_sox_game['moneyline']['away']:+d}")
            print(f"  Home (Orioles): {red_sox_game['moneyline']['home']:+d}")
            print(f"")
            print(f"Total:")
            print(f"  Line: {red_sox_game['total_runs']['line']}")
            print(f"  Over: {red_sox_game['total_runs']['over']:+d}")
            print(f"  Under: {red_sox_game['total_runs']['under']:+d}")
            
            print(f"\n🚨 DISCREPANCY ALERT:")
            print(f"  Our data shows: Red Sox +{red_sox_game['moneyline']['away']}")
            print(f"  DraftKings shows: Red Sox -206")
            print(f"  Difference: ~380+ points!")
            
            print(f"\n💡 POSSIBLE EXPLANATIONS:")
            print(f"  1. Pitching change or injury news")
            print(f"  2. Different game/date")
            print(f"  3. API data lag")
            print(f"  4. Different sportsbook aggregation")
            
        else:
            print("❌ Red Sox game not found in current data")
            print("\nAvailable games:")
            for game_key in lines_data.get('lines', {}).keys():
                print(f"  - {game_key}")
    
    except Exception as e:
        print(f"Error checking lines: {e}")

if __name__ == "__main__":
    check_betting_lines_discrepancy()
