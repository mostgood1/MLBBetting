# PowerShell script to regenerate historical predictions
# Usage: .\regen_predictions.ps1 [date]
# Example: .\regen_predictions.ps1 2025-08-23
# Example: .\regen_predictions.ps1 (uses today's date)

param(
    [string]$Date = ""
)

Write-Host "🎯 MLB Predictions Regenerator" -ForegroundColor Yellow
Write-Host "================================" -ForegroundColor Yellow

if ($Date -eq "") {
    $Date = Get-Date -Format "yyyy-MM-dd"
    Write-Host "📅 Using today's date: $Date" -ForegroundColor Green
} else {
    Write-Host "📅 Using specified date: $Date" -ForegroundColor Green
}

try {
    # Run the quick regeneration script
    Write-Host "🚀 Starting prediction regeneration..." -ForegroundColor Cyan
    python quick_regen.py $Date
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ SUCCESS: Predictions regenerated for $Date" -ForegroundColor Green
        
        # Test the API to see updated results
        Write-Host "🧪 Testing updated predictions..." -ForegroundColor Cyan
        python -c "import requests; r = requests.get('http://127.0.0.1:5000/api/today-games'); d = r.json(); print(f'✅ API working: {len(d.get(\"games\", []))} games loaded')"
    } else {
        Write-Host "❌ FAILED: Could not regenerate predictions" -ForegroundColor Red
        exit 1
    }
} catch {
    Write-Host "💥 ERROR: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

Write-Host "🎉 Complete!" -ForegroundColor Green
