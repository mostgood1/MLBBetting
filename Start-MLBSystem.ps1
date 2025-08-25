# MLB Betting System PowerShell Launcher
param(
    [switch]$NoWait,
    [switch]$Verbose
)

Write-Host "================================================" -ForegroundColor Cyan
Write-Host "MLB Betting System PowerShell Launcher" -ForegroundColor Cyan  
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
    Write-Host "No virtual environment found - using system Python" -ForegroundColor Yellow
}

Write-Host ""

# Check if required files exist
$requiredFiles = @("app.py", "historical_analysis_app.py")
foreach ($file in $requiredFiles) {
    if (-not (Test-Path $file)) {
        Write-Host "❌ Required file not found: $file" -ForegroundColor Red
        exit 1
    }
}

try {
    # Start main prediction app
    Write-Host "🚀 Starting Main Prediction App (port 5000)..." -ForegroundColor Green
    $mainApp = Start-Process -FilePath "python" -ArgumentList "app.py" -PassThru -WindowStyle Minimized
    
    # Wait a moment for main app to initialize
    Start-Sleep -Seconds 3
    
    # Start historical analysis app
    Write-Host "🚀 Starting Historical Analysis App (port 5001)..." -ForegroundColor Green  
    $historicalApp = Start-Process -FilePath "python" -ArgumentList "historical_analysis_app.py" -PassThru -WindowStyle Minimized
    
    # Wait for both services to be ready
    Write-Host ""
    $mainReady = Wait-ForService -Port 5000 -ServiceName "Main Prediction App" -MaxAttempts 30
    $historicalReady = Wait-ForService -Port 5001 -ServiceName "Historical Analysis App" -MaxAttempts 30
    
    if ($mainReady -and $historicalReady) {
        Write-Host ""
        Write-Host "🎉 MLB Betting System Started Successfully!" -ForegroundColor Green
        Write-Host "================================================" -ForegroundColor Cyan
        Write-Host "📍 Main Prediction App:    http://localhost:5000" -ForegroundColor White
        Write-Host "📍 Historical Analysis:    http://localhost:5001" -ForegroundColor White
        Write-Host "📊 Complete System:        http://localhost:5000/historical-analysis" -ForegroundColor White
        Write-Host "================================================" -ForegroundColor Cyan
        Write-Host ""
        Write-Host "Process IDs:" -ForegroundColor Yellow
        Write-Host "  Main App PID: $($mainApp.Id)" -ForegroundColor Gray
        Write-Host "  Historical App PID: $($historicalApp.Id)" -ForegroundColor Gray
        Write-Host ""
        
        if (-not $NoWait) {
            Write-Host "💡 Press any key to stop both services..." -ForegroundColor Yellow
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
        }
        
    } else {
        Write-Host "❌ One or more services failed to start" -ForegroundColor Red
        
        # Cleanup failed processes
        if ($mainApp -and -not $mainApp.HasExited) { $mainApp.Kill() }
        if ($historicalApp -and -not $historicalApp.HasExited) { $historicalApp.Kill() }
        
        exit 1
    }
    
    } catch {
        Write-Host "❌ Error starting MLB Betting System: $($_.Exception.Message)" -ForegroundColor Red
        exit 1
    }