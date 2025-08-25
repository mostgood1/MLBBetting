#!/usr/bin/env python3
"""
Check game matching for all dates with betting recommendations
"""

import os
from check_game_matching import check_game_matching

def check_all_dates():
    print("🎯 Checking game matching for all historical dates")
    print("=" * 60)
    
    # Get all betting recommendation files
    dates = []
    for filename in os.listdir('data'):
        if filename.startswith('betting_recommendations_') and filename.endswith('.json'):
            date_part = filename.replace('betting_recommendations_', '').replace('.json', '')
            date = date_part.replace('_', '-')
            dates.append(date)
    
    dates.sort()
    print(f"Found {len(dates)} dates with betting recommendations")
    
    summary = {}
    
    for date in dates:
        try:
            print(f"\n{'='*50}")
            check_game_matching(date)
            # Extract match rate from the output (this is a bit hacky but works)
            summary[date] = "Checked"
        except Exception as e:
            print(f"❌ Error checking {date}: {e}")
            summary[date] = f"Error: {e}"
    
    print(f"\n\n🎯 OVERALL SUMMARY")
    print("=" * 60)
    for date, status in summary.items():
        print(f"{date}: {status}")

if __name__ == "__main__":
    check_all_dates()
