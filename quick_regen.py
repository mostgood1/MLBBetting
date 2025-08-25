#!/usr/bin/env python3
"""
Quick Prediction Regenerator
============================

Simple script to quickly regenerate predictions for a single date.

Usage:
    python quick_regen.py 2025-08-23
    python quick_regen.py  # Uses today's date
"""

import sys
import json
import subprocess
from datetime import datetime
from pathlib import Path

def regenerate_predictions_for_date(date: str) -> bool:
    """Regenerate predictions for a specific date"""
    root_dir = Path(__file__).parent
    
    print(f"🎯 Regenerating predictions for {date}")
    
    try:
        # Step 1: Generate UltraFast predictions
        print("🚀 Running UltraFast predictions...")
        result = subprocess.run([
            sys.executable, "daily_ultrafastengine_predictions.py", "--date", date
        ], cwd=root_dir, capture_output=True, text=True)
        
        if result.returncode != 0:
            print(f"❌ UltraFast predictions failed: {result.stderr}")
            return False
        
        print("✅ UltraFast predictions completed")
        
        # Step 2: Temporarily modify unified betting engine for this date
        engine_path = root_dir / "unified_betting_engine.py"
        
        # Read and modify the engine
        with open(engine_path, 'r') as f:
            content = f.read()
        
        # Replace current date
        original_line = "self.current_date = datetime.now().strftime('%Y-%m-%d')"
        temp_line = f"self.current_date = '{date}'"
        modified_content = content.replace(original_line, temp_line)
        
        # Write temporary version
        with open(engine_path, 'w') as f:
            f.write(modified_content)
        
        print("🚀 Running unified betting engine...")
        
        try:
            # Step 3: Generate betting recommendations
            result = subprocess.run([
                sys.executable, "unified_betting_engine.py"
            ], cwd=root_dir, capture_output=True, text=True)
            
            if result.returncode != 0:
                print(f"❌ Unified betting engine failed: {result.stderr}")
                return False
            
            print("✅ Unified betting recommendations completed")
            
        finally:
            # Always restore the original engine
            with open(engine_path, 'w') as f:
                f.write(content)
            print("🔧 Restored unified betting engine")
        
        print(f"✅ Successfully regenerated all predictions for {date}")
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def main():
    """Main function"""
    if len(sys.argv) > 1:
        date = sys.argv[1]
    else:
        date = datetime.now().strftime('%Y-%m-%d')
    
    print(f"Quick Prediction Regenerator")
    print(f"Date: {date}")
    print("-" * 40)
    
    success = regenerate_predictions_for_date(date)
    
    if success:
        print("🎉 SUCCESS: Predictions regenerated!")
    else:
        print("💥 FAILED: Could not regenerate predictions")
        sys.exit(1)

if __name__ == "__main__":
    main()
