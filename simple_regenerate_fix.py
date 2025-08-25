#!/usr/bin/env python3
"""
Simple script to generate recommendations for a specific historical date
"""

import os
import sys
import shutil
import subprocess

def regenerate_for_date(target_date):
    """Regenerate recommendations by temporarily modifying the unified engine"""
    print(f"🎯 Regenerating recommendations for {target_date}")
    
    engine_file = 'unified_betting_engine.py'
    backup_file = f'{engine_file}.backup_temp'
    
    try:
        # Read the original file
        with open(engine_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Backup the original
        shutil.copy2(engine_file, backup_file)
        
        # Replace the current_date initialization
        date_underscore = target_date.replace('-', '_')
        modified_content = content.replace(
            "self.current_date = datetime.now().strftime('%Y-%m-%d')",
            f"self.current_date = '{target_date}'"
        )
        
        # Write the modified version
        with open(engine_file, 'w', encoding='utf-8') as f:
            f.write(modified_content)
        
        print(f"📝 Modified engine to use date: {target_date}")
        
        # Run the unified engine
        print("🚀 Running unified betting engine...")
        result = subprocess.run([
            sys.executable, engine_file
        ], capture_output=True, text=True, encoding='utf-8', errors='replace')
        
        # Restore the original file
        shutil.move(backup_file, engine_file)
        print("✅ Restored original engine file")
        
        if result.returncode == 0:
            print(f"✅ Successfully generated recommendations for {target_date}")
            print("Output:")
            print(result.stdout)
            return True
        else:
            print(f"❌ Engine failed for {target_date}")
            print("STDOUT:", result.stdout)
            print("STDERR:", result.stderr)
            return False
            
    except Exception as e:
        # Ensure we restore the original file even if there's an error
        if os.path.exists(backup_file):
            shutil.move(backup_file, engine_file)
        print(f"💥 Error: {e}")
        return False

if __name__ == "__main__":
    success = regenerate_for_date("2025-08-21")
    if success:
        print("🎉 Regeneration completed successfully!")
    else:
        print("💥 Regeneration failed!")
