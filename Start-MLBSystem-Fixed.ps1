# MLB Betting System PowerShell Launcher - Updated Version
param(
    [switch]$NoWait,
    [switch]$Verbose
)

Write-Host "================================================" -ForegroundColor Cyan
Write-Host "MLB Betting System PowerShell Launcher (Updated)" -ForegroundColor Cyan  
Write-Host "================================================" -ForegroundColor Cyan
Write-Host ""

# Function to check if port is available
function Test-Port {
    param([int]$Port)
    try {
        $connection = New-Object System.Net.Sockets.TcpClient
        $connection.Connect("localhost", $Port)
        $connection.Close()
        return $true
    }
    catch {
        return $false
    }
}

# Function to wait for service to be ready
function Wait-ForService {
    param([int]$Port, [string]$ServiceName, [int]$MaxAttempts = 30)
    
    Write-Host "Waiting for $ServiceName to be ready on port $Port..." -ForegroundColor Yellow
    
    for ($i = 1; $i -le $MaxAttempts; $i++) {
        if (Test-Port -Port $Port) {
            Write-Host "✅ $ServiceName is ready!" -ForegroundColor Green
            return $true
        }
        Start-Sleep -Seconds 1
        if ($Verbose) {
            Write-Host "  Attempt $i/$MaxAttempts..." -ForegroundColor Gray
        }
    }
    
    Write-Host "❌ $ServiceName failed to start within $MaxAttempts seconds" -ForegroundColor Red
    return $false
}

# Check if virtual environment exists
if (Test-Path ".venv\Scripts\Activate.ps1") {
    Write-Host "Activating virtual environment..." -ForegroundColor Yellow
    & .venv\Scripts\Activate.ps1
} else {
    Write-Host "❌ Virtual environment not found - please run 'python -m venv .venv' first" -ForegroundColor Red
    exit 1
}

Write-Host ""

# Check if required files exist
$requiredFiles = @("app.py", "start_historical_analysis.py")
foreach ($file in $requiredFiles) {
    if (-not (Test-Path $file)) {
        Write-Host "❌ Required file not found: $file" -ForegroundColor Red
        exit 1
    }
}

# Check if essential data files exist
$dataFiles = @(
    "data\comprehensive_optimized_config.json",
    "data\master_pitcher_stats.json", 
    "data\master_team_strength.json"
)
foreach ($file in $dataFiles) {
    if (-not (Test-Path $file)) {
        Write-Host "⚠️ Warning: Essential data file missing: $file" -ForegroundColor Yellow
    }
}

# Kill any existing Python processes to avoid conflicts
Write-Host "🧹 Cleaning up any existing Python processes..." -ForegroundColor Yellow
Get-Process python -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 2

