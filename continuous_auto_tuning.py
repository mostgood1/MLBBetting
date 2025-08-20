"""
MLB Auto-Tuning Background Process
Runs continuously, optimizing every few hours based on real game results
"""

import time
import logging
import schedule
import signal
import sys
import os
from datetime import datetime
from real_game_performance_tracker import performance_tracker

class ContinuousAutoTuner:
    """Runs auto-tuning continuously in the background"""
    
    def __init__(self):
        self.running = True
        self.setup_logging()
        self.logger = logging.getLogger(__name__)
        
        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
        
    def setup_logging(self):
        """Setup logging for continuous operation"""
        log_file = os.path.join('data', 'continuous_auto_tuning.log')
        
        # Create data directory if it doesn't exist
        os.makedirs('data', exist_ok=True)
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler()
            ]
        )
    
    def signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully"""
        self.logger.info(f"SHUTDOWN: Received signal {signum}, shutting down gracefully...")
        self.running = False
    
    def quick_optimization_check(self):
        """Quick optimization check without full analysis"""
        try:
            self.logger.info("QUICK-CHECK: Performing optimization check...")
            
            # Analyze last 3 days for quick feedback
            performance = performance_tracker.analyze_recent_performance(3)
            
            if performance:
                winner_acc = performance.get('winner_accuracy', 0)
                total_acc = performance.get('total_accuracy', 0)
                games = performance.get('games_analyzed', 0)
                
                self.logger.info(f"PERFORMANCE: {games} games - Winner: {winner_acc:.1%}, Total: {total_acc:.1%}")
                
                # Only suggest optimization if we have enough data and performance is concerning
                if games >= 5:
                    if winner_acc < 0.48 or total_acc < 0.38:  # Performance declining
                        self.logger.info("TRIGGER: Performance declining, running full optimization...")
                        return self.full_optimization()
                    elif winner_acc > 0.57 and total_acc > 0.47:  # Performance excellent
                        self.logger.info("STATUS: Performance excellent, no optimization needed")
                    else:
                        self.logger.info("STATUS: Performance stable, no changes needed")
                else:
                    self.logger.info("STATUS: Not enough recent games for optimization")
            else:
                self.logger.warning("WARNING: No performance data available")
                
            return True
            
        except Exception as e:
            self.logger.error(f"ERROR: Quick check failed: {e}")
            return False
    
    def full_optimization(self):
        """Run full optimization analysis"""
        try:
            self.logger.info("FULL-OPT: Running full optimization analysis...")
            
            # Analyze last 7 days for full optimization
            suggestions = performance_tracker.suggest_parameter_adjustments(7)
            
            if 'error' in suggestions:
                self.logger.error(f"ERROR: {suggestions['error']}")
                return False
            
            adjustments = suggestions.get('parameter_adjustments', {})
            confidence = suggestions.get('confidence_level', 'LOW')
            
            if not adjustments:
                self.logger.info("SUCCESS: No adjustments needed - performance optimal")
                return True
            
            self.logger.info(f"SUGGESTIONS: Found {len(adjustments)} parameter adjustments ({confidence} confidence)")
            
            # Auto-apply HIGH confidence suggestions
            if confidence == 'HIGH':
                self.logger.info("APPLY: Applying HIGH confidence optimizations...")
                result = performance_tracker.apply_parameter_adjustments(adjustments)
                
                if result['success']:
                    self.logger.info("SUCCESS: Optimization applied successfully")
                    for param, value in adjustments.items():
                        self.logger.info(f"CHANGED: {param} -> {value}")
                    return True
                else:
                    self.logger.error(f"ERROR: Optimization failed: {result['error']}")
                    return False
            else:
                self.logger.info(f"SKIP: Confidence {confidence} too low for auto-apply (need HIGH)")
                return True
                
        except Exception as e:
            self.logger.error(f"ERROR: Full optimization failed: {e}")
            return False
    
    def daily_full_optimization(self):
        """Scheduled daily full optimization"""
        self.logger.info("DAILY: Running scheduled daily optimization...")
        return self.full_optimization()
    
    def run_continuously(self):
        """Main continuous loop"""
        self.logger.info("STARTUP: Continuous auto-tuning started")
        self.logger.info("SCHEDULE: Setting up optimization schedule...")
        
        # Schedule optimizations
        schedule.every().day.at("06:00").do(self.daily_full_optimization)  # Daily full optimization
        schedule.every(4).hours.do(self.quick_optimization_check)          # Quick checks every 4 hours
        schedule.every().day.at("23:30").do(self.quick_optimization_check) # End of day check
        
        self.logger.info("SCHEDULE: Configured:")
        self.logger.info("  - 06:00: Daily full optimization")
        self.logger.info("  - Every 4 hours: Quick performance check")
        self.logger.info("  - 23:30: End-of-day check")
        
        # Run initial check
        self.logger.info("INITIAL: Running startup optimization check...")
        self.quick_optimization_check()
        
        # Main loop
        self.logger.info("RUNNING: Continuous optimization active (Ctrl+C to stop)")
        
        try:
            while self.running:
                schedule.run_pending()
                time.sleep(60)  # Check every minute
                
        except KeyboardInterrupt:
            self.logger.info("SHUTDOWN: Interrupted by user")
        except Exception as e:
            self.logger.error(f"ERROR: Unexpected error: {e}")
        finally:
            self.logger.info("SHUTDOWN: Continuous auto-tuning stopped")

def main():
    """Main entry point"""
    tuner = ContinuousAutoTuner()
    tuner.run_continuously()

if __name__ == "__main__":
    main()
