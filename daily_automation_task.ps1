# Daily MLB Betting System Automation
# This script runs automatically to update predictions and performance data

# Set error handling
$ErrorActionPreference = "Continue"

# Change to the MLB Betting directory
Set-Location "C:\Users\mostg\OneDrive\Coding\MLB-Betting"

# Log start time
$startTime = Get-Date
Write-Host "[$startTime] Starting daily MLB betting automation..."

try {
    # Activate virtual environment and run automation
    & ".\.venv\Scripts\python.exe" "complete_daily_automation.py" 2>&1 | Tee-Object -FilePath "daily_automation_$(Get-Date -Format 'yyyyMMdd_HHmmss').log"
    
    $endTime = Get-Date
    $duration = $endTime - $startTime
    Write-Host "[$endTime] Daily automation completed in $($duration.TotalMinutes) minutes"
    
} catch {
    $errorTime = Get-Date
    Write-Error "[$errorTime] Daily automation failed: $($_.Exception.Message)"
    
    # Log error to file
    "[$errorTime] ERROR: $($_.Exception.Message)" | Out-File -FilePath "daily_automation_error_$(Get-Date -Format 'yyyyMMdd').log" -Append
}

# Optional: Send notification (can be customized)
Write-Host "Daily MLB automation task completed. Check logs for details."
