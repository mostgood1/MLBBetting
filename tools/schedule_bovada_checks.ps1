# Runs periodic Bovada props monitoring and refetch if coverage is low.
# Suggested schedule: every 15 minutes 10:00-23:59 US/Eastern on game days.

$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent $PSScriptRoot
$venvPy = Join-Path $repoRoot '.venv\Scripts\python.exe'
$monitor = Join-Path $repoRoot 'tools\monitor_bovada_props.py'

& $venvPy $monitor --min-cover 0.75 --git-commit | Write-Output
