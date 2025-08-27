@echo off
echo.
echo =======================================
echo    MLB Betting System Launcher
echo =======================================
echo.

REM Check if we're in the right directory
if not exist "app.py" (
    echo Error: app.py not found. Please run this from the MLB-Betting directory.
    pause
    exit /b 1
)

REM Activate virtual environment if it exists
if exist ".venv\Scripts\activate.bat" (
    echo Activating virtual environment...
    call .venv\Scripts\activate.bat
) else if exist "venv\Scripts\activate.bat" (
    echo Activating virtual environment...
    call venv\Scripts\activate.bat
) else (
    echo No virtual environment found - using system Python
)

echo.
echo Starting Main MLB Betting Application...
echo Main app will be available at: http://localhost:5000
echo.

REM Start the main application
start "MLB Betting App" python app.py

echo.
echo Waiting 10 seconds for main app to initialize...
timeout /t 10 /nobreak >nul

echo.
echo Starting Historical Analysis Service...
echo Historical analysis will be available at: http://localhost:5001
echo.

REM Start historical analysis if it exists
if exist "historical_analysis_app.py" (
    start "MLB Historical Analysis" python historical_analysis_app.py
    echo Historical analysis service started.
) else (
    echo Historical analysis app not found, skipping...
)

echo.
echo =======================================
echo    MLB Betting System Status
echo =======================================
echo Main Application: http://localhost:5000
echo Historical Analysis: http://localhost:5001
echo.
echo Both services are starting in separate windows.
echo To stop services, close their respective windows.
echo.
pause
