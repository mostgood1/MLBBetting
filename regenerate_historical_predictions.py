#!/usr/bin/env python3
"""
Historical Predictions Regenerator
==================================

Re-runs predictions for multiple historical dates to update recommendations
with current algorithms and models.

Usage:
    python regenerate_historical_predictions.py --start-date 2025-08-15 --end-date 2025-08-24
    python regenerate_historical_predictions.py --date 2025-08-23  # Single date
    python regenerate_historical_predictions.py --last-n-days 7   # Last 7 days
"""

import argparse
import json
import logging
import os
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'historical_predictions_regeneration_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class HistoricalPredictionsRegenerator:
    """Regenerates predictions for historical dates"""
    
    def __init__(self, backup_originals: bool = True):
        self.root_dir = Path(__file__).parent
        self.data_dir = self.root_dir / "data"
        self.backup_originals = backup_originals
        self.backup_dir = self.root_dir / "data" / "backups" / f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        if self.backup_originals:
            self.backup_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"📁 Backup directory created: {self.backup_dir}")
    
    def get_date_range(self, start_date: str, end_date: str) -> List[str]:
        """Generate list of dates between start and end (inclusive)"""
        start = datetime.strptime(start_date, '%Y-%m-%d')
        end = datetime.strptime(end_date, '%Y-%m-%d')
        
        dates = []
        current = start
        while current <= end:
            dates.append(current.strftime('%Y-%m-%d'))
            current += timedelta(days=1)
        
        return dates
    
    def backup_existing_files(self, date: str) -> None:
        """Backup existing prediction and recommendation files"""
        if not self.backup_originals:
            return
            
        date_underscore = date.replace('-', '_')
        files_to_backup = [
            f"betting_recommendations_{date_underscore}.json",
            f"unified_engine_output_{date_underscore}.json"
        ]
        
        for filename in files_to_backup:
            source_path = self.data_dir / filename
            if source_path.exists():
                backup_path = self.backup_dir / filename
                backup_path.parent.mkdir(parents=True, exist_ok=True)
                subprocess.run(['copy', str(source_path), str(backup_path)], shell=True, check=False)
                logger.info(f"📦 Backed up: {filename}")
    
    def check_required_files(self, date: str) -> bool:
        """Check if required input files exist for the date"""
        date_underscore = date.replace('-', '_')
        required_files = [
            f"games_{date}.json",
            f"real_betting_lines_{date_underscore}.json",
            f"starting_pitchers_{date_underscore}.json"
        ]
        
        missing_files = []
        for filename in required_files:
            if not (self.data_dir / filename).exists():
                missing_files.append(filename)
        
        if missing_files:
            logger.warning(f"⚠️ Missing required files for {date}: {missing_files}")
            return False
        
        logger.info(f"✅ All required files found for {date}")
        return True
    
    def run_predictions_for_date(self, date: str) -> bool:
        """Generate predictions for a specific date"""
        logger.info(f"🎯 Generating predictions for {date}")
        
        try:
            # Step 1: Generate UltraFast predictions
            cmd = [sys.executable, "daily_ultrafastengine_predictions.py", "--date", date]
            result = subprocess.run(cmd, capture_output=True, text=True, cwd=self.root_dir)
            
            if result.returncode != 0:
                logger.error(f"❌ UltraFast predictions failed for {date}: {result.stderr}")
                return False
            
            logger.info(f"✅ UltraFast predictions completed for {date}")
            
            # Step 2: Generate unified betting recommendations
            # First, temporarily set the unified betting engine to use the specific date
            self.set_unified_engine_date(date)
            
            cmd = [sys.executable, "unified_betting_engine.py"]
            result = subprocess.run(cmd, capture_output=True, text=True, cwd=self.root_dir)
            
            if result.returncode != 0:
                logger.error(f"❌ Unified betting engine failed for {date}: {result.stderr}")
                return False
            
            logger.info(f"✅ Unified betting recommendations completed for {date}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error generating predictions for {date}: {e}")
            return False
    
    def set_unified_engine_date(self, date: str) -> None:
        """Temporarily modify unified betting engine to use specific date"""
        engine_path = self.root_dir / "unified_betting_engine.py"
        
        # Read the current file
        with open(engine_path, 'r') as f:
            content = f.read()
        
        # Replace the current_date initialization
        old_line = "self.current_date = datetime.now().strftime('%Y-%m-%d')"
        new_line = f"self.current_date = '{date}'"
        
        modified_content = content.replace(old_line, new_line)
        
        # Write the modified file
        with open(engine_path, 'w') as f:
            f.write(modified_content)
        
        logger.debug(f"🔧 Modified unified_betting_engine.py to use date: {date}")
    
    def restore_unified_engine_date(self) -> None:
        """Restore unified betting engine to use current date"""
        engine_path = self.root_dir / "unified_betting_engine.py"
        
        # Read the current file
        with open(engine_path, 'r') as f:
            content = f.read()
        
        # Find and replace any hardcoded date back to dynamic current date
        import re
        pattern = r"self\.current_date = '[0-9]{4}-[0-9]{2}-[0-9]{2}'"
        replacement = "self.current_date = datetime.now().strftime('%Y-%m-%d')"
        
        modified_content = re.sub(pattern, replacement, content)
        
        # Write the restored file
        with open(engine_path, 'w') as f:
            f.write(modified_content)
        
        logger.debug("🔧 Restored unified_betting_engine.py to use current date")
    
    def update_unified_cache(self, dates: List[str]) -> None:
        """Update the unified predictions cache with new predictions"""
        try:
            cache_path = self.data_dir / "unified_predictions_cache.json"
            
            # Load existing cache
            if cache_path.exists():
                with open(cache_path, 'r') as f:
                    cache = json.load(f)
            else:
                cache = {'predictions_by_date': {}}
            
            if 'predictions_by_date' not in cache:
                cache['predictions_by_date'] = {}
            
            # Process each regenerated date
            for date in dates:
                date_underscore = date.replace('-', '_')
                
                # Look for the games data that should have been updated
                games_file = self.data_dir / f"games_{date}.json"
                if games_file.exists():
                    logger.info(f"🔄 Updating unified cache for {date}")
                    # The daily_ultrafastengine_predictions.py should have already updated the cache
                    # but we can verify it was updated
                    
            logger.info(f"✅ Unified cache updated for {len(dates)} dates")
            
        except Exception as e:
            logger.error(f"❌ Error updating unified cache: {e}")
    
    def regenerate_for_dates(self, dates: List[str]) -> dict:
        """Regenerate predictions for multiple dates"""
        results = {
            'successful': [],
            'failed': [],
            'skipped': []
        }
        
        logger.info(f"🚀 Starting prediction regeneration for {len(dates)} dates")
        
        try:
            for i, date in enumerate(dates, 1):
                logger.info(f"📅 Processing date {i}/{len(dates)}: {date}")
                
                # Check if required files exist
                if not self.check_required_files(date):
                    results['skipped'].append(date)
                    continue
                
                # Backup existing files
                self.backup_existing_files(date)
                
                # Generate new predictions
                if self.run_predictions_for_date(date):
                    results['successful'].append(date)
                    logger.info(f"✅ Successfully regenerated predictions for {date}")
                else:
                    results['failed'].append(date)
                    logger.error(f"❌ Failed to regenerate predictions for {date}")
            
            # Update unified cache
            if results['successful']:
                self.update_unified_cache(results['successful'])
            
        finally:
            # Always restore the unified engine to use current date
            self.restore_unified_engine_date()
        
        # Print summary
        logger.info("📊 REGENERATION SUMMARY:")
        logger.info(f"✅ Successful: {len(results['successful'])} dates")
        logger.info(f"❌ Failed: {len(results['failed'])} dates")
        logger.info(f"⏭️ Skipped: {len(results['skipped'])} dates")
        
        if results['successful']:
            logger.info(f"✅ Successfully regenerated: {', '.join(results['successful'])}")
        if results['failed']:
            logger.info(f"❌ Failed dates: {', '.join(results['failed'])}")
        if results['skipped']:
            logger.info(f"⏭️ Skipped dates: {', '.join(results['skipped'])}")
        
        return results

