#!/usr/bin/env python3
"""
Complete Daily MLB Refresh System
Fixed workflow with proper dependencies and Athletics normalization
"""

import os
import sys
import subprocess
import logging
import shutil
import json
from datetime import datetime
from pathlib import Path

def setup_logging():
    """Setup logging for the automation"""
    today = datetime.now().strftime('%Y%m%d_%H%M%S')
    log_file = f"complete_daily_refresh_{today}.log"
    
    # Create safe stream handler for Windows encoding issues
    class SafeStreamHandler(logging.StreamHandler):
        def emit(self, record):
            try:
                msg = self.format(record)
                # Convert any problematic characters
                msg = msg.encode('ascii', errors='replace').decode('ascii')
                self.stream.write(msg + self.terminator)
                self.flush()
            except Exception:
                self.handleError(record)

    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    stream_handler = SafeStreamHandler()
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[file_handler, stream_handler]
    )
    
    return logging.getLogger(__name__)

def run_script(script_path: Path, description: str, logger, timeout: int = 300):
    """Run a script with error handling"""
    try:
        logger.info(f"Running: {description}")
        if not script_path.exists():
            logger.warning(f"Script not found, skipping: {script_path}")
            return False

        result = subprocess.run([
            sys.executable, str(script_path)
        ], capture_output=True, text=True, timeout=timeout, cwd=str(script_path.parent))
        
        if result.returncode == 0:
            logger.info(f"SUCCESS: {description}")
            if result.stdout:
                # Clean output for logging
                clean_output = result.stdout.encode('ascii', errors='replace').decode('ascii')
                logger.info(f"Output: {clean_output.strip()}")
            return True
        else:
            logger.error(f"FAILED: {description}")
            if result.stderr:
                clean_error = result.stderr.encode('ascii', errors='replace').decode('ascii')
                logger.error(f"Error: {clean_error}")
            return False
            
    except subprocess.TimeoutExpired:
        logger.error(f"TIMEOUT: {description} (>{timeout}s)")
        return False
    except Exception as e:
        logger.error(f"EXCEPTION: {description} - {str(e)}")
        return False

