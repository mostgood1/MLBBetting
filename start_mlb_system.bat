@echo off
echo.
echo ================================================
echo MLB Betting System Startup Script
echo ================================================
echo.

REM Activate virtual environment if it exists
if exist .venv\Scripts\activate.bat (
    echo Activating virtual environment...
    call .venv\Scripts\activate.bat
) else (
    echo No virtual environment found - using system Python
)

echo.
echo Starting MLB Betting System Services...
echo.

REM Start main prediction app in background
echo Starting Main Prediction App on port 5000...
start "MLB Main App" /min python app.py

REM Wait a few seconds for main app to initialize
timeout /t 3 /nobreak >nul

REM Start historical analysis app in background  
echo Starting Historical Analysis App on port 5001...
start "MLB Historical Analysis" /min python historical_analysis_app.py

REM Wait for services to start
timeout /t 5 /nobreak >nul

echo.
echo ================================================
echo MLB Betting System Started Successfully!
echo ================================================
echo.
echo Main Prediction App:     http://localhost:5000
echo Historical Analysis:     http://localhost:5001  
echo Complete System:         http://localhost:5000/historical-analysis
echo.
echo Both services are running in minimized windows
echo Close the command windows to stop the services
echo.
pause
