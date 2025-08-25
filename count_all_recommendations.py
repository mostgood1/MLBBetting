#!/usr/bin/env python3
"""
Count total recommendations across all historical dates
"""

import os
import json

def count_recommendations():
    dates = [
        '2025-08-15', '2025-08-16', '2025-08-17', '2025-08-18', 
        '2025-08-19', '2025-08-20', '2025-08-21', '2025-08-22', '2025-08-23'
    ]
    
    print("📊 Historical Betting Recommendations Summary")
    print("=" * 50)
    
    total_recommendations = 0
    date_counts = {}
    
    for date in dates:
        date_underscore = date.replace('-', '_')
        file_path = f'data/betting_recommendations_{date_underscore}.json'
        
        if os.path.exists(file_path):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # Count value bets
                count = 0
                for game_data in data.get('games', {}).values():
                    count += len(game_data.get('value_bets', []))
                
                date_counts[date] = count
                total_recommendations += count
                print(f"{date}: {count} recommendations")
                
            except Exception as e:
                print(f"{date}: Error reading file - {e}")
                date_counts[date] = 0
        else:
            print(f"{date}: File not found")
            date_counts[date] = 0
    
    print("=" * 50)
    print(f"📈 Total recommendations: {total_recommendations}")
    
    # Show dates with most recommendations
    top_dates = sorted(date_counts.items(), key=lambda x: x[1], reverse=True)[:3]
    print(f"🏆 Top performing dates:")
    for date, count in top_dates:
        print(f"   {date}: {count} recommendations")

if __name__ == "__main__":
    count_recommendations()
