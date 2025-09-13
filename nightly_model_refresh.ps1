# Nightly Pitcher Props Model Refresh
# Runs after games finish to backfill outcomes, train, and promote models.

$ErrorActionPreference = "Continue"

Set-Location "C:\Users\mostg\OneDrive\Coding\MLB-Betting"

$startTime = Get-Date
$logName = "nightly_model_refresh_$($startTime.ToString('yyyyMMdd_HHmmss')).log"
Write-Host "[$startTime] Starting nightly model refresh..."

try {
    & ".\.venv\Scripts\python.exe" "modeling\auto_refresh_models.py" 2>&1 | Tee-Object -FilePath $logName
    $endTime = Get-Date
    $duration = $endTime - $startTime
    Write-Host "[$endTime] Nightly model refresh completed in $($duration.TotalMinutes) minutes"
} catch {
    $errorTime = Get-Date
    Write-Error "[$errorTime] Nightly model refresh failed: $($_.Exception.Message)"
    "[$errorTime] ERROR: $($_.Exception.Message)" | Out-File -FilePath "nightly_model_refresh_error_$($startTime.ToString('yyyyMMdd')).log" -Append
}

Write-Host "Nightly model refresh completed. Check $logName for details."
