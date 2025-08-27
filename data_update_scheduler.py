#!/usr/bin/env python3
"""
Master Data Update Scheduler
Orchestrates dai        "daily_updates": {
            "enabled": True,
            "pitcher_stats": True,
            "weather_park_factors": True,
            "bullpen_factors": True
        },d weekly data updates based on schedule
"""

import os
import sys
import subprocess
import logging
import json
from datetime import datetime, timedelta
from pathlib import Path

def setup_logging():
    """Setup logging for the scheduler"""
    today = datetime.now().strftime('%Y%m%d_%H%M%S')
    log_file = f"data_update_scheduler_{today}.log"
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler()
        ]
    )
    
    return logging.getLogger(__name__)

def run_script(script_path: Path, description: str, logger, timeout: int = 300):
    """Run a script with error handling"""
    try:
        logger.info(f"🚀 {description}")
        
        if not script_path.exists():
            logger.error(f"❌ Script not found: {script_path}")
            return False

        result = subprocess.run([
            sys.executable, str(script_path)
        ], capture_output=True, text=True, timeout=timeout, cwd=str(script_path.parent))
        
        if result.returncode == 0:
            logger.info(f"✅ SUCCESS: {description}")
            if result.stdout and len(result.stdout.strip()) > 0:
                # Log only first few lines to avoid spam
                output_lines = result.stdout.strip().split('\n')
                for line in output_lines[:10]:
                    if line.strip():
                        logger.info(f"   {line}")
                if len(output_lines) > 10:
                    logger.info(f"   ... and {len(output_lines) - 10} more lines")
            return True
        else:
            logger.error(f"❌ FAILED: {description}")
            if result.stderr:
                error_lines = result.stderr.strip().split('\n')
                for line in error_lines[:5]:
                    if line.strip():
                        logger.error(f"   Error: {line}")
            return False
            
    except subprocess.TimeoutExpired:
        logger.error(f"⏰ TIMEOUT: {description} (>{timeout}s)")
        return False
    except Exception as e:
        logger.error(f"💥 EXCEPTION: {description} - {str(e)}")
        return False

def load_schedule_config():
    """Load or create update schedule configuration"""
    config_file = Path("data") / "update_schedule_config.json"
    
    default_config = {
        "daily_updates": {
            "enabled": True,
            "pitcher_stats": True,
            "bullpen_stats": True
        },
        "weekly_updates": {
            "enabled": True,
            "team_strength": True,
            "day_of_week": 1,  # Monday = 0, Sunday = 6
            "full_data_update": False
        },
        "comprehensive_updates": {
            "enabled": True,
            "day_of_week": 0,  # Monday
            "frequency_weeks": 2  # Every 2 weeks
        },
        "last_updates": {
            "daily": None,
            "weekly": None,
            "comprehensive": None
        }
    }
    
    try:
        if config_file.exists():
            with open(config_file, 'r') as f:
                config = json.load(f)
                # Merge with defaults for any missing keys
                for key, value in default_config.items():
                    if key not in config:
                        config[key] = value
                return config
        else:
            config_file.parent.mkdir(exist_ok=True)
            with open(config_file, 'w') as f:
                json.dump(default_config, f, indent=2)
            return default_config
    except Exception:
        return default_config

def save_schedule_config(config):
    """Save update schedule configuration"""
    config_file = Path("data") / "update_schedule_config.json"
    try:
        config_file.parent.mkdir(exist_ok=True)
        with open(config_file, 'w') as f:
            json.dump(config, f, indent=2)
    except Exception as e:
        logging.getLogger(__name__).error(f"❌ Error saving config: {e}")

def should_run_daily_update(config, logger):
    """Check if daily update should run"""
    if not config.get('daily_updates', {}).get('enabled', True):
        return False
    
    last_daily = config.get('last_updates', {}).get('daily')
    today = datetime.now().strftime('%Y-%m-%d')
    
    if last_daily != today:
        logger.info(f"📅 Daily update needed (last: {last_daily}, today: {today})")
        return True
    
    logger.info("✅ Daily update already completed today")
    return False

def should_run_weekly_update(config, logger):
    """Check if weekly update should run"""
    if not config.get('weekly_updates', {}).get('enabled', True):
        return False
    
    target_day = config.get('weekly_updates', {}).get('day_of_week', 1)  # Default Monday
    current_day = datetime.now().weekday()
    
    last_weekly = config.get('last_updates', {}).get('weekly')
    today = datetime.now().strftime('%Y-%m-%d')
    
    # Check if it's the right day and we haven't run this week
    if current_day == target_day:
        if not last_weekly:
            logger.info("📅 Weekly update needed (never run)")
            return True
        
        last_date = datetime.strptime(last_weekly, '%Y-%m-%d')
        days_since = (datetime.now() - last_date).days
        
        if days_since >= 7:
            logger.info(f"📅 Weekly update needed (last: {last_weekly}, {days_since} days ago)")
            return True
    
    logger.info(f"✅ Weekly update not needed (target day: {target_day}, current: {current_day})")
    return False

