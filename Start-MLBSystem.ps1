# MLB System Launcher
# Enhanced version with better error handling and process management

param(
    [switch]$NoWait
)

# Configuration
$workingDir = "c:\Users\mostg\OneDrive\Coding\MLB-Betting"
$venvPath = Join-Path $workingDir ".venv"
$venvActivate = Join-Path $venvPath "Scripts\Activate.ps1"
$mainApp = "app.py"
$historicalApp = "historical_analysis_app.py"
$mainPort = 5000
$historicalPort = 5001
$logDir = Join-Path $workingDir "logs"

# Ensure we're in the right directory
Set-Location $workingDir

# Check if virtual environment exists
if (-not (Test-Path $venvActivate)) {
    Write-Host "Error: Virtual environment not found at $venvPath" -ForegroundColor Red
    Write-Host "Please create a virtual environment first:" -ForegroundColor Yellow
    Write-Host "python -m venv .venv" -ForegroundColor Yellow
    exit 1
}

# Create logs directory if it doesn't exist
if (-not (Test-Path $logDir)) {
    New-Item -ItemType Directory -Path $logDir -Force | Out-Null
}

# Function to check if port is in use
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

# Function to start application in separate window
function Start-Application {
    param(
        [string]$AppName,
        [int]$Port,
        [string]$LogSuffix
    )
    
    if (Test-Port -Port $Port) {
        Write-Host "Port $Port is already in use. Application may already be running." -ForegroundColor Yellow
        return $null
    }
    
    $logFile = Join-Path $logDir "mlb_system_$LogSuffix.log"
    Write-Host "Starting $AppName in separate window on port $Port..."
    Write-Host "Log file: $logFile"
    
    # Create command to run in new window
    $windowTitle = "MLB $LogSuffix App - Port $Port"
    $command = "cd '$workingDir'; & '$venvActivate'; python '$AppName' 2>&1 | Tee-Object -FilePath '$logFile'"
    
    # Start the application in a new PowerShell window
    $process = Start-Process -FilePath "powershell.exe" -ArgumentList @(
        "-NoExit",
        "-Command",
        "`$Host.UI.RawUI.WindowTitle = '$windowTitle'; $command"
    ) -PassThru
    
    # Wait a moment for the app to start
    Start-Sleep -Seconds 5
    
    if (Test-Port -Port $Port) {
        Write-Host "$AppName started successfully on port $Port" -ForegroundColor Green
        return $process
    } else {
        Write-Host "Failed to start $AppName on port $Port" -ForegroundColor Red
        return $null
    }
}

# Stop any existing processes on the ports
Write-Host "Checking for existing processes..."
$existingMainProcess = Get-NetTCPConnection -LocalPort $mainPort -ErrorAction SilentlyContinue
$existingHistoricalProcess = Get-NetTCPConnection -LocalPort $historicalPort -ErrorAction SilentlyContinue

if ($existingMainProcess) {
    Write-Host "Stopping existing process on port $mainPort..."
    Stop-Process -Id $existingMainProcess.OwningProcess -Force -ErrorAction SilentlyContinue
}

if ($existingHistoricalProcess) {
    Write-Host "Stopping existing process on port $historicalPort..."
    Stop-Process -Id $existingHistoricalProcess.OwningProcess -Force -ErrorAction SilentlyContinue
}

# Start applications
Write-Host "Starting MLB Betting System..." -ForegroundColor Cyan
Write-Host "Working directory: $workingDir"

$mainProcess = Start-Application -AppName $mainApp -Port $mainPort -LogSuffix "main"
$historicalProcess = Start-Application -AppName $historicalApp -Port $historicalPort -LogSuffix "historical"

# Summary
Write-Host "`n=== MLB System Status ===" -ForegroundColor Cyan
if ($mainProcess) {
    Write-Host "[OK] Main App: http://localhost:$mainPort" -ForegroundColor Green
} else {
    Write-Host "[ERROR] Main App: Failed to start" -ForegroundColor Red
}

if ($historicalProcess) {
    Write-Host "[OK] Historical App: http://localhost:$historicalPort" -ForegroundColor Green
} else {
    Write-Host "[ERROR] Historical App: Failed to start" -ForegroundColor Red
}

if ($mainProcess -or $historicalProcess) {
    Write-Host "`nApplications are running in separate windows." -ForegroundColor Yellow
    Write-Host "Close the individual windows to stop each application." -ForegroundColor Yellow
    
    # Try to open browser automatically
    if ($mainProcess) {
        try {
            Start-Process "http://localhost:$mainPort"
            Write-Host "Main application opened in browser." -ForegroundColor Green
        } catch {
            Write-Host "Could not automatically open browser. Navigate to http://localhost:$mainPort manually." -ForegroundColor Yellow
        }
    }
    
    if (-not $NoWait) {
        Write-Host "`nPress any key to exit launcher (applications will continue running)..."
        $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
    }
    
    Write-Host "`nLauncher exiting. Applications are still running in their windows." -ForegroundColor Green
} else {
    Write-Host "Failed to start any applications. Check the error messages above." -ForegroundColor Red
    exit 1
}
