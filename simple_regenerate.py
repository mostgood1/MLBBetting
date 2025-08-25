#!/usr/bin/env python3
"""
Simple Historical Predictions Regenerator - Windows Compatible
Regenerates historical predictions without Unicode characters
"""

import os
import json
import shutil
import subprocess
import sys
from datetime import datetime, timedelta
import argparse
import logging

# Configure logging without Unicode characters
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('regeneration.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class SimpleRegenerator:
    def __init__(self):
        self.data_dir = os.path.join(os.getcwd(), 'data')
        self.backup_dir = os.path.join(self.data_dir, 'backups', f'backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}')
        if not os.path.exists(self.backup_dir):
            os.makedirs(self.backup_dir)
        logger.info(f"Backup directory: {self.backup_dir}")

    def check_required_files(self, date):
        """Check if all required files exist for the given date"""
        # Games files use hyphens, others use underscores
        date_str = date.replace('-', '_')
        required_files = [
            f'games_{date}.json',  # Uses hyphens
            f'real_betting_lines_{date_str}.json',  # Uses underscores
            f'starting_pitchers_{date_str}.json'    # Uses underscores
        ]
        
        missing_files = []
        for filename in required_files:
            filepath = os.path.join(self.data_dir, filename)
            if not os.path.exists(filepath):
                missing_files.append(filename)
        
        if missing_files:
            logger.error(f"Missing files for {date}: {missing_files}")
            return False
        
        logger.info(f"All required files found for {date}")
        return True

    def backup_existing_files(self, date):
        """Backup existing betting recommendations file"""
        date_str = date.replace('-', '_')
        betting_file = f'betting_recommendations_{date_str}.json'
        betting_path = os.path.join(self.data_dir, betting_file)
        
        if os.path.exists(betting_path):
            backup_path = os.path.join(self.backup_dir, betting_file)
            shutil.copy2(betting_path, backup_path)
            logger.info(f"Backed up: {betting_file}")

    def run_predictions_for_date(self, date):
        """Run UltraFast predictions for a specific date"""
        try:
            logger.info(f"Generating predictions for {date}")
            
            # Run daily_ultrafastengine_predictions.py with date override
            env = os.environ.copy()
            env['PREDICTION_DATE'] = date
            
            result = subprocess.run([
                sys.executable, 'daily_ultrafastengine_predictions.py'
            ], capture_output=True, text=True, encoding='utf-8', env=env)
            
            if result.returncode == 0:
                logger.info(f"UltraFast predictions completed for {date}")
                
                # Now run unified betting engine with date override
                return self.run_unified_engine(date)
            else:
                logger.error(f"UltraFast predictions failed for {date}: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"Error generating predictions for {date}: {e}")
            return False

    def run_unified_engine(self, date):
        """Run unified betting engine for a specific date"""
        try:
            logger.info(f"Running unified betting engine for {date}")
            
            # Temporarily modify unified_betting_engine.py to use the specific date
            engine_file = 'unified_betting_engine.py'
            backup_engine = f'{engine_file}.backup'
            
            # Read the original file with proper encoding
            with open(engine_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Backup original
            shutil.copy2(engine_file, backup_engine)
            
            # Modify to use specific date - update ALL date-dependent paths
            date_underscore = date.replace('-', '_')
            modified_content = content.replace(
                "today_date = datetime.now().strftime('%Y-%m-%d')",
                f"today_date = '{date}'"
            ).replace(
                "self.betting_lines_path = os.path.join(self.root_dir, 'data', f'real_betting_lines_{self.current_date.replace(\"-\", \"_\")}.json')",
                f"self.betting_lines_path = os.path.join(self.root_dir, 'data', 'real_betting_lines_{date_underscore}.json')"
            ).replace(
                "self.output_path = os.path.join(self.root_dir, 'data', f'betting_recommendations_{self.current_date.replace(\"-\", \"_\")}.json')",
                f"self.output_path = os.path.join(self.root_dir, 'data', 'betting_recommendations_{date_underscore}.json')"
            )
            
            # Write modified version
            with open(engine_file, 'w', encoding='utf-8') as f:
                f.write(modified_content)
            
            # Run the unified engine
            result = subprocess.run([
                sys.executable, engine_file
            ], capture_output=True, text=True, encoding='utf-8')
            
            # Restore original file
            shutil.move(backup_engine, engine_file)
            
            if result.returncode == 0:
                logger.info(f"Unified betting engine completed for {date}")
                return True
            else:
                logger.error(f"Unified betting engine failed for {date}: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"Error running unified engine for {date}: {e}")
            return False

    def regenerate_for_dates(self, dates):
        """Regenerate predictions for multiple dates"""
        logger.info(f"Starting regeneration for {len(dates)} dates")
        
        results = {'successful': [], 'failed': []}
        
        for i, date in enumerate(dates, 1):
            logger.info(f"Processing date {i}/{len(dates)}: {date}")
            
            # Check if required files exist
            if not self.check_required_files(date):
                logger.error(f"Skipping {date} - missing required files")
                results['failed'].append(date)
                continue
            
            # Backup existing files
            self.backup_existing_files(date)
            
            # Run predictions
            if self.run_predictions_for_date(date):
                logger.info(f"Successfully regenerated {date}")
                results['successful'].append(date)
            else:
                logger.error(f"Failed to regenerate {date}")
                results['failed'].append(date)
        
        return results

def parse_date_range(start_date, end_date):
    """Parse date range and return list of dates"""
    start = datetime.strptime(start_date, '%Y-%m-%d')
    end = datetime.strptime(end_date, '%Y-%m-%d')
    
    dates = []
    current = start
    while current <= end:
        dates.append(current.strftime('%Y-%m-%d'))
        current += timedelta(days=1)
    
    return dates

def main():
    parser = argparse.ArgumentParser(description='Regenerate historical predictions')
    parser.add_argument('--start-date', required=True, help='Start date (YYYY-MM-DD)')
    parser.add_argument('--end-date', required=True, help='End date (YYYY-MM-DD)')
    parser.add_argument('--exclude', nargs='*', default=[], help='Dates to exclude (YYYY-MM-DD)')
    
    args = parser.parse_args()
    
    # Parse date range
    try:
        dates = parse_date_range(args.start_date, args.end_date)
    except ValueError as e:
        logger.error(f"Invalid date format: {e}")
        return
    
    # Exclude specific dates
    if args.exclude:
        dates = [d for d in dates if d not in args.exclude]
        logger.info(f"Excluding dates: {args.exclude}")
    
    logger.info(f"Will regenerate predictions for dates: {', '.join(dates)}")
    
    # Create regenerator and run
    regenerator = SimpleRegenerator()
    results = regenerator.regenerate_for_dates(dates)
    
    # Summary
    logger.info("=" * 50)
    logger.info("REGENERATION SUMMARY")
    logger.info("=" * 50)
    logger.info(f"Successfully regenerated: {len(results['successful'])} dates")
    for date in results['successful']:
        logger.info(f"  SUCCESS: {date}")
    
    logger.info(f"Failed to regenerate: {len(results['failed'])} dates")
    for date in results['failed']:
        logger.info(f"  FAILED: {date}")
    
    if results['failed']:
        logger.error("Some predictions could not be regenerated")
        sys.exit(1)
    else:
        logger.info("All predictions regenerated successfully!")

if __name__ == "__main__":
    main()
