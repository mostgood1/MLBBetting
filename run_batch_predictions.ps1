# PowerShell script to safely batch-generate predictions for a date range
# This script runs the prediction engine sequentially for each date, ensuring the cache is appended correctly

$startDay = 15
$endDay = 23
$year = 2025
$month = 8

for ($d = $startDay; $d -le $endDay; $d++) {
    $date = "{0:D4}-{1:D2}-{2:D2}" -f $year, $month, $d
    Write-Host "Running prediction engine for $date"
    python daily_ultrafastengine_predictions.py --date $date
}
Write-Host "Batch prediction complete. Check data/unified_predictions_cache.json for all dates."