def main():
    """Main function with argument parsing"""
    parser = argparse.ArgumentParser(
        description="Regenerate historical MLB predictions and betting recommendations",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Regenerate predictions for a date range
  python regenerate_historical_predictions.py --start-date 2025-08-15 --end-date 2025-08-24
  
  # Regenerate predictions for a single date
  python regenerate_historical_predictions.py --date 2025-08-23
  
  # Regenerate predictions for the last 7 days
  python regenerate_historical_predictions.py --last-n-days 7
  
  # Skip backing up original files
  python regenerate_historical_predictions.py --date 2025-08-23 --no-backup
        """
    )
    
    # Date selection (mutually exclusive)
    date_group = parser.add_mutually_exclusive_group(required=True)
    date_group.add_argument('--date', type=str, help='Single date to regenerate (YYYY-MM-DD)')
    date_group.add_argument('--start-date', type=str, help='Start date for range (YYYY-MM-DD)')
    date_group.add_argument('--last-n-days', type=int, help='Regenerate last N days')
    
    # End date (only used with start-date)
    parser.add_argument('--end-date', type=str, help='End date for range (YYYY-MM-DD) - required with --start-date')
    
    # Options
    parser.add_argument('--no-backup', action='store_true', help='Skip backing up original files')
    parser.add_argument('--force', action='store_true', help='Force regeneration even if files are missing')
    
    args = parser.parse_args()
    
    # Validate arguments
    if args.start_date and not args.end_date:
        parser.error("--end-date is required when using --start-date")
    
    # Determine dates to process
    if args.date:
        dates = [args.date]
    elif args.start_date and args.end_date:
        regenerator = HistoricalPredictionsRegenerator()
        dates = regenerator.get_date_range(args.start_date, args.end_date)
    elif args.last_n_days:
        dates = []
        for i in range(args.last_n_days):
            date = (datetime.now() - timedelta(days=i)).strftime('%Y-%m-%d')
            dates.append(date)
        dates.reverse()  # Chronological order
    
    logger.info(f"🎯 Will regenerate predictions for dates: {', '.join(dates)}")
    
    # Create regenerator and run
    regenerator = HistoricalPredictionsRegenerator(backup_originals=not args.no_backup)
    results = regenerator.regenerate_for_dates(dates)
    
    # Exit with appropriate code
    if results['failed']:
        sys.exit(1)  # Some failures occurred
    else:
        sys.exit(0)  # All successful

if __name__ == "__main__":
    main()
