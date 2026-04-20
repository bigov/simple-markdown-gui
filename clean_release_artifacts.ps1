param(
    [switch]$KeepCurrentRelease,
    [string]$CurrentVersion = '1.0.2'
)

$ErrorActionPreference = 'Stop'

$repoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$buildDir = Join-Path $repoRoot 'build'
$releaseDir = Join-Path $repoRoot 'release'
$logFiles = @(
    (Join-Path $repoRoot 'build_run.log'),
    (Join-Path $repoRoot 'error.log'),
    (Join-Path $repoRoot 'output.log')
)

if (Test-Path $buildDir) {
    Remove-Item $buildDir -Recurse -Force
}

foreach ($logFile in $logFiles) {
    if (Test-Path $logFile) {
        Remove-Item $logFile -Force
    }
}

if (-not $KeepCurrentRelease -and (Test-Path $releaseDir)) {
    $currentReleasePattern = "simple-markdown-gui-windows-x64-v$CurrentVersion*"
    Get-ChildItem -Path $releaseDir -File |
    Where-Object { $_.Name -notlike $currentReleasePattern } |
    Remove-Item -Force
}

Write-Host 'Cleanup completed successfully.'