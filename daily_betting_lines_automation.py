#!/usr/bin/env python3
"""
Daily Real Betting Lines Automation
===================================

This script automatically fetches real betting lines every day to ensure
NO FAKE DATA is ever used in the MLB betting application.

Features:
- Fetches fresh betting lines from OddsAPI
- Updates the Flask app's betting lines cache
- Runs automatically via Windows Task Scheduler
- Comprehensive error handling and logging
- Validates data integrity

Usage:
- Run manually: python daily_betting_lines_automation.py
- Schedule via Task Scheduler: daily at 8:00 AM
"""

import os
import sys
import json
import logging
import subprocess
from datetime import datetime, timedelta
import traceback

# Setup logging
def setup_logging():
    """Setup comprehensive logging for the automation"""
    log_dir = os.path.join(os.path.dirname(__file__), 'logs')
    os.makedirs(log_dir, exist_ok=True)
    
    log_file = os.path.join(log_dir, f'daily_betting_lines_{datetime.now().strftime("%Y%m%d")}.log')
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )
    return logging.getLogger(__name__)

def run_command(command, description, logger):
    """Run a command and handle errors"""
    try:
        logger.info(f"Running: {command}")
        
        # Run commands using the current Python interpreter where applicable
        if isinstance(command, str):
            # Preserve backward compatibility for shell commands, but prefer list form
            cmd = command
        else:
            cmd = command

        result = subprocess.run(
            cmd,
            shell=isinstance(cmd, str),
            capture_output=True,
            text=True,
            cwd=os.path.dirname(__file__)
        )
        
        if result.returncode == 0:
            logger.info(f"SUCCESS: {description}")
            if result.stdout:
                logger.info(f"Output: {result.stdout}")
            return True
        else:
            logger.error(f"FAILED: {description}")
            logger.error(f"Error: {result.stderr}")
            return False
            
    except Exception as e:
        logger.error(f"ERROR: {description} - EXCEPTION: {e}")
        return False

def validate_betting_lines(logger):
    """Validate that betting lines were successfully created"""
    try:
        today = datetime.now().strftime('%Y-%m-%d')
        today_underscore = datetime.now().strftime('%Y_%m_%d')
        
        # Check for both date formats
        possible_files = [
            f'MLB-Betting/data/real_betting_lines_{today}.json',
            f'MLB-Betting/data/real_betting_lines_{today_underscore}.json'
        ]
        
        for file_path in possible_files:
            if os.path.exists(file_path):
                with open(file_path, 'r') as f:
                    data = json.load(f)
                    
                if 'lines' in data and len(data['lines']) > 0:
                    game_count = len(data['lines'])
                    logger.info(f"VALIDATION: Found {game_count} games with real betting lines in {file_path}")
                    
                    # Log sample game for verification
                    sample_game = list(data['lines'].keys())[0]
                    sample_lines = data['lines'][sample_game]
                    logger.info(f"Sample: {sample_game}")
                    logger.info(f"    Moneyline: {sample_lines.get('moneyline', 'N/A')}")
                    logger.info(f"    Total: {sample_lines.get('total_runs', {}).get('line', 'N/A')}")
                    
                    return True
                    
        logger.error("VALIDATION: No valid betting lines file found")
        return False
        
    except Exception as e:
        logger.error(f"VALIDATION: Error checking betting lines: {e}")
        return False

def main():
    """Main automation function"""
    logger = setup_logging()
    
    logger.info("STARTING DAILY BETTING LINES AUTOMATION")
    logger.info("=" * 60)
    logger.info(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"Working Directory: {os.getcwd()}")
    
    today = datetime.now().strftime('%Y-%m-%d')
    success_count = 0
    total_steps = 3
    
    try:
        # Step 1: Fetch fresh betting lines from OddsAPI
        repo_root = os.path.dirname(__file__)
        fetch_script = os.path.join(repo_root, 'fetch_odds_api.py')
        if run_command(
            [sys.executable, fetch_script, today],
            "Fetching fresh betting lines from OddsAPI",
            logger
        ):
            success_count += 1
        
        # Step 2: Convert betting lines to Flask format
        convert_script = os.path.join(repo_root, 'convert_betting_lines.py')
        if run_command(
            [sys.executable, convert_script],
            "Converting betting lines to Flask format",
            logger
        ):
            success_count += 1
            
        # Step 3: Validate the results
        if validate_betting_lines(logger):
            success_count += 1
            
        # Report results
        logger.info("=" * 60)
        logger.info(f"AUTOMATION COMPLETE: {success_count}/{total_steps} steps successful")
        
        if success_count == total_steps:
            logger.info("SUCCESS: Real betting lines updated successfully!")
            logger.info("NO FAKE DATA: All betting recommendations will use real market odds")
            return True
        else:
            logger.error(f"PARTIAL SUCCESS: Only {success_count}/{total_steps} steps completed")
            return False
            
    except Exception as e:
        logger.error(f"CRITICAL ERROR: {e}")
        logger.error(traceback.format_exc())
        return False

def fetch_fresh_betting_lines():
    """
    API function to fetch fresh betting lines and return result for Flask app
    
    Returns:
        dict: Result with 'success' and 'games_count' keys
    """
    try:
        logger = setup_logging()
        logger.info("🔄 API call: Fetching fresh betting lines...")
        
        # For now, validate existing betting lines since we don't have OddsAPI integration
        # In a real implementation, this would fetch from OddsAPI
        
        # Check if we have current betting lines
        games_count = 0
        today = datetime.now().strftime('%Y_%m_%d')
        data_dir = os.path.join(os.path.dirname(__file__), 'data')
        lines_file = os.path.join(data_dir, f'real_betting_lines_{today}.json')
        
        if os.path.exists(lines_file):
            try:
                with open(lines_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    lines = data.get('lines', {})
                    games_count = len(lines)
                    logger.info(f"✅ Current betting lines file contains {games_count} games")
                    
                    return {
                        'success': True,
                        'games_count': games_count,
                        'message': f'Using existing betting lines with {games_count} games',
                        'timestamp': datetime.now().isoformat()
                    }
            except Exception as e:
                logger.error(f"Error reading betting lines file: {e}")
        
        # If no current file, check for alternative formats
        alt_today = datetime.now().strftime('%Y-%m-%d')
        alt_lines_file = os.path.join(data_dir, f'real_betting_lines_{alt_today}.json')
        
        if os.path.exists(alt_lines_file):
            try:
                with open(alt_lines_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    lines = data.get('lines', {})
                    games_count = len(lines)
                    logger.info(f"✅ Found alternative betting lines file with {games_count} games")
                    
                    return {
                        'success': True,
                        'games_count': games_count,
                        'message': f'Using existing betting lines with {games_count} games',
                        'timestamp': datetime.now().isoformat()
                    }
            except Exception as e:
                logger.error(f"Error reading alternative betting lines file: {e}")
        
        # No betting lines found
        logger.warning("No current betting lines file found")
        return {
            'success': False,
            'error': 'No current betting lines available - OddsAPI integration needed',
            'games_count': 0,
            'timestamp': datetime.now().isoformat()
        }
            
    except Exception as e:
        logger.error(f"Error in fetch_fresh_betting_lines: {e}")
        return {
            'success': False,
            'error': str(e),
            'games_count': 0,
            'timestamp': datetime.now().isoformat()
        }

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