try {
    # Start main prediction app
    Write-Host "🚀 Starting Main Prediction App (port 5000)..." -ForegroundColor Green
    $mainApp = Start-Process -FilePath "python" -ArgumentList "app.py" -PassThru -WindowStyle Minimized
    
    # Wait a moment for main app to initialize
    Start-Sleep -Seconds 5
    
    # Start historical analysis app (using stable startup script)
    Write-Host "🚀 Starting Historical Analysis App (port 5002)..." -ForegroundColor Green  
    $historicalApp = Start-Process -FilePath "python" -ArgumentList "start_historical_analysis.py" -PassThru -WindowStyle Minimized
    
    # Wait for both services to be ready
    Write-Host ""
    $mainReady = Wait-ForService -Port 5000 -ServiceName "Main Prediction App" -MaxAttempts 45
    $historicalReady = Wait-ForService -Port 5002 -ServiceName "Historical Analysis App" -MaxAttempts 30
    
    if ($mainReady -and $historicalReady) {
        Write-Host ""
        Write-Host "🎉 MLB Betting System Started Successfully!" -ForegroundColor Green
        Write-Host "================================================" -ForegroundColor Cyan
        Write-Host "📍 Main Prediction App:    http://localhost:5000" -ForegroundColor White
        Write-Host "📊 Historical Analysis:    http://localhost:5002" -ForegroundColor White
        Write-Host "🔍 Health Checks:" -ForegroundColor White
        Write-Host "   Main:                   http://localhost:5000/health" -ForegroundColor Gray
        Write-Host "   Historical:             http://localhost:5002/health" -ForegroundColor Gray
        Write-Host "================================================" -ForegroundColor Cyan
        Write-Host ""
        Write-Host "Process IDs:" -ForegroundColor Yellow
        Write-Host "  Main App PID: $($mainApp.Id)" -ForegroundColor Gray
        Write-Host "  Historical App PID: $($historicalApp.Id)" -ForegroundColor Gray
        Write-Host ""
        
        # Test health endpoints
        try {
            Write-Host "🔍 Testing health endpoints..." -ForegroundColor Yellow
            $mainHealth = Invoke-WebRequest -Uri "http://localhost:5000/health" -UseBasicParsing -TimeoutSec 5
            $historicalHealth = Invoke-WebRequest -Uri "http://localhost:5002/health" -UseBasicParsing -TimeoutSec 5
            
            if ($mainHealth.StatusCode -eq 200 -and $historicalHealth.StatusCode -eq 200) {
                Write-Host "✅ Both services are responding correctly!" -ForegroundColor Green
            }
        }
        catch {
            Write-Host "⚠️ Health check warning: $($_.Exception.Message)" -ForegroundColor Yellow
        }
        
        if (-not $NoWait) {
            Write-Host ""
            Write-Host "💡 System is ready! Press any key to stop both services..." -ForegroundColor Yellow
            $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
            
            Write-Host ""
            Write-Host "🛑 Stopping services..." -ForegroundColor Yellow
            
            if (-not $mainApp.HasExited) {
                $mainApp.Kill()
                Write-Host "✅ Main app stopped" -ForegroundColor Green
            }
            
            if (-not $historicalApp.HasExited) {
                $historicalApp.Kill() 
                Write-Host "✅ Historical analysis app stopped" -ForegroundColor Green
            }
            
            Write-Host "🏁 All services stopped" -ForegroundColor Green
        } else {
            Write-Host "Running in background mode. Use 'Get-Process python' to monitor." -ForegroundColor Yellow
            Write-Host "To stop services later: Get-Process python | Stop-Process -Force" -ForegroundColor Yellow
        }
        
    } else {
        Write-Host "❌ One or more services failed to start" -ForegroundColor Red
        Write-Host ""
        Write-Host "Troubleshooting tips:" -ForegroundColor Yellow
        Write-Host "1. Check if virtual environment is activated" -ForegroundColor Gray
        Write-Host "2. Verify all dependencies are installed: pip install -r requirements.txt" -ForegroundColor Gray
        Write-Host "3. Check for port conflicts: netstat -ano | findstr :5000" -ForegroundColor Gray
        Write-Host "4. Review any error messages above" -ForegroundColor Gray
        
        # Cleanup failed processes
        if ($mainApp -and -not $mainApp.HasExited) { $mainApp.Kill() }
        if ($historicalApp -and -not $historicalApp.HasExited) { $historicalApp.Kill() }
        
        exit 1
    }
    
} catch {
    Write-Host "❌ Error starting MLB Betting System: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host ""
    Write-Host "Common solutions:" -ForegroundColor Yellow
    Write-Host "- Ensure Python and pip are installed" -ForegroundColor Gray
    Write-Host "- Run: pip install -r requirements.txt" -ForegroundColor Gray
    Write-Host "- Check if ports 5000 and 5002 are available" -ForegroundColor Gray
    
    # Cleanup any processes that might have started
    if ($mainApp -and -not $mainApp.HasExited) { $mainApp.Kill() }
    if ($historicalApp -and -not $historicalApp.HasExited) { $historicalApp.Kill() }
    
    exit 1
}
