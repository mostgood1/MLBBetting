#!/usr/bin/env python3
"""
Batch Regeneration Script for 8/15 to Current Date
==================================================

Regenerates all predictions and betting recommendations from 8/15 to current date.
"""

import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

def main():
    """Regenerate all predictions from 8/15 to current date"""
    start_date = "2025-08-15"
    end_date = datetime.now().strftime('%Y-%m-%d')
    
    print("🚀 BATCH REGENERATION: 8/15 to Current Date")
    print(f"📅 Date range: {start_date} to {end_date}")
    print("=" * 50)
    
    # Use the comprehensive regeneration script
    cmd = [
        sys.executable, 
        "regenerate_historical_predictions.py",
        "--start-date", start_date,
        "--end-date", end_date
    ]
    
    print("🎯 Running comprehensive regeneration...")
    print(f"Command: {' '.join(cmd)}")
    print("-" * 50)
    
    try:
        result = subprocess.run(cmd, cwd=Path(__file__).parent)
        
        if result.returncode == 0:
            print("\n🎉 SUCCESS: All predictions regenerated!")
            print("\n📊 Check the log file for detailed results")
        else:
            print("\n💥 FAILED: Some predictions could not be regenerated")
            print("📊 Check the log file for details")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n⛔ CANCELLED: User interrupted the process")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
