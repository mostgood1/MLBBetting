#!/usr/bin/env python3
"""
Complete Daily Refresh Automation
====================================
This script orchestrates the complete daily automation workflow for the MLB betting system.
It runs all necessary data collection, analysis, and prediction generation in the correct sequence.

CRITICAL TIMING:
- Weather/Park factors MUST be generated BEFORE predictions
- All data collection happens first, then processing, then predictions

Sequence:
1. Data Collection (betting lines, schedules, etc.)
2. Factor Generation (team strength, bullpen stats)
2.5. Weather/Park Factor Generation (BEFORE predictions)
3. Prediction Generation (all engines)
4. Cleanup and validation
"""

import os
import sys
import logging
import traceback
from datetime import datetime, timedelta
import subprocess
import json
import time

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(name)s %(message)s',
    handlers=[
        logging.FileHandler(f'complete_daily_automation_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class CompleteDailyRefresh:
    """Complete daily automation orchestrator"""
    
    def __init__(self):
        self.start_time = datetime.now()
        self.results = {}
        self.errors = []
        
    def log_step(self, step_name, status="STARTING"):
        """Log automation step"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        logger.info(f"[{timestamp}] {status}: {step_name}")
        
    def run_script(self, script_name, description, timeout=300):
        """Run a Python script with error handling"""
        self.log_step(description)
        
        try:
            # Check if script exists
            if not os.path.exists(script_name):
                raise FileNotFoundError(f"Script not found: {script_name}")
            
            # Run the script
            result = subprocess.run(
                [sys.executable, script_name],
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=os.path.dirname(os.path.abspath(__file__))
            )
            
            if result.returncode == 0:
                self.log_step(description, "SUCCESS")
                self.results[script_name] = {"status": "success", "output": result.stdout}
                return True
            else:
                error_msg = f"Script failed with return code {result.returncode}: {result.stderr}"
                logger.error(error_msg)
                self.errors.append(f"{script_name}: {error_msg}")
                self.results[script_name] = {"status": "error", "error": error_msg}
                return False
                
        except subprocess.TimeoutExpired:
            error_msg = f"Script timed out after {timeout} seconds"
            logger.error(error_msg)
            self.errors.append(f"{script_name}: {error_msg}")
            self.results[script_name] = {"status": "timeout", "error": error_msg}
            return False
            
        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            logger.error(error_msg)
            logger.error(traceback.format_exc())
            self.errors.append(f"{script_name}: {error_msg}")
            self.results[script_name] = {"status": "exception", "error": error_msg}
            return False
    
    def step_1_data_collection(self):
        """Step 1: Collect all external data"""
        logger.info("=" * 80)
        logger.info("STEP 1: DATA COLLECTION")
        logger.info("=" * 80)
        
        scripts = [
            ("daily_betting_lines_automation.py", "Fetch daily betting lines"),
            ("fetch_today_games.py", "Fetch today's game schedule"),
            ("fetch_todays_starters.py", "Fetch starting pitcher information"),
        ]
        
        success_count = 0
        for script, description in scripts:
            if self.run_script(script, description):
                success_count += 1
        
        logger.info(f"Step 1 Complete: {success_count}/{len(scripts)} data collection tasks successful")
        return success_count == len(scripts)
    
    def step_2_factor_generation(self):
        """Step 2: Generate team and player factors"""
        logger.info("=" * 80)
        logger.info("STEP 2: FACTOR GENERATION")
        logger.info("=" * 80)
        
        scripts = [
            ("enhanced_mlb_fetcher.py", "Generate team strength factors"),
            ("comprehensive_betting_performance_tracker.py", "Generate bullpen statistics"),
        ]
        
        success_count = 0
        for script, description in scripts:
            if self.run_script(script, description):
                success_count += 1
        
        logger.info(f"Step 2 Complete: {success_count}/{len(scripts)} factor generation tasks successful")
        return success_count == len(scripts)
    
    def step_2_5_weather_park_factors(self):
        """Step 2.5: Generate weather and park factors (CRITICAL: BEFORE predictions)"""
        logger.info("=" * 80)
        logger.info("STEP 2.5: WEATHER & PARK FACTORS (PRE-PREDICTION)")
        logger.info("=" * 80)
        logger.info("🌤️ CRITICAL: Weather/Park factors must be generated BEFORE predictions!")
        
        # Run weather/park integration
        success = self.run_script(
            "weather_park_integration.py", 
            "Generate daily weather and park factors",
            timeout=600  # Allow more time for API calls
        )
        
        if success:
            logger.info("✅ Weather/Park factors generated successfully - Ready for predictions")
        else:
            logger.error("❌ Weather/Park factor generation failed - Predictions may use stale data")
        
        return success
    
    def step_3_predictions(self):
        """Step 3: Generate all predictions"""
        logger.info("=" * 80)
        logger.info("STEP 3: PREDICTION GENERATION")
        logger.info("=" * 80)
        
        scripts = [
            ("daily_ultrafastengine_predictions.py", "Generate Ultra Fast Engine predictions"),
            ("betting_recommendations_engine.py", "Generate betting recommendations"),
        ]
        
        success_count = 0
        for script, description in scripts:
            if self.run_script(script, description, timeout=600):  # Allow more time for predictions
                success_count += 1
        
        logger.info(f"Step 3 Complete: {success_count}/{len(scripts)} prediction tasks successful")
        return success_count == len(scripts)
    
    def step_4_cleanup_validation(self):
        """Step 4: Cleanup and validation"""
        logger.info("=" * 80)
        logger.info("STEP 4: CLEANUP & VALIDATION")
        logger.info("=" * 80)
        
        # Validate critical files exist
        critical_files = [
            "data/unified_predictions_cache.json",
            "data/master_team_strength.json",
            "data/bullpen_stats.json"
        ]
        
        # Check for today's weather/park factors
        today_str = datetime.now().strftime("%Y_%m_%d")
        weather_file = f"data/park_weather_factors_{today_str}.json"
        critical_files.append(weather_file)
        
        validation_results = {}
        for file_path in critical_files:
            if os.path.exists(file_path):
                try:
                    # Try to load JSON files to verify they're valid
                    if file_path.endswith('.json'):
                        with open(file_path, 'r') as f:
                            data = json.load(f)
                            validation_results[file_path] = {
                                "exists": True, 
                                "valid_json": True,
                                "size": len(data) if isinstance(data, (dict, list)) else "unknown"
                            }
                    else:
                        validation_results[file_path] = {"exists": True, "valid_json": "N/A"}
                except Exception as e:
                    validation_results[file_path] = {
                        "exists": True, 
                        "valid_json": False, 
                        "error": str(e)
                    }
            else:
                validation_results[file_path] = {"exists": False}
        
        # Log validation results
        for file_path, result in validation_results.items():
            if result["exists"]:
                if result.get("valid_json", True):
                    logger.info(f"✅ {file_path}: Valid (size: {result.get('size', 'unknown')})")
                else:
                    logger.error(f"❌ {file_path}: Invalid JSON - {result.get('error', 'unknown error')}")
            else:
                logger.error(f"❌ {file_path}: Missing")
        
        return all(result["exists"] for result in validation_results.values())
    
    def generate_summary(self):
        """Generate automation summary"""
        end_time = datetime.now()
        duration = end_time - self.start_time
        
        logger.info("=" * 80)
        logger.info("DAILY AUTOMATION SUMMARY")
        logger.info("=" * 80)
        logger.info(f"Start Time: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info(f"End Time: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info(f"Total Duration: {duration}")
        
        # Count successes and failures
        total_scripts = len(self.results)
        successful_scripts = sum(1 for result in self.results.values() if result["status"] == "success")
        
        logger.info(f"Scripts Executed: {total_scripts}")
        logger.info(f"Successful: {successful_scripts}")
        logger.info(f"Failed: {total_scripts - successful_scripts}")
        
        if self.errors:
            logger.info("\nERRORS:")
            for error in self.errors:
                logger.error(f"  - {error}")
        
        # Overall status
        if not self.errors:
            logger.info("🎉 DAILY AUTOMATION: COMPLETE SUCCESS")
        elif successful_scripts > total_scripts / 2:
            logger.info("⚠️ DAILY AUTOMATION: PARTIAL SUCCESS")
        else:
            logger.info("❌ DAILY AUTOMATION: FAILED")
        
        return {
            "start_time": self.start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "duration_seconds": duration.total_seconds(),
            "total_scripts": total_scripts,
            "successful_scripts": successful_scripts,
            "errors": self.errors,
            "results": self.results
        }
    
    def run_complete_refresh(self):
        """Run the complete daily refresh automation"""
        logger.info("🚀 Starting Complete Daily Refresh Automation")
        logger.info(f"Timestamp: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        
        try:
            # Step 1: Data Collection
            step1_success = self.step_1_data_collection()
            
            # Step 2: Factor Generation  
            step2_success = self.step_2_factor_generation()
            
            # Step 2.5: Weather/Park Factors (CRITICAL: Before predictions)
            step2_5_success = self.step_2_5_weather_park_factors()
            
            # Step 3: Predictions (only if previous steps succeeded)
            if step1_success and step2_success and step2_5_success:
                step3_success = self.step_3_predictions()
            else:
                logger.warning("Skipping predictions due to previous step failures")
                step3_success = False
            
            # Step 4: Cleanup and Validation
            step4_success = self.step_4_cleanup_validation()
            
            # Generate summary
            summary = self.generate_summary()
            
            # Save summary to file
            summary_file = f"automation_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(summary_file, 'w') as f:
                json.dump(summary, f, indent=2)
            
            logger.info(f"Summary saved to: {summary_file}")
            
            return summary
            
        except Exception as e:
            logger.error(f"Critical error in automation: {str(e)}")
            logger.error(traceback.format_exc())
            raise

def main():
    """Main automation entry point"""
    try:
        # Create and run automation
        automation = CompleteDailyRefresh()
        summary = automation.run_complete_refresh()
        
        # Exit with appropriate code
        if summary["successful_scripts"] == summary["total_scripts"]:
            sys.exit(0)  # Complete success
        elif summary["successful_scripts"] > 0:
            sys.exit(1)  # Partial success
        else:
            sys.exit(2)  # Complete failure
            
    except KeyboardInterrupt:
        logger.info("Automation interrupted by user")
        sys.exit(130)
    except Exception as e:
        logger.error(f"Fatal error: {str(e)}")
        sys.exit(3)

if __name__ == "__main__":
    main()
