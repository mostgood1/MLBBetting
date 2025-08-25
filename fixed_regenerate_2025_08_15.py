#!/usr/bin/env python3
"""
Fixed regeneration script that properly sets the date in unified betting engine
"""

import os
import sys
import json
from datetime import datetime

# Add the current directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import the unified betting engine
from unified_betting_engine import UnifiedBettingEngine

def regenerate_for_date(target_date):
    """Regenerate betting recommendations for a specific historical date"""
    print(f"🎯 Regenerating betting recommendations for {target_date}")
    
    # Create a custom engine instance with the target date
    class HistoricalBettingEngine(UnifiedBettingEngine):
        def __init__(self, historical_date):
            # Override the date before calling parent constructor
            self.historical_date = historical_date
            super().__init__()
            
        def __init_paths(self):
            """Override path initialization to use historical date"""
            self.current_date = self.historical_date
            self.root_dir = os.path.dirname(os.path.abspath(__file__))
            
            # Set up file paths for historical date
            date_underscore = self.current_date.replace('-', '_')
            self.predictions_cache_path = os.path.join(self.root_dir, 'data', 'unified_predictions_cache.json')
            self.betting_lines_path = os.path.join(self.root_dir, 'data', f'real_betting_lines_{date_underscore}.json')
            self.output_path = os.path.join(self.root_dir, 'data', f'betting_recommendations_{date_underscore}.json')
            
            print(f"📊 Using predictions: {self.predictions_cache_path}")
            print(f"💰 Using betting lines: {self.betting_lines_path}")
            print(f"📁 Output file: {self.output_path}")
    
    # Override the __init__ method properly
    def custom_init(self, historical_date):
        self.historical_date = historical_date
        self.current_date = historical_date
        self.root_dir = os.path.dirname(os.path.abspath(__file__))
        
        # Set up file paths for historical date
        date_underscore = self.current_date.replace('-', '_')
        self.predictions_cache_path = os.path.join(self.root_dir, 'data', 'unified_predictions_cache.json')
        self.betting_lines_path = os.path.join(self.root_dir, 'data', f'real_betting_lines_{date_underscore}.json')
        self.output_path = os.path.join(self.root_dir, 'data', f'betting_recommendations_{date_underscore}.json')
        
        print(f"📊 Using predictions: {self.predictions_cache_path}")
        print(f"💰 Using betting lines: {self.betting_lines_path}")
        print(f"📁 Output file: {self.output_path}")
        
        # Initialize logger
        import logging
        logging.basicConfig(level=logging.INFO)
        
        # Load predictions and betting lines
        self.predictions = self.load_predictions()
        self.betting_lines = self.load_betting_lines()
    
    # Monkey patch the initialization
    UnifiedBettingEngine.__init__ = custom_init
    
    try:
        # Create engine instance for the historical date
        engine = UnifiedBettingEngine(target_date)
        
        # Generate recommendations
        recommendations = engine.generate_recommendations()
        
        print(f"✅ Generated {len(recommendations)} recommendations for {target_date}")
        
        # Save to file
        engine.save_recommendations(recommendations)
        
        return True
        
    except Exception as e:
        print(f"❌ Error regenerating for {target_date}: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    target_date = "2025-08-15"
    success = regenerate_for_date(target_date)
    if success:
        print(f"🎉 Successfully regenerated betting recommendations for {target_date}")
    else:
        print(f"💥 Failed to regenerate betting recommendations for {target_date}")
