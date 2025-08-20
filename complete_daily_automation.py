#!/usr/bin/env python3
"""
Complete Daily MLB Automation Trigger
Comprehensive script to set up a new day's data from scratch
"""

import os
import sys
import subprocess
import logging
import shutil
from datetime import datetime
from pathlib import Path

def setup_logging():
    """Setup logging for the automation"""
    today = datetime.now().strftime('%Y%m%d_%H%M%S')
    log_file = f"complete_daily_automation_{today}.log"
    
    # Create UTF-8 safe stream handler to avoid console encoding errors on Windows
    class Utf8StreamHandler(logging.StreamHandler):
        def emit(self, record):
            try:
                msg = self.format(record)
                stream = self.stream
                # Prefer binary write to avoid encoding issues
                try:
                    stream.buffer.write((msg + self.terminator).encode('utf-8', errors='replace'))
                except Exception:
                    # Fallback to text write
                    stream.write(msg + self.terminator)
                self.flush()
            except Exception:
                self.handleError(record)

    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    stream_handler = Utf8StreamHandler()
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[file_handler, stream_handler]
    )
    
    return logging.getLogger(__name__)

def run_script(script_path: Path, description: str, logger, timeout: int = 300):
    """Run a script with error handling"""
    try:
        logger.info(f"🚀 {description}")
        # Ensure script exists before attempting to run
        if not script_path.exists():
            logger.warning(f"⚠️ Script not found, skipping: {script_path}")
            return False

        result = subprocess.run([
            sys.executable, str(script_path)
        ], capture_output=True, text=True, timeout=timeout, cwd=str(script_path.parent))
        
        if result.returncode == 0:
            logger.info(f"✅ SUCCESS: {description}")
            if result.stdout:
                logger.info(f"Output: {result.stdout.strip()}")
            return True
        else:
            logger.error(f"❌ FAILED: {description}")
            logger.error(f"Error: {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        logger.error(f"⏰ TIMEOUT: {description} (>{timeout}s)")
        return False
    except Exception as e:
        logger.error(f"💥 EXCEPTION: {description} - {str(e)}")
        return False

def copy_file_safe(source: Path, target: Path, logger):
    """Safely copy a file with error handling"""
    try:
        if source.exists():
            target.parent.mkdir(parents=True, exist_ok=True)
            try:
                shutil.copy2(source, target)
            except shutil.SameFileError:
                logger.info(f"SKIP: Source and target are the same file: {source}")
                return True
            logger.info(f"📋 Copied {source.name} to {target}")
            return True
        else:
            logger.warning(f"⚠️  Source file not found: {source}")
            return False
    except Exception as e:
        logger.error(f"❌ Error copying {source} to {target}: {e}")
        return False

def complete_daily_automation():
    """Run the complete daily automation workflow"""
    logger = setup_logging()
    today = datetime.now().strftime('%Y-%m-%d')
    today_underscore = today.replace('-', '_')
    
    logger.info("=" * 80)
    logger.info("🏆 COMPLETE DAILY MLB AUTOMATION STARTING")
    logger.info(f"📅 Date: {today}")
    logger.info("=" * 80)
    
    # Base directory setup (repo root)
    base_dir = Path(__file__).parent
    data_dir = base_dir / "data"
    mlb_betting_data_dir = data_dir
    
    # Step 1: Run the enhanced daily automation (try fallbacks)
    logger.info("\n🎯 STEP 1: Running Enhanced Daily Automation")
    enhanced_candidates = [
        base_dir / "daily_enhanced_automation_clean.py",
        base_dir / "daily_betting_lines_automation.py",
        base_dir / "fetch_todays_starters.py"
    ]

    success1 = False
    for candidate in enhanced_candidates:
        if candidate.exists():
            success1 = run_script(candidate, f"Enhanced Daily Automation ({candidate.name})", logger, 600)
            if success1:
                break
        else:
            logger.debug(f"Candidate not found: {candidate}")

    # If none of the candidates were runnable, try importing module functions as a fallback
    if not success1:
        try:
            # Try calling daily_betting_lines_automation.main()
            import importlib
            mod = importlib.import_module('daily_betting_lines_automation')
            if hasattr(mod, 'main'):
                logger.info("🔁 Running daily_betting_lines_automation.main() as fallback")
                success1 = mod.main()
        except Exception as e:
            logger.debug(f"Fallback enhanced automation import failed: {e}")
    
    # Step 2: Generate today's predictions (try fallbacks)
    logger.info("\n🎯 STEP 2: Generating Today's Predictions")
    prediction_candidates = [
        base_dir / "daily_ultrafastengine_predictions.py",
        # No direct equivalent; as best-effort, we can attempt to run a script that triggers engine routines
    ]

    success2 = False
    for candidate in prediction_candidates:
        if candidate.exists():
            success2 = run_script(candidate, f"Generate Today's Predictions ({candidate.name})", logger)
            if success2:
                break
    if not success2:
        logger.info("No prediction script candidate found; relying on existing unified cache if present")
    
    # Step 3: Generate betting recommendations (try fallbacks)
    logger.info("\n🎯 STEP 3: Generating Betting Recommendations")
    betting_candidates = [
        base_dir / "betting_recommendations_engine.py",
        base_dir / "unified_betting_engine.py",
        base_dir / "app_betting_integration.py"
    ]

    success3 = False
    for candidate in betting_candidates:
        if candidate.exists():
            # If unified_betting_engine.py is present, prefer it because it has a main()
            success3 = run_script(candidate, f"Generate Betting Recommendations ({candidate.name})", logger)
            if success3:
                break
        else:
            logger.debug(f"Candidate not found: {candidate}")

    # Fallback: import unified_betting_engine and call main() or generate_recommendations()
    if not success3:
        try:
            import importlib
            ube = importlib.import_module('unified_betting_engine')
            if hasattr(ube, 'main'):
                logger.info("🔁 Running unified_betting_engine.main() as fallback")
                try:
                    ube.main()
                    success3 = True
                except Exception as e:
                    logger.error(f"Unified engine main() failed: {e}")
            else:
                # Try programmatic use
                if hasattr(ube, 'UnifiedBettingEngine'):
                    logger.info("🔁 Running UnifiedBettingEngine.generate_recommendations() as fallback")
                    try:
                        engine = ube.UnifiedBettingEngine()
                        recs = engine.generate_recommendations()
                        if recs and engine.save_recommendations(recs):
                            success3 = True
                    except Exception as e:
                        logger.error(f"Unified engine programmatic run failed: {e}")
        except Exception as e:
            logger.debug(f"Fallback betting recommendations import failed: {e}")
    
    # Step 4: Copy files to correct locations
    logger.info("\n🎯 STEP 4: Copying Files to MLB-Betting Directory")
    
    files_to_copy = [
        (data_dir / "unified_predictions_cache.json", mlb_betting_data_dir / "unified_predictions_cache.json"),
        (data_dir / f"betting_recommendations_{today_underscore}.json", mlb_betting_data_dir / f"betting_recommendations_{today_underscore}.json"),
    ]
    
    copy_success = True
    for source, target in files_to_copy:
        if not copy_file_safe(source, target, logger):
            copy_success = False
    
    # Step 5: Verify data integrity
    logger.info("\n🎯 STEP 5: Verifying Data Integrity")
    
    # Check unified cache
    unified_cache_path = mlb_betting_data_dir / "unified_predictions_cache.json"
    betting_recs_path = mlb_betting_data_dir / f"betting_recommendations_{today_underscore}.json"
    
    cache_ok = unified_cache_path.exists()
    betting_ok = betting_recs_path.exists()
    
    if cache_ok:
        try:
            import json
            with open(unified_cache_path, 'r') as f:
                cache_data = json.load(f)
                dates = list(cache_data.get('predictions_by_date', {}).keys())
                has_today = today in dates
                games_count = len(cache_data.get('predictions_by_date', {}).get(today, {}).get('games', {}))
                
                logger.info(f"✅ Unified cache loaded: {len(dates)} dates, today included: {has_today}, games today: {games_count}")
        except Exception as e:
            logger.error(f"❌ Error reading unified cache: {e}")
            cache_ok = False
    
    if betting_ok:
        try:
            import json
            with open(betting_recs_path, 'r') as f:
                betting_data = json.load(f)
                games_with_betting = len(betting_data.get('games', {}))
                logger.info(f"✅ Betting recommendations loaded: {games_with_betting} games")
        except Exception as e:
            logger.error(f"❌ Error reading betting recommendations: {e}")
            betting_ok = False
    
    # Final summary
    logger.info("\n" + "=" * 80)
    logger.info("📊 AUTOMATION SUMMARY")
    logger.info("=" * 80)
    
    steps = [
        ("Enhanced Daily Automation", success1),
        ("Generate Predictions", success2),
        ("Generate Betting Recommendations", success3),
        ("File Copying", copy_success),
        ("Unified Cache Verification", cache_ok),
        ("Betting Recommendations Verification", betting_ok)
    ]
    
    all_success = True
    for step_name, success in steps:
        status = "✅ PASS" if success else "❌ FAIL"
        logger.info(f"{step_name}: {status}")
        if not success:
            all_success = False
    
    if all_success:
        logger.info("\n🎉 ALL STEPS COMPLETED SUCCESSFULLY!")
        logger.info(f"🎯 Ready for MLB betting analysis on {today}")
        return True
    else:
        logger.warning("\n⚠️  SOME STEPS FAILED - Check logs for details")
        return False

if __name__ == "__main__":
    success = complete_daily_automation()
    sys.exit(0 if success else 1)
