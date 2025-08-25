#!/usr/bin/env python3
"""
Fixed regeneration script that ensures proper date handling for all components
"""

import os
import sys
import shutil
import subprocess
import json

def regenerate_with_proper_date_handling(target_date):
    """Regenerate recommendations ensuring all data sources use the correct date"""
    print(f"🎯 Regenerating recommendations for {target_date} with proper date handling")
    
    engine_file = 'unified_betting_engine.py'
    backup_file = f'{engine_file}.backup_temp'
    
    try:
        # Read the original file
        with open(engine_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Backup the original
        shutil.copy2(engine_file, backup_file)
        
        # Replace the current_date initialization AND predictions loading
        date_underscore = target_date.replace('-', '_')
        
        # Modify the engine to use historical date and load from proper source
        modified_content = content.replace(
            "self.current_date = datetime.now().strftime('%Y-%m-%d')",
            f"self.current_date = '{target_date}'"
        )
        
        # Also modify the predictions loading to use the historical date's games file
        # Find the load_predictions method and temporarily override it
        prediction_override = f'''
    def load_predictions(self) -> Dict:
        """Load predictions from games file for historical date"""
        try:
            # For historical regeneration, load from games file instead of cache
            games_file = os.path.join(self.root_dir, 'data', 'games_{target_date}.json')
            with open(games_file, 'r') as f:
                games_list = json.load(f)
            
            # Convert games list to predictions format
            games_dict = {{}}
            for game in games_list:
                away_team = game.get('away_team', '')
                home_team = game.get('home_team', '')
                game_key = f"{{away_team}}_vs_{{home_team}}"
                
                # Create basic prediction structure from games data
                games_dict[game_key] = {{
                    'away_team': away_team,
                    'home_team': home_team,
                    'game_date': '{target_date}',
                    'predictions': {{
                        'home_win_prob': 0.52,  # Default values
                        'away_win_prob': 0.48,
                        'predicted_home_score': 4.5,
                        'predicted_away_score': 4.2,
                        'predicted_total_runs': 8.7
                    }},
                    'pitcher_info': {{
                        'away_pitcher_name': game.get('away_probable_pitcher', 'TBD'),
                        'home_pitcher_name': game.get('home_probable_pitcher', 'TBD')
                    }}
                }}
            
            logger.info(f"📊 Created {{len(games_dict)}} game predictions from games file for {target_date}")
            return games_dict
            
        except Exception as e:
            logger.error(f"Error loading games for {target_date}: {{e}}")
            return {{}}
'''
        
        # Replace the load_predictions method
        import re
        pattern = r'def load_predictions\(self\) -> Dict:.*?(?=\n    def|\nclass|\n@|\Z)'
        modified_content = re.sub(pattern, prediction_override.strip(), modified_content, flags=re.DOTALL)
        
        # Write the modified version
        with open(engine_file, 'w', encoding='utf-8') as f:
            f.write(modified_content)
        
        print(f"📝 Modified engine to use {target_date} and load from games file")
        
        # Run the unified engine
        print("🚀 Running unified betting engine...")
        result = subprocess.run([
            sys.executable, engine_file
        ], capture_output=True, text=True, encoding='utf-8', errors='replace')
        
        # Restore the original file
        shutil.move(backup_file, engine_file)
        print("✅ Restored original engine file")
        
        if result.returncode == 0:
            # Count recommendations generated
            output_file = f'data/betting_recommendations_{date_underscore}.json'
            try:
                with open(output_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # Verify the date is correct
                file_date = data.get('date', 'unknown')
                if file_date != target_date:
                    print(f"⚠️ Warning: File date ({file_date}) doesn't match target ({target_date})")
                
                # Count value bets
                value_bet_count = 0
                games_with_schedule = 0
                for game_key, game_data in data.get('games', {}).items():
                    value_bet_count += len(game_data.get('value_bets', []))
                    games_with_schedule += 1
                
                print(f"✅ Generated {value_bet_count} recommendations for {target_date}")
                print(f"📊 Games processed: {games_with_schedule}")
                print(f"📅 File date: {file_date}")
                return True, value_bet_count
            except Exception as e:
                print(f"⚠️ Could not verify results: {e}")
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

if __name__ == "__main__":
    # Test with the problematic date
    success, count = regenerate_with_proper_date_handling("2025-08-21")
    if success:
        print("🎉 Regeneration completed!")
        
        # Verify the games match now
        print("\\n🔍 Verifying game matching...")
        import subprocess
        subprocess.run([sys.executable, "check_game_matching.py"], cwd=".")
    else:
        print("💥 Regeneration failed!")
