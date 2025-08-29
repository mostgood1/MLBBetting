#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Automated log file cleanup for MLB Betting System

.DESCRIPTION
    Cleans up old log files while preserving recent ones for debugging.
    - Keeps 3 most recent automation logs
    - Keeps current day's scheduler logs  
    - Archives old logs instead of deleting them
    - Removes empty/test log files

.EXAMPLE
    .\cleanup_logs.ps1
    .\cleanup_logs.ps1 -KeepCount 5 -DryRun
#>

param(
    [int]$KeepCount = 3,
    [switch]$DryRun
)

$ErrorActionPreference = "SilentlyContinue"

Write-Host "Log Cleanup for MLB Betting System" -ForegroundColor Cyan
Write-Host "=" * 50

# Create logs archive directory
if (-not (Test-Path "logs_archive")) {
    New-Item -ItemType Directory -Path "logs_archive" -Force | Out-Null
    Write-Host "Created logs_archive directory" -ForegroundColor Green
}

# Get log file counts before cleanup
$beforeCount = (Get-ChildItem "*.log" -ErrorAction SilentlyContinue | Measure-Object).Count
$beforeSize = (Get-ChildItem "*.log" -ErrorAction SilentlyContinue | Measure-Object -Property Length -Sum).Sum

Write-Host "Before cleanup: $beforeCount log files ($([math]::Round($beforeSize/1KB,1)) KB total)"

# Archive old automation logs (keep most recent)
$automationLogs = Get-ChildItem "complete_daily_automation_*.log" -ErrorAction SilentlyContinue | Sort-Object LastWriteTime
if ($automationLogs.Count -gt $KeepCount) {
    $logsToArchive = $automationLogs | Select-Object -SkipLast $KeepCount
    
    Write-Host "Archiving $($logsToArchive.Count) old automation logs (keeping $KeepCount most recent)"
    
    foreach ($log in $logsToArchive) {
        if ($DryRun) {
            Write-Host "   [DRY-RUN] Would archive: $($log.Name)" -ForegroundColor Yellow
        } else {
            Move-Item $log.FullName "logs_archive\" -Force
            Write-Host "   Archived: $($log.Name)" -ForegroundColor Green
        }
    }
}

# Remove old scheduler logs (older than 1 day)
$oldSchedulerLogs = Get-ChildItem "data_update_scheduler_*.log" -ErrorAction SilentlyContinue | Where-Object {$_.LastWriteTime -lt (Get-Date).AddDays(-1)}

if ($oldSchedulerLogs) {
    Write-Host "Removing $($oldSchedulerLogs.Count) old scheduler logs"
    foreach ($log in $oldSchedulerLogs) {
        if ($DryRun) {
            Write-Host "   [DRY-RUN] Would remove: $($log.Name)" -ForegroundColor Yellow
        } else {
            Remove-Item $log.FullName -Force
            Write-Host "   Removed: $($log.Name)" -ForegroundColor Green
        }
    }
}

# Remove empty/test logs
$testLogs = @("monitoring_system.log", "automation_test.log", "test.log", "debug.log")
foreach ($testLog in $testLogs) {
    if (Test-Path $testLog) {
        $size = (Get-Item $testLog).Length
        if ($size -eq 0 -or $testLog -like "*test*") {
            if ($DryRun) {
                Write-Host "   [DRY-RUN] Would remove empty/test log: $testLog" -ForegroundColor Yellow
            } else {
                Remove-Item $testLog -Force
                Write-Host "   Removed empty/test log: $testLog" -ForegroundColor Green
            }
        }
    }
}

# Summary
$afterCount = (Get-ChildItem "*.log" -ErrorAction SilentlyContinue | Measure-Object).Count
$afterSize = (Get-ChildItem "*.log" -ErrorAction SilentlyContinue | Measure-Object -Property Length -Sum).Sum
$archivedCount = (Get-ChildItem "logs_archive\*.log" -ErrorAction SilentlyContinue | Measure-Object).Count

Write-Host ""
Write-Host "Results:" -ForegroundColor Cyan
Write-Host "   Current logs: $afterCount files ($([math]::Round($afterSize/1KB,1)) KB)"
Write-Host "   Archived logs: $archivedCount files"
Write-Host "   Cleaned up: $($beforeCount - $afterCount) files"

if ($DryRun) {
    Write-Host ""
    Write-Host "This was a dry run. Use without -DryRun to actually clean files." -ForegroundColor Yellow
} else {
    Write-Host ""
    Write-Host "Log cleanup complete!" -ForegroundColor Green
}
