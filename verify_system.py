#!/usr/bin/env python3
"""
MLB Betting System Verification Script
Checks if the system is working correctly with proper configuration
"""

import requests
import json
import time
import sys
from pathlib import Path

def test_endpoint(url, timeout=10):
    """Test if an endpoint is responding"""
    try:
        response = requests.get(url, timeout=timeout)
        return response.status_code == 200, response.status_code
    except requests.exceptions.RequestException as e:
        return False, str(e)

def check_file_exists(file_path):
    """Check if a required file exists"""
    return Path(file_path).exists()

def main():
    print("🔍 MLB Betting System Verification")
    print("=" * 50)
    
    # Check required files
    print("\n📁 Checking Required Files:")
    required_files = [
        "app.py",
        "start_historical_analysis.py", 
        "data/comprehensive_optimized_config.json",
        "data/master_pitcher_stats.json",
        "data/master_team_strength.json"
    ]
    
    missing_files = []
    for file_path in required_files:
        exists = check_file_exists(file_path)
        status = "✅" if exists else "❌"
        print(f"  {status} {file_path}")
        if not exists:
            missing_files.append(file_path)
    
    if missing_files:
        print(f"\n⚠️ Missing files: {', '.join(missing_files)}")
        print("Please ensure all required files are present before starting.")
        return False
    
    # Test service endpoints
    print("\n🌐 Testing Service Endpoints:")
    
    # Test main app
    main_working, main_status = test_endpoint("http://localhost:5000/health")
    main_icon = "✅" if main_working else "❌"
    print(f"  {main_icon} Main App (port 5000): {main_status}")
    
    # Test historical analysis
    historical_working, historical_status = test_endpoint("http://localhost:5002/health")
    historical_icon = "✅" if historical_working else "❌"
    print(f"  {historical_icon} Historical Analysis (port 5002): {historical_status}")
    
    # Test main app routes
    if main_working:
        print("\n🎯 Testing Main App Routes:")
        routes_to_test = [
            ("http://localhost:5000/", "Main Page"),
            ("http://localhost:5000/api/predictions/today", "Today's Predictions"),
            ("http://localhost:5000/debug/config", "Config Debug")
        ]
        
        for url, name in routes_to_test:
            working, status = test_endpoint(url)
            icon = "✅" if working else "❌"
            print(f"  {icon} {name}: {status}")
    
    # Test historical analysis routes
    if historical_working:
        print("\n📊 Testing Historical Analysis Routes:")
        routes_to_test = [
            ("http://localhost:5002/", "Historical Main Page"),
            ("http://localhost:5002/api/dates", "Available Dates")
        ]
        
        for url, name in routes_to_test:
            working, status = test_endpoint(url)
            icon = "✅" if working else "❌"
            print(f"  {icon} {name}: {status}")
    
    # Check configuration
    print("\n⚙️ Checking Configuration:")
    try:
        with open("data/comprehensive_optimized_config.json", "r") as f:
            config = json.load(f)
            
        # Check bias correction
        hfa = config.get("home_field_advantage", 0)
        afb = config.get("away_field_boost", 0)
        net_advantage = hfa - afb
        
        print(f"  Home Field Advantage: {hfa}")
        print(f"  Away Field Boost: {afb}")
        print(f"  Net Home Advantage: {net_advantage}")
        
        # Check if bias correction is applied
        if 0.05 <= net_advantage <= 0.08:
            print("  ✅ Road team bias correction applied correctly")
        else:
            print("  ⚠️ Unusual home/away advantage values")
            
    except Exception as e:
        print(f"  ❌ Error reading configuration: {e}")
    
    # Summary
    print("\n" + "=" * 50)
    if main_working and historical_working:
        print("🎉 System Verification: PASSED")
        print("\n🔗 Access URLs:")
        print("  Main App: http://localhost:5000")
        print("  Historical Analysis: http://localhost:5002")
        return True
    else:
        print("❌ System Verification: FAILED")
        print("\n💡 Troubleshooting:")
        if not main_working:
            print("  - Main app not responding - check if app.py is running")
        if not historical_working:
            print("  - Historical analysis not responding - check if start_historical_analysis.py is running")
        print("  - Use PowerShell script: .\\Start-MLBSystem-Updated.ps1")
        print("  - Check for port conflicts: netstat -ano | findstr :5000")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
