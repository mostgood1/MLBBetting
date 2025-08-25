@echo off
REM MLB Betting Daily Automation Batch Script
REM This script can be run from Windows Task Scheduler

echo Starting MLB Daily Automation...
echo Date: %date% %time%

REM Change to the MLB-Betting directory
cd /d "C:\Users\mostg\OneDrive\Coding\MLB-Betting"

REM Run the simple daily automation
python simple_daily_automation.py

REM Check exit code
if %errorlevel% equ 0 (
    echo Daily automation completed successfully
) else (
    echo Daily automation failed with error code %errorlevel%
)

REM Pause if running interactively (optional)
REM pause

exit /b %errorlevel%
