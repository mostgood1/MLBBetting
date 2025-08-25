# PowerShell script to batch-generate betting recommendations for a date range
# This script runs the betting recommendations engine sequentially for each date

$startDay = 15
$endDay = 22
$year = 2025
$month = 8

Push-Location "$(Split-Path -Path $MyInvocation.MyCommand.Definition -Parent)"
for ($d = $startDay; $d -le $endDay; $d++) {
    $date = "{0:D4}-{1:D2}-{2:D2}" -f $year, $month, $d
    Write-Host "Running betting recommendations engine for $date"
    python betting_recommendations_engine.py --date $date
}
Pop-Location
Write-Host "Batch betting recommendations complete. Check data/betting_recommendations_YYYY_MM_DD.json for all dates."
