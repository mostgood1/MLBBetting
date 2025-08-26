# 🎯 MLB Betting System - Complete Local Setup Guide

## 📋 Prerequisites

1. **Python Virtual Environment**
   ```powershell
   # Verify virtual environment exists
   Test-Path .venv\Scripts\Activate.ps1
   ```

2. **Required Dependencies**
   ```powershell
   # Activate virtual environment
   .venv\Scripts\Activate.ps1
   
   # Install dependencies if needed
   pip install -r requirements.txt
   ```

## 🚀 Quick Start (Recommended)

### Option 1: Using Updated PowerShell Script
```powershell
# Start both apps with proper port configuration
.\Start-MLBSystem-Updated.ps1
```

### Option 2: Manual Start (Most Reliable)
```powershell
# Terminal 1: Start Main Prediction App
.venv\Scripts\Activate.ps1
python app.py
# Runs on http://localhost:5000

# Terminal 2: Start Historical Analysis (Fixed Version)  
.venv\Scripts\Activate.ps1
python start_historical_analysis.py
# Runs on http://localhost:5002
```

## 🔧 Updated Port Configuration

**IMPORTANT**: The historical analysis app should use port 5002 (not 5001) to avoid conflicts:

- **Main Prediction App**: `http://localhost:5000`
- **Historical Analysis**: `http://localhost:5002` 
- **Health Checks**: 
  - Main: `http://localhost:5000/health`
  - Historical: `http://localhost:5002/health`

## 📊 System Components

### 1. Main Prediction App (`app.py`)
- **Purpose**: Primary betting predictions interface
- **Features**: 
  - Today's game predictions
  - Betting recommendations  
  - Performance analytics
  - Admin tuning dashboard
- **Port**: 5000
- **Key Routes**: `/`, `/admin`, `/api/test-route`

### 2. Historical Analysis App (`start_historical_analysis.py`)
- **Purpose**: Historical performance analysis
- **Features**:
  - 11 dates of historical data (2025-08-15 to 2025-08-25)
  - Prediction accuracy tracking
  - Betting performance analysis
- **Port**: 5002 (fixed configuration)
- **Key Routes**: `/`, `/health`, `/api/available-dates`

## 🔍 Verification Steps

1. **Check Both Services Running**
   ```powershell
   # Test main app
   Invoke-WebRequest -Uri "http://localhost:5000/health" -UseBasicParsing
   
   # Test historical analysis  
   Invoke-WebRequest -Uri "http://localhost:5002/health" -UseBasicParsing
   ```

2. **Access Web Interfaces**
   - Main predictions: http://localhost:5000
   - Historical analysis: http://localhost:5002
   - Navigation between apps via UI links

## ⚠️ Common Issues & Solutions

### Issue 1: Port Conflicts
**Symptom**: "Unable to connect" or "Address already in use"
**Solution**: 
```powershell
# Check what's using ports
netstat -ano | findstr :5000
netstat -ano | findstr :5002

# Kill conflicting processes if needed
taskkill /PID <process_id> /F
```

### Issue 2: Virtual Environment Not Activated
**Symptom**: Module import errors
**Solution**:
```powershell
# Always activate before starting
.venv\Scripts\Activate.ps1
```

### Issue 3: Historical Analysis Crashes
**Symptom**: App starts then stops during data loading  
**Solution**: Use the stable startup script:
```powershell
python start_historical_analysis.py
```

### Issue 4: Missing Data Files
**Symptom**: "No predictions found" or empty displays
**Solution**: Ensure data files exist:
```powershell
# Check key data files
ls data\*2025_08_25*
ls data\comprehensive_optimized_config.json
ls data\master_*.json
```

## 🎛️ Advanced Configuration

### Environment Variables
```powershell
# Optional: Set custom ports
$env:PORT = "5000"              # Main app port
$env:HISTORICAL_PORT = "5002"   # Historical analysis port
$env:FLASK_ENV = "development"  # Enable debug features
```

### Performance Monitoring
```powershell
# Monitor system resources
Get-Process python | Select-Object Id, ProcessName, CPU, WorkingSet
```

## 🔗 System Integration

Both apps are designed to work together:
- Main app has links to historical analysis
- Historical analysis has "Back to Dashboard" links
- Shared data directory and configurations
- Consistent UI styling and navigation

## 📈 Expected Performance

**System Ready Indicators**:
- Main app: Status 200, shows today's games
- Historical analysis: Status 200, "11 dates available"
- Memory usage: ~100-200MB per app
- Startup time: 30-60 seconds total

## 🆘 Troubleshooting Commands

```powershell
# Full system restart
Get-Process python | Stop-Process -Force
Start-Sleep -Seconds 3
.\Start-MLBSystem-Updated.ps1

# Check logs for errors
python -c "import logging; print('Python logging working')"

# Verify model configuration
python -c "from engines.ultra_fast_engine import UltraFastSimEngine; print('Engine import successful')"
```

---

**For the most reliable local setup, use the manual start method with two terminals. This avoids port conflicts and provides better error visibility.**
