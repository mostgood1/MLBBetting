#!/usr/bin/env python3
"""
Complete Daily Refresh Script
===============================
Runs ALL necessary data updates in the correct order for daily MLB predictions:

1. Fetch today's games
2. Update team strength data  
3. Update pitcher stats
4. Fetch starting pitchers
5. Fetch real betting lines
6. Generate predictions
7. Generate betting recommendations
8. Update unified cache

This ensures everything is fresh and in the right order.
"""

import subprocess
import sys
import os
import json
import logging
from datetime import datetime, date
from pathlib import Path

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class CompleteDailyRefresh:
    def __init__(self, target_date=None):
        self.target_date = target_date or datetime.now().strftime('%Y-%m-%d')
        self.data_dir = Path("data")
        self.data_dir.mkdir(exist_ok=True)
        
        logger.info(f"🚀 Complete Daily Refresh for {self.target_date}")
    
    def run_script(self, script_name, description, args=None):
        """Run a Python script and handle errors"""
        logger.info(f"📝 {description}...")
        
        cmd = [sys.executable, script_name]
        if args:
            cmd.extend(args)
            
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            if result.returncode == 0:
                logger.info(f"✅ {description} completed successfully")
                if result.stdout.strip():
                    logger.info(f"   Output: {result.stdout.strip()[:200]}...")
                return True
            else:
                logger.error(f"❌ {description} failed with code {result.returncode}")
                if result.stderr:
                    logger.error(f"   Error: {result.stderr.strip()}")
                return False
        except subprocess.TimeoutExpired:
            logger.error(f"❌ {description} timed out after 300 seconds")
            return False
        except Exception as e:
            logger.error(f"❌ {description} failed with exception: {e}")
            return False
    
    def check_file_exists(self, filename, description):
        """Check if a required file exists"""
        if self.data_dir.joinpath(filename).exists():
            logger.info(f"✅ {description} exists")
            return True
        else:
            logger.warning(f"❌ {description} missing")
            return False
    
    def run_complete_refresh(self):
        """Run the complete daily refresh sequence"""
        logger.info("🎯 Starting Complete Daily Refresh Sequence")
        
        success_count = 0
        total_steps = 9  # Updated total
        
        # Step 1: Fetch today's games
        if self.run_script("fetch_today_games.py", "Fetching today's games"):
            success_count += 1
            self.check_file_exists(f"games_{self.target_date}.json", "Games data")
        
        # Step 2: Update core team data
        if self.run_script("daily_data_updater.py", "Updating team strength and pitcher stats"):
            success_count += 1
            self.check_file_exists("master_team_strength.json", "Team strength data")
            self.check_file_exists("master_pitcher_stats.json", "Pitcher stats data")
        
        # Step 3: Fetch starting pitchers
        if self.run_script("fetch_todays_starters.py", "Fetching starting pitchers"):
            success_count += 1
            expected_starter_file = f"starting_pitchers_{self.target_date.replace('-', '_')}.json"
            self.check_file_exists(expected_starter_file, "Starting pitchers data")
        
        # Step 4: Fetch real betting lines
        if self.run_script("fetch_betting_lines_real.py", "Fetching real betting lines"):
            success_count += 1
            expected_lines_file = f"real_betting_lines_{self.target_date.replace('-', '_')}.json"
            self.check_file_exists(expected_lines_file, "Real betting lines data")
        
        # Step 5: Generate predictions
        if self.run_script("daily_ultrafastengine_predictions.py", "Generating predictions", ["--date", self.target_date]):
            success_count += 1
        
        # Step 6: Generate betting recommendations  
        if self.run_script("betting_recommendations_engine.py", "Generating betting recommendations"):
            success_count += 1
            expected_recs_file = f"betting_recommendations_{self.target_date.replace('-', '_')}.json"
            self.check_file_exists(expected_recs_file, "Betting recommendations")
        
        # Step 7: Update unified cache
        if self.update_unified_cache():
            success_count += 1
        
        # Step 8: Fetch yesterday's final scores for historical analysis
        if self.fetch_yesterday_final_scores():
            success_count += 1
        
        # Step 9: Final verification
        if self.verify_all_data():
            success_count += 1
        
        # Summary
        total_steps = 9  # Updated total
        logger.info(f"📊 Daily Refresh Summary: {success_count}/{total_steps} steps completed")
        
        if success_count == total_steps:
            logger.info("🎉 Complete Daily Refresh SUCCESSFUL! All data is ready.")
            return True
        else:
            logger.warning(f"⚠️ Daily Refresh PARTIAL: {total_steps - success_count} steps failed")
            return False
    
    def update_unified_cache(self):
        """Update the unified predictions cache"""
        logger.info("📝 Updating unified predictions cache...")
        
        try:
            # Load predictions if they exist
            prediction_file = self.data_dir / f"predictions_{self.target_date.replace('-', '_')}.json"
            if not prediction_file.exists():
                logger.warning(f"No predictions file found at {prediction_file}")
                return False
            
            with open(prediction_file, 'r') as f:
                predictions = json.load(f)
            
            # Load existing cache or create new
            cache_file = self.data_dir / "unified_predictions_cache.json"
            if cache_file.exists():
                with open(cache_file, 'r') as f:
                    cache = json.load(f)
            else:
                cache = {"predictions_by_date": {}}
            
            # Update cache with today's predictions
            cache["predictions_by_date"][self.target_date] = predictions
            
            # Save updated cache
            with open(cache_file, 'w') as f:
                json.dump(cache, f, indent=2)
            
            logger.info("✅ Unified cache updated successfully")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to update unified cache: {e}")
            return False
    
    def fetch_yesterday_final_scores(self):
        """Fetch final scores for yesterday's games for historical analysis"""
        logger.info("📝 Fetching yesterday's final scores for historical analysis...")
        
        try:
            from datetime import datetime, timedelta
            yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
            
            # Check if final scores already exist for yesterday
            scores_file = self.data_dir / f"final_scores_{yesterday.replace('-', '_')}.json"
            if scores_file.exists():
                logger.info(f"✅ Final scores for {yesterday} already exist")
                return True
            
            # Run the final scores fetcher
            if self.run_script("tools/fetch_final_scores.py", f"Fetching final scores for {yesterday}", [yesterday]):
                logger.info(f"✅ Final scores fetched for {yesterday}")
                return True
            else:
                logger.warning(f"⚠️ Failed to fetch final scores for {yesterday}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Failed to fetch yesterday's final scores: {e}")
            return False
    
    def verify_all_data(self):
        """Verify all required data files exist and are recent"""
        logger.info("📝 Verifying all data files...")
        
        required_files = [
            f"games_{self.target_date}.json",
            f"starting_pitchers_{self.target_date.replace('-', '_')}.json", 
            f"real_betting_lines_{self.target_date.replace('-', '_')}.json",
            f"predictions_{self.target_date.replace('-', '_')}.json",
            f"betting_recommendations_{self.target_date.replace('-', '_')}.json",
            "master_team_strength.json",
            "master_pitcher_stats.json",
            "unified_predictions_cache.json"
        ]
        
        missing_files = []
        for filename in required_files:
            if not self.data_dir.joinpath(filename).exists():
                missing_files.append(filename)
        
        if missing_files:
            logger.error(f"❌ Missing files: {missing_files}")
            return False
        else:
            logger.info("✅ All required data files exist")
            return True

def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Complete Daily MLB Data Refresh")
    parser.add_argument('--date', type=str, help='Target date (YYYY-MM-DD)', default=None)
    args = parser.parse_args()
    
    refresher = CompleteDailyRefresh(target_date=args.date)
    success = refresher.run_complete_refresh()
    
    if success:
        print("\n🎉 DAILY REFRESH COMPLETE! Your MLB system is ready for today.")
        sys.exit(0)
    else:
        print("\n⚠️ DAILY REFRESH INCOMPLETE. Check logs for issues.")
        sys.exit(1)

if __name__ == "__main__":
    main()
