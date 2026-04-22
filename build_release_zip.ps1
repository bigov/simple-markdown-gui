param(
    [string]$Version,
    [string]$ReleaseName,
    [switch]$SkipBuild,
    [switch]$SkipDependencyInstall
)

$ErrorActionPreference = 'Stop'

$repoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$buildVersionHelper = Join-Path $repoRoot 'tools\build_version.ps1'
$releaseDir = Join-Path $repoRoot 'release'
$distExe = Join-Path $repoRoot 'dist\simple-markdown-gui.exe'

. $buildVersionHelper

if (-not $Version) {
    $Version = Get-CurrentRepoVersion -RepoRoot $repoRoot
}

if (-not $ReleaseName) {
    $ReleaseName = "simple-markdown-gui-windows-x64-v$Version"
}

$archivePath = Join-Path $releaseDir ($ReleaseName + '.zip')
$hashPath = Join-Path $releaseDir ($ReleaseName + '.sha256.txt')
$stagingDir = Join-Path $env:TEMP ($ReleaseName + '-staging-' + (Get-Date -Format 'yyyyMMddHHmmss'))

Push-Location $repoRoot

try {
    if (-not $SkipBuild) {
        $buildArgs = @(
            '-NoProfile',
            '-ExecutionPolicy', 'Bypass',
            '-File', (Join-Path $repoRoot 'build_windows.ps1')
        )

        if ($Version) {
            $buildArgs += @('-Version', $Version)
        }

        if ($SkipDependencyInstall) {
            $buildArgs += '-SkipDependencyInstall'
        }

        & powershell.exe @buildArgs
        if ($LASTEXITCODE -ne 0) {
            throw 'Windows executable build failed.'
        }
    }

    if (-not (Test-Path $distExe)) {
        throw 'Expected executable was not found in dist.'
    }

    New-Item -ItemType Directory -Path $releaseDir -Force | Out-Null

    if (Test-Path $archivePath) {
        Remove-Item $archivePath -Force
    }

    if (Test-Path $hashPath) {
        Remove-Item $hashPath -Force
    }

    New-Item -ItemType Directory -Path $stagingDir | Out-Null

    Copy-Item $distExe -Destination (Join-Path $stagingDir 'simple-markdown-gui.exe')
    Copy-Item (Join-Path $repoRoot 'README.md') -Destination (Join-Path $stagingDir 'README.md')
    Copy-Item (Join-Path $repoRoot 'LICENSE') -Destination (Join-Path $stagingDir 'LICENSE')
    Copy-Item (Join-Path $repoRoot 'LICENSE_LGPL') -Destination (Join-Path $stagingDir 'LICENSE_LGPL')
    Copy-Item (Join-Path $repoRoot 'NOTICE') -Destination (Join-Path $stagingDir 'NOTICE')

    Compress-Archive -Path (Join-Path $stagingDir '*') -DestinationPath $archivePath -CompressionLevel Optimal

    $hash = Get-FileHash -Path $archivePath -Algorithm SHA256
    Set-Content -Path $hashPath -Value ($hash.Hash + '  ' + [System.IO.Path]::GetFileName($archivePath)) -Encoding ascii

    Write-Host ''
    Write-Host 'Release archive created successfully:'
    Write-Host $archivePath
    Write-Host $hashPath
}
finally {
    if (Test-Path $stagingDir) {
        Remove-Item $stagingDir -Recurse -Force -ErrorAction SilentlyContinue
    }
    Pop-Location
}