def should_run_comprehensive_update(config, logger):
    """Check if comprehensive update should run"""
    if not config.get('comprehensive_updates', {}).get('enabled', True):
        return False
    
    target_day = config.get('comprehensive_updates', {}).get('day_of_week', 0)  # Default Monday
    frequency_weeks = config.get('comprehensive_updates', {}).get('frequency_weeks', 2)
    current_day = datetime.now().weekday()
    
    last_comprehensive = config.get('last_updates', {}).get('comprehensive')
    
    # Check if it's the right day
    if current_day == target_day:
        if not last_comprehensive:
            logger.info("📅 Comprehensive update needed (never run)")
            return True
        
        last_date = datetime.strptime(last_comprehensive, '%Y-%m-%d')
        days_since = (datetime.now() - last_date).days
        
        if days_since >= (frequency_weeks * 7):
            logger.info(f"📅 Comprehensive update needed (last: {last_comprehensive}, {days_since} days ago)")
            return True
    
    logger.info(f"✅ Comprehensive update not needed")
    return False

def run_data_updates():
    """Main function to run scheduled data updates"""
    logger = setup_logging()
    
    logger.info("=" * 80)
    logger.info("📊 MLB DATA UPDATE SCHEDULER STARTING")
    logger.info(f"📅 Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"📅 Day of Week: {datetime.now().strftime('%A')} ({datetime.now().weekday()})")
    logger.info("=" * 80)
    
    # Load configuration
    config = load_schedule_config()
    base_dir = Path(__file__).parent
    
    # Results tracking
    results = {
        'daily': None,
        'weekly': None,
        'comprehensive': None
    }
    
    # Check and run daily updates
    if should_run_daily_update(config, logger):
        logger.info("\n🎯 RUNNING DAILY UPDATES")
        
        daily_success = True
        
        # Fast pitcher updates
        if config.get('daily_updates', {}).get('pitcher_stats', True):
            pitcher_script = base_dir / "fast_pitcher_updater.py"
            if pitcher_script.exists():
                success = run_script(pitcher_script, "Daily Pitcher Stats Update", logger, 300)
                daily_success = daily_success and success
            else:
                logger.warning("⚠️ Fast pitcher updater not found")
                daily_success = False
        
        # Weather and park factors update
        if config.get('daily_updates', {}).get('weather_park_factors', True):
            weather_script = base_dir / "weather_park_integration.py"
            if weather_script.exists():
                success = run_script(weather_script, "Daily Weather and Park Factors Update", logger, 300)
                daily_success = daily_success and success
            else:
                logger.warning("⚠️ Weather and park factors updater not found")
                daily_success = False
        
        # Update last daily run
        if daily_success:
            config['last_updates']['daily'] = datetime.now().strftime('%Y-%m-%d')
            logger.info("✅ Daily updates completed successfully")
        else:
            logger.error("❌ Daily updates failed")
        
        results['daily'] = daily_success
    
    # Check and run weekly updates
    if should_run_weekly_update(config, logger):
        logger.info("\n🎯 RUNNING WEEKLY UPDATES")
        
        weekly_success = True
        
        # Team strength updates
        if config.get('weekly_updates', {}).get('team_strength', True):
            team_script = base_dir / "weekly_team_updater.py"
            if team_script.exists():
                success = run_script(team_script, "Weekly Team Strength Update", logger, 600)
                weekly_success = weekly_success and success
            else:
                logger.warning("⚠️ Weekly team updater not found")
                weekly_success = False
        
        # Update last weekly run
        if weekly_success:
            config['last_updates']['weekly'] = datetime.now().strftime('%Y-%m-%d')
            logger.info("✅ Weekly updates completed successfully")
        else:
            logger.error("❌ Weekly updates failed")
        
        results['weekly'] = weekly_success
    
    # Check and run comprehensive updates
    if should_run_comprehensive_update(config, logger):
        logger.info("\n🎯 RUNNING COMPREHENSIVE UPDATES")
        
        comprehensive_success = True
        
        # Full data update
        comprehensive_script = base_dir / "daily_data_updater.py"
        if comprehensive_script.exists():
            success = run_script(comprehensive_script, "Comprehensive Data Update", logger, 1200)
            comprehensive_success = comprehensive_success and success
        else:
            logger.warning("⚠️ Comprehensive data updater not found")
            comprehensive_success = False
        
        # Update last comprehensive run
        if comprehensive_success:
            config['last_updates']['comprehensive'] = datetime.now().strftime('%Y-%m-%d')
            logger.info("✅ Comprehensive updates completed successfully")
        else:
            logger.error("❌ Comprehensive updates failed")
        
        results['comprehensive'] = comprehensive_success
    
    # Save updated configuration
    save_schedule_config(config)
    
    # Summary
    logger.info("\n" + "=" * 80)
    logger.info("📋 UPDATE SUMMARY")
    
    for update_type, result in results.items():
        if result is None:
            logger.info(f"   ⏭️  {update_type.title()}: Skipped (not scheduled)")
        elif result:
            logger.info(f"   ✅ {update_type.title()}: Success")
        else:
            logger.info(f"   ❌ {update_type.title()}: Failed")
    
    total_attempted = sum(1 for r in results.values() if r is not None)
    total_successful = sum(1 for r in results.values() if r is True)
    
    logger.info(f"📊 Overall: {total_successful}/{total_attempted} successful")
    logger.info("=" * 80)
    
    return results

if __name__ == "__main__":
    run_data_updates()
