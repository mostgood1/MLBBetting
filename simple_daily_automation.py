#!/usr/bin/env python3
"""
Simple Daily MLB Automation
Lightweight script that can be run as a Windows scheduled task
"""

import os
import sys
import subprocess
import logging
from datetime import datetime
from pathlib import Path

def setup_simple_logging():
    """Setup simple logging for daily automation"""
    today = datetime.now().strftime('%Y%m%d_%H%M%S')
    log_file = f"simple_daily_automation_{today}.log"
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler()
        ]
    )
    
    return logging.getLogger(__name__)

def run_script_simple(script_path, description, logger, timeout=600):
    """Simple script runner with minimal error handling"""
    try:
        logger.info(f"🚀 {description}")
        
        if not script_path.exists():
            logger.error(f"❌ Script not found: {script_path}")
            return False

        result = subprocess.run([
            sys.executable, str(script_path)
        ], capture_output=True, text=True, timeout=timeout)
        
        if result.returncode == 0:
            logger.info(f"✅ {description} - SUCCESS")
            return True
        else:
            logger.error(f"❌ {description} - FAILED")
            if result.stderr:
                logger.error(f"   Error: {result.stderr[:200]}")
            return False
            
    except subprocess.TimeoutExpired:
        logger.error(f"⏰ {description} - TIMEOUT")
        return False
    except Exception as e:
        logger.error(f"💥 {description} - ERROR: {str(e)}")
        return False

def simple_daily_automation():
    """Run simple daily automation"""
    logger = setup_simple_logging()
    
    logger.info("🏆 SIMPLE DAILY MLB AUTOMATION")
    logger.info(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    base_dir = Path(__file__).parent
    success_count = 0
    total_steps = 0
    
    # Step 1: Data Updates
    logger.info("\n📊 Data Updates")
    scheduler_script = base_dir / "data_update_scheduler.py"
    if scheduler_script.exists():
        total_steps += 1
        if run_script_simple(scheduler_script, "Data Updates", logger, 1800):
            success_count += 1
    
    # Step 2: Games & Pitchers
    logger.info("\n🎯 Games & Pitchers")
    games_script = base_dir / "fetch_today_games.py"
    if games_script.exists():
        total_steps += 1
        if run_script_simple(games_script, "Today's Games", logger, 300):
            success_count += 1
    
    pitchers_script = base_dir / "fetch_todays_starters.py"
    if pitchers_script.exists():
        total_steps += 1
        if run_script_simple(pitchers_script, "Starting Pitchers", logger, 300):
            success_count += 1
    
    # Step 3: Betting Lines
    logger.info("\n💰 Betting Lines")
    lines_script = base_dir / "daily_betting_lines_automation.py"
    if lines_script.exists():
        total_steps += 1
        if run_script_simple(lines_script, "Betting Lines", logger, 600):
            success_count += 1
    
    # Step 4: Predictions
    logger.info("\n🔮 Predictions")
    predictions_script = base_dir / "daily_ultrafastengine_predictions.py"
    if predictions_script.exists():
        total_steps += 1
        if run_script_simple(predictions_script, "Game Predictions", logger, 900):
            success_count += 1
    
    # Step 5: Recommendations
    logger.info("\n🎲 Betting Recommendations")
    betting_script = base_dir / "betting_recommendations_engine.py"
    if betting_script.exists():
        total_steps += 1
        if run_script_simple(betting_script, "Betting Recommendations", logger, 300):
            success_count += 1
    
    # Summary
    logger.info(f"\n📋 AUTOMATION COMPLETE: {success_count}/{total_steps} successful")
    
    if success_count == total_steps and total_steps > 0:
        logger.info("🎉 All steps completed successfully!")
        return True
    elif success_count > 0:
        logger.info(f"⚠️ Partial success ({success_count}/{total_steps})")
        return True
    else:
        logger.error("❌ Automation failed")
        return False

if __name__ == "__main__":
    success = simple_daily_automation()
    sys.exit(0 if success else 1)