def normalize_athletics_references():
    """Ensure Athletics team name is consistent across all data files"""
    logger = logging.getLogger(__name__)
    logger.info("Normalizing Athletics team references...")
    
    base_dir = Path(__file__).parent
    data_dir = base_dir / "data"
    
    # Files that might contain team references
    files_to_check = []
    
    # Add all JSON files in data directory
    if data_dir.exists():
        for json_file in data_dir.glob("*.json"):
            files_to_check.append(json_file)
    
    # Also check specific config files
    config_files = [
        base_dir / "team_strength_factors.json",
        base_dir / "bullpen_factors.json", 
        base_dir / "park_factors.json"
    ]
    
    for config_file in config_files:
        if config_file.exists():
            files_to_check.append(config_file)
    
    normalized_count = 0
    
    for file_path in files_to_check:
        if file_path.exists():
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Replace various Athletics references
                modified = False
                original_content = content
                
                # Common Athletics variations to normalize to "Athletics"
                replacements = [
                    ('"Oakland Athletics"', '"Athletics"'),
                    ('"Oakland A\'s"', '"Athletics"'),
                    ('"A\'s"', '"Athletics"'),
                    ('Oakland Athletics_vs_', 'Athletics_vs_'),
                    ('_vs_Oakland Athletics', '_vs_Athletics'),
                    ('Oakland Athletics @', 'Athletics @'),
                    ('@ Oakland Athletics', '@ Athletics'),
                    ('Oakland Athletics:', 'Athletics:'),
                ]
                
                for old_pattern, new_pattern in replacements:
                    if old_pattern in content:
                        content = content.replace(old_pattern, new_pattern)
                        modified = True
                
                if modified:
                    # Validate JSON format if it's a JSON file
                    if file_path.suffix == '.json':
                        try:
                            json.loads(content)  # Test if valid JSON
                        except json.JSONDecodeError:
                            logger.warning(f"Invalid JSON after normalization in {file_path.name}, skipping")
                            continue
                    
                    # Save the normalized content
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(content)
                    logger.info(f"Normalized Athletics references in {file_path.name}")
                    normalized_count += 1
                    
            except Exception as e:
                logger.warning(f"Could not normalize {file_path.name}: {e}")
    
    logger.info(f"Athletics normalization complete: {normalized_count} files updated")
    return True

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
    """Run the complete daily refresh workflow in correct order"""
    logger = setup_logging()
    today = datetime.now().strftime('%Y-%m-%d')
    today_underscore = today.replace('-', '_')
    
    logger.info("=" * 80)
    logger.info("COMPLETE DAILY MLB REFRESH STARTING")
    logger.info(f"Date: {today}")
    logger.info("=" * 80)
    
    base_dir = Path(__file__).parent
    data_dir = base_dir / "data"
    
    # Ensure data directory exists
    data_dir.mkdir(exist_ok=True)
    
    success_count = 0
    total_steps = 8
    
    # Step 1: Normalize Athletics team references first
    logger.info("\nSTEP 1: Normalizing Team References")
    if normalize_athletics_references():
        success_count += 1
        logger.info("SUCCESS: Athletics normalization")
    else:
        logger.warning("WARNING: Athletics normalization had issues")
    
    # Step 2: Fetch today's games
    logger.info("\nSTEP 2: Fetching Today's Games")
    games_script = base_dir / "fetch_today_games.py"
    if run_script(games_script, "Fetch Today's Games", logger, 300):
        success_count += 1
    
    # Step 3: Update team strength factors
    logger.info("\nSTEP 3: Updating Team Strength Factors")
    team_script = base_dir / "weekly_team_updater.py"
    if run_script(team_script, "Update Team Strength Factors", logger, 600):
        success_count += 1
    
    # Step 4: Update bullpen factors
    logger.info("\nSTEP 4: Updating Bullpen Factors")
    bullpen_script = base_dir / "bullpen_factor_system.py"
    if run_script(bullpen_script, "Update Bullpen Factors", logger, 600):
        success_count += 1
    
    # Step 5: Update weather and park factors (CRITICAL - before predictions)
    logger.info("\nSTEP 5: Updating Weather and Park Factors")
    weather_script = base_dir / "weather_park_integration.py"
    if run_script(weather_script, "Update Weather and Park Factors", logger, 300):
        success_count += 1
        logger.info("CRITICAL: Weather data updated successfully")
    else:
        logger.error("CRITICAL: Weather update failed - predictions may be inaccurate")
    
    # Step 6: Fetch real betting lines (CRITICAL - before predictions)
    logger.info("\nSTEP 6: Fetching Real Betting Lines")
    lines_script = base_dir / "fetch_betting_lines_real.py"
    if run_script(lines_script, "Fetch Real Betting Lines", logger, 600):
        success_count += 1
        logger.info("CRITICAL: Betting lines fetched successfully")
    else:
        logger.warning("WARNING: No real betting lines - using predictions only")
    
    # Step 7: Generate predictions (depends on weather and team data)
    logger.info("\nSTEP 7: Generating Daily Predictions")
    predictions_script = base_dir / "daily_ultrafastengine_predictions.py"
    if run_script(predictions_script, "Generate Daily Predictions", logger, 900):
        success_count += 1
        logger.info("SUCCESS: Daily predictions generated")
    else:
        logger.error("CRITICAL: Prediction generation failed")
    
    # Step 8: Generate betting recommendations (depends on predictions and lines)
    logger.info("\nSTEP 8: Generating Betting Recommendations")
    betting_script = base_dir / "betting_recommendations_engine.py"
    if run_script(betting_script, "Generate Betting Recommendations", logger, 300):
        success_count += 1
        logger.info("SUCCESS: Betting recommendations generated")
    else:
        logger.error("CRITICAL: Betting recommendations failed")
    
    # Final verification
    logger.info("\n" + "=" * 80)
    logger.info("DAILY REFRESH SUMMARY")
    logger.info("=" * 80)
    
    # Check critical files
    critical_files = [
        (data_dir / f"games_{today}.json", "Today's Games"),
        (data_dir / f"park_weather_factors_{today_underscore}.json", "Weather Data"),
        (data_dir / "unified_predictions_cache.json", "Predictions Cache"),
        (data_dir / f"betting_recommendations_{today_underscore}.json", "Betting Recommendations")
    ]
    
    files_ok = 0
    for file_path, description in critical_files:
        if file_path.exists():
            logger.info(f"VERIFIED: {description} - {file_path.name}")
            files_ok += 1
        else:
            logger.error(f"MISSING: {description} - {file_path.name}")
    
    # Optional files
    optional_files = [
        (data_dir / f"real_betting_lines_{today_underscore}.json", "Real Betting Lines")
    ]
    
    for file_path, description in optional_files:
        if file_path.exists():
            logger.info(f"AVAILABLE: {description} - {file_path.name}")
        else:
            logger.warning(f"OPTIONAL: {description} - Not available (using predictions only)")
    
    logger.info(f"\nSteps completed: {success_count}/{total_steps}")
    logger.info(f"Critical files: {files_ok}/{len(critical_files)}")
    
    if success_count >= 6 and files_ok >= 3:  # Allow some flexibility
        logger.info("\nSUCCESS: Daily refresh completed successfully!")
        logger.info(f"System ready for MLB betting analysis on {today}")
        return True
    else:
        logger.error("\nFAILED: Critical steps missing - manual intervention needed")
        return False

if __name__ == "__main__":
    success = complete_daily_automation()
    sys.exit(0 if success else 1)
