#!/usr/bin/env python3
"""
Render Deployment Verification Script
Checks that all necessary files and configurations are present for full functionality
"""

import os
import json
import sys
from pathlib import Path

def check_file_exists(file_path, required=True):
    """Check if a file exists and report status"""
    exists = os.path.exists(file_path)
    status = "✅" if exists else ("❌" if required else "⚠️")
    requirement = "REQUIRED" if required else "OPTIONAL"
    print(f"{status} {file_path} ({requirement})")
    return exists

def check_json_file(file_path, required=True):
    """Check if JSON file exists and is valid"""
    if not os.path.exists(file_path):
        status = "❌" if required else "⚠️"
        requirement = "REQUIRED" if required else "OPTIONAL"
        print(f"{status} {file_path} (MISSING - {requirement})")
        return False
    
    try:
        with open(file_path, 'r') as f:
            json.load(f)
        print(f"✅ {file_path} (VALID JSON)")
        return True
    except json.JSONDecodeError:
        print(f"❌ {file_path} (INVALID JSON)")
        return False

def main():
    print("🔍 Render Deployment Verification")
    print("=" * 50)
    
    # Check core application files
    print("\n📱 Core Application Files:")
    core_files = [
        "app.py",
        "requirements.txt", 
        "runtime.txt",
        "Procfile",
        "build.sh",
        "render.yaml"
    ]
    
    core_issues = 0
    for file in core_files:
        if not check_file_exists(file, required=True):
            core_issues += 1
    
    # Check engine files
    print("\n⚙️ Engine Files:")
    engine_files = [
        "engines/ultra_fast_engine.py",
        "engines/__init__.py",
        "weather_park_integration.py",
        "betting_recommendations_engine.py"
    ]
    
    for file in engine_files:
        check_file_exists(file, required=True)
    
    # Check template files
    print("\n🎨 Template Files:")
    template_files = [
        "templates/index.html",
        "templates/today_games.html"
    ]
    
    for file in template_files:
        check_file_exists(file, required=True)
    
    # Check essential data files
    print("\n📊 Essential Data Files:")
    data_files = [
        ("data/comprehensive_optimized_config.json", True),
        ("data/master_team_strength.json", True),
        ("data/master_pitcher_stats.json", True),
        ("data/team_assets.json", True),
        ("data/unified_predictions_cache.json", False),
        ("data/betting_accuracy_analysis.json", False),
        ("data/daily_dashboard_stats.json", False)
    ]
    
    for file, required in data_files:
        check_json_file(file, required)
    
    # Check environment variables
    print("\n🌍 Environment Configuration:")
    env_vars = [
        ("WEATHER_API_KEY", "487d8b3060df1751a73e0f242629f0ca"),
        ("FLASK_ENV", "production"),
        ("PYTHONUNBUFFERED", "1")
    ]
    
    for var, default in env_vars:
        value = os.environ.get(var, default)
        status = "✅" if value else "❌"
        print(f"{status} {var}={value}")
    
    # Check Python dependencies
    print("\n🐍 Python Dependencies:")
    try:
        import flask
        print(f"✅ Flask {flask.__version__}")
    except ImportError:
        print("❌ Flask not installed")
        core_issues += 1
    
    try:
        import requests
        print(f"✅ Requests available")
    except ImportError:
        print("❌ Requests not installed")
        core_issues += 1
    
    try:
        import numpy
        print(f"✅ Numpy available")
    except ImportError:
        print("❌ Numpy not installed")
        core_issues += 1
    
    # Summary
    print("\n" + "=" * 50)
    if core_issues == 0:
        print("🎉 Deployment verification PASSED!")
        print("Your Render site should have full functionality.")
    else:
        print(f"⚠️ Found {core_issues} critical issues that need to be resolved.")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
