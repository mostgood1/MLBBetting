#!/usr/bin/env python3
"""
Batch regeneration script to fix all earlier dates with missing recommendations
"""

import os
import sys
import shutil
import subprocess
import json
from datetime import datetime, timedelta

def regenerate_for_date(target_date):
    """Regenerate recommendations by temporarily modifying the unified engine"""
    print(f"\n🎯 Regenerating recommendations for {target_date}")
    
    engine_file = 'unified_betting_engine.py'
    backup_file = f'{engine_file}.backup_temp'
    
    try:
        # Check if required files exist
        date_underscore = target_date.replace('-', '_')
        required_files = [
            f'data/games_{target_date}.json',
            f'data/real_betting_lines_{date_underscore}.json',
            f'data/starting_pitchers_{date_underscore}.json'
        ]
        
        missing_files = [f for f in required_files if not os.path.exists(f)]
        if missing_files:
            print(f"❌ Missing files for {target_date}: {missing_files}")
            return False, 0
        
        # Read the original file
        with open(engine_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Backup the original
        shutil.copy2(engine_file, backup_file)
        
        # Replace the current_date initialization
        modified_content = content.replace(
            "self.current_date = datetime.now().strftime('%Y-%m-%d')",
            f"self.current_date = '{target_date}'"
        )
        
        # Write the modified version
        with open(engine_file, 'w', encoding='utf-8') as f:
            f.write(modified_content)
        
        # Run the unified engine
        result = subprocess.run([
            sys.executable, engine_file
        ], capture_output=True, text=True, encoding='utf-8', errors='replace')
        
        # Restore the original file
        shutil.move(backup_file, engine_file)
        
        if result.returncode == 0:
            # Count recommendations generated
            output_file = f'data/betting_recommendations_{date_underscore}.json'
            try:
                with open(output_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # Count value bets
                value_bet_count = 0
                for game_data in data.get('games', {}).values():
                    value_bet_count += len(game_data.get('value_bets', []))
                
                print(f"✅ Generated {value_bet_count} recommendations for {target_date}")
                return True, value_bet_count
            except Exception as e:
                print(f"⚠️ Could not count recommendations: {e}")
                return True, -1
        else:
            print(f"❌ Engine failed for {target_date}")
            print("STDERR:", result.stderr[:500])
            return False, 0
            
    except Exception as e:
        # Ensure we restore the original file even if there's an error
        if os.path.exists(backup_file):
            shutil.move(backup_file, engine_file)
        print(f"💥 Error: {e}")
        return False, 0

def main():
    # Dates that were showing 0 recommendations before the fix
    problem_dates = [
        "2025-08-15",  # We already fixed this one, but including for completeness
        "2025-08-16", 
        "2025-08-19", 
        "2025-08-20"
    ]
    
    print("🚀 Starting batch regeneration for problem dates...")
    print(f"📅 Dates to process: {', '.join(problem_dates)}")
    
    results = {}
    total_before = 0
    total_after = 0
    
    for date in problem_dates:
        success, count = regenerate_for_date(date)
        results[date] = {'success': success, 'count': count}
        if success and count >= 0:
            total_after += count
    
    print("\n" + "="*60)
    print("📊 BATCH REGENERATION SUMMARY")
    print("="*60)
    
    for date, result in results.items():
        status = "✅" if result['success'] else "❌"
        count_str = f"{result['count']} recommendations" if result['count'] >= 0 else "unknown count"
        print(f"{status} {date}: {count_str}")
    
    successful_dates = [date for date, result in results.items() if result['success']]
    print(f"\n📈 Successfully regenerated: {len(successful_dates)}/{len(problem_dates)} dates")
    print(f"🎯 Total recommendations generated: {total_after}")
    
    if len(successful_dates) == len(problem_dates):
        print("🎉 All problem dates successfully regenerated!")
    else:
        failed_dates = [date for date, result in results.items() if not result['success']]
        print(f"⚠️ Failed dates: {', '.join(failed_dates)}")

if __name__ == "__main__":
    main()
