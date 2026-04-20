param(
    [switch]$SkipDependencyInstall
)

$ErrorActionPreference = 'Stop'

$repoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$pythonExe = Join-Path $repoRoot '.venv\Scripts\python.exe'
$distDir = Join-Path $repoRoot 'dist'
$buildRoot = Join-Path $env:TEMP ('simple-markdown-gui-pyinstaller-' + (Get-Date -Format 'yyyyMMddHHmmss'))
$workDir = Join-Path $buildRoot 'work'
$specDir = Join-Path $buildRoot 'spec'
$entryPoint = Join-Path $repoRoot 'src\app\main.py'
$stylesPath = Join-Path $repoRoot 'src\app\assets\styles.css'
$configSamplePath = Join-Path $repoRoot 'src\app\assets\config_sample.ini'

if (-not (Test-Path $pythonExe)) {
    throw 'Virtual environment interpreter was not found at .venv\Scripts\python.exe'
}

Push-Location $repoRoot

try {
    if (-not $SkipDependencyInstall) {
        & $pythonExe -m pip install -r requirements-build.txt
        if ($LASTEXITCODE -ne 0) {
            throw 'Failed to install build dependencies.'
        }
    }

    if (Test-Path $distDir) {
        Remove-Item $distDir -Recurse -Force
    }

    $pyInstallerArgs = @(
        '-m', 'PyInstaller',
        '--noconfirm',
        '--clean',
        '--distpath', $distDir,
        '--workpath', $workDir,
        '--specpath', $specDir,
        '--windowed',
        '--onefile',
        '--name', 'simple-markdown-gui',
        '--add-data', "$stylesPath;assets",
        '--add-data', "$configSamplePath;assets",
        $entryPoint
    )

    & $pythonExe @pyInstallerArgs
    if ($LASTEXITCODE -ne 0) {
        throw 'PyInstaller build failed.'
    }

    Write-Host ''
    Write-Host 'Build completed successfully:'
    Write-Host (Join-Path $distDir 'simple-markdown-gui.exe')

    if (Test-Path $buildRoot) {
        Remove-Item $buildRoot -Recurse -Force -ErrorAction SilentlyContinue
    }
}
finally {
    Pop-Location
}