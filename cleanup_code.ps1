# MLB Betting System Cleanup Script
# This script removes test files, debug scripts, empty files, and other junk

param(
    [switch]$DryRun = $false,
    [switch]$Verbose = $false
)

Write-Host "MLB Betting System Code Cleanup" -ForegroundColor Green
Write-Host "================================" -ForegroundColor Green

$workspaceRoot = "c:\Users\mostg\OneDrive\Coding\MLB-Betting"
Set-Location $workspaceRoot

# List of files to remove
$filesToRemove = @(
    # Empty debug/test files
    "debug_analysis.py",
    "debug_data_structure.py", 
    "debug_manager.py",
    "diagnose_json_error.py",
    "historical_analysis.py",
    "simple_manager.py",
    "start_mlb_system.py",
    "test_api.html",
    "test_comprehensive_fixed.py",
    "test_kelly_guidance.py",
    
    # Empty configuration and cache files
    "balanced_final_config.json",
    "historical_summary_cache.json",
    "YOUR_ACTION_PLAN.md",
    
    # Batch file (replaced with PowerShell)
    "start_mlb_system.bat",
    
    # Old debug/test JSON files 
    "debug_test.json",
    "clean_debug.json"
)

# Files to potentially remove (let user decide)
$questionableFiles = @(
    # Old analysis scripts that might still be useful
    "analyze_betting_line_quality.py",
    "analyze_good_vs_bad_days.py", 
    "check_daily_stats.py",
    "check_lines_discrepancy.py",
    "fix_dashboard_and_analysis.py",
    "quick_performance_check.py"
)

# Old documentation files that might be outdated
$questionableDocs = @(
    "CLEANUP_SUMMARY.md",
    "COMPREHENSIVE_RETUNING_SUMMARY.md", 
    "RETUNING_SUCCESS_REPORT.md",
    "ENHANCED_SYSTEM_STATUS.md",
    "RENDER_COMPATIBILITY_REPORT.md",
    "RENDER_DEPLOYMENT.md",
    "RENDER_FULL_FUNCTIONALITY_STATUS.md"
)

# Directories to clean up (remove empty __pycache__ dirs)
$pyCache = Get-ChildItem -Recurse -Directory -Name "__pycache__"

Write-Host "`nFiles to be removed:" -ForegroundColor Yellow
$actualFilesToRemove = @()
foreach ($file in $filesToRemove) {
    if (Test-Path $file) {
        $fileInfo = Get-Item $file
        $sizeKB = [math]::Round($fileInfo.Length / 1KB, 1)
        Write-Host "  X $file ($sizeKB KB)" -ForegroundColor Red
        $actualFilesToRemove += $file
    }
}

Write-Host "`nQuestionable files (manual review suggested):" -ForegroundColor Yellow
$questionablePresent = @()
foreach ($file in $questionableFiles) {
    if (Test-Path $file) {
        $fileInfo = Get-Item $file
        $sizeKB = [math]::Round($fileInfo.Length / 1KB, 1)
        Write-Host "  ! $file ($sizeKB KB)" -ForegroundColor Yellow
        $questionablePresent += $file
    }
}

Write-Host "`nOld documentation files (consider archiving):" -ForegroundColor Cyan
$questionableDocsPresent = @()
foreach ($file in $questionableDocs) {
    if (Test-Path $file) {
        $fileInfo = Get-Item $file
        $sizeKB = [math]::Round($fileInfo.Length / 1KB, 1)
        Write-Host "  ? $file ($sizeKB KB)" -ForegroundColor Cyan
        $questionableDocsPresent += $file
    }
}

Write-Host "`nPython cache directories to remove:" -ForegroundColor Yellow
foreach ($dir in $pyCache) {
    Write-Host "  DIR $dir" -ForegroundColor Cyan
}

# Count total files
$totalFiles = $actualFilesToRemove.Count + $pyCache.Count
$totalSizeKB = 0
foreach ($file in $actualFilesToRemove) {
    if (Test-Path $file) {
        $totalSizeKB += (Get-Item $file).Length / 1KB
    }
}

Write-Host "`nSummary:" -ForegroundColor Green
Write-Host "  Files to remove: $($actualFilesToRemove.Count)"
Write-Host "  Cache dirs to remove: $($pyCache.Count)"  
Write-Host "  Total space to reclaim: $([math]::Round($totalSizeKB, 1)) KB"

if ($questionablePresent.Count -gt 0) {
    Write-Host "  Files needing manual review: $($questionablePresent.Count)" -ForegroundColor Yellow
}

if ($questionableDocsPresent.Count -gt 0) {
    Write-Host "  Old docs to consider archiving: $($questionableDocsPresent.Count)" -ForegroundColor Cyan
}

if ($DryRun) {
    Write-Host "`nDRY RUN MODE - No files were actually removed" -ForegroundColor Blue
    exit 0
}

if ($actualFilesToRemove.Count -eq 0 -and $pyCache.Count -eq 0) {
    Write-Host "`nNo junk files found! Workspace is already clean." -ForegroundColor Green
    exit 0
}

# Confirm removal
Write-Host "`nDo you want to proceed with removing these files? (y/N): " -ForegroundColor Yellow -NoNewline
$confirmation = Read-Host
if ($confirmation -ne 'y' -and $confirmation -ne 'Y') {
    Write-Host "Cleanup cancelled." -ForegroundColor Red
    exit 0
}

Write-Host "`nStarting cleanup..." -ForegroundColor Green

# Remove files
$removedCount = 0
foreach ($file in $actualFilesToRemove) {
    try {
        Remove-Item $file -Force
        Write-Host "  + Removed: $file" -ForegroundColor Green
        $removedCount++
    }
    catch {
        Write-Host "  - Failed to remove: $file - $($_.Exception.Message)" -ForegroundColor Red
    }
}

# Remove cache directories
$removedDirs = 0
foreach ($dir in $pyCache) {
    try {
        Remove-Item $dir -Recurse -Force
        Write-Host "  + Removed cache: $dir" -ForegroundColor Green
        $removedDirs++
    }
    catch {
        Write-Host "  - Failed to remove cache: $dir - $($_.Exception.Message)" -ForegroundColor Red
    }
}

Write-Host "`nCleanup complete!" -ForegroundColor Green
Write-Host "  Files removed: $removedCount"
Write-Host "  Cache dirs removed: $removedDirs"
Write-Host "  Total space reclaimed: $([math]::Round($totalSizeKB, 1)) KB"

if ($questionablePresent.Count -gt 0) {
    Write-Host "`nManual review recommended for:" -ForegroundColor Yellow
    foreach ($file in $questionablePresent) {
        Write-Host "  > $file" -ForegroundColor Yellow
    }
    Write-Host "  These files may contain useful analysis code." -ForegroundColor Yellow
}

if ($questionableDocsPresent.Count -gt 0) {
    Write-Host "`nOld documentation files to consider archiving:" -ForegroundColor Cyan
    foreach ($file in $questionableDocsPresent) {
        Write-Host "  > $file" -ForegroundColor Cyan
    }
    Write-Host "  These are old status reports that may be outdated." -ForegroundColor Cyan
}

Write-Host "`nNext steps:" -ForegroundColor Blue
Write-Host "  1. Review the questionable files above"
Write-Host "  2. Consider running: git add -A && git commit -m \"Clean up test/debug files\""
Write-Host "  3. Run .\cleanup_logs.ps1 to clean up old log files"
