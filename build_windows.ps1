param(
    [string]$Version = '0.1.0',
    [string]$CompanyName = 'Simple Markdown GUI contributors',
    [string]$ProductName = 'Simple Markdown GUI',
    [string]$FileDescription = 'Simple Markdown GUI Markdown editor',
    [string]$Copyright = 'Copyright (c) 2026 Simple Markdown GUI contributors',
    [switch]$SkipDependencyInstall
)

$ErrorActionPreference = 'Stop'

$repoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$pythonExe = Join-Path $repoRoot '.venv\Scripts\python.exe'
$distDir = Join-Path $repoRoot 'dist'
$buildRoot = Join-Path $env:TEMP ('simple-markdown-gui-pyinstaller-' + (Get-Date -Format 'yyyyMMddHHmmss'))
$pyInstallerDistDir = Join-Path $buildRoot 'dist'
$workDir = Join-Path $buildRoot 'work'
$resourceDir = Join-Path $buildRoot 'resources'
$faviconPath = Join-Path $repoRoot 'src\resources\icon.png'
$resourceHelper = Join-Path $repoRoot 'tools\prepare_windows_build_resources.py'
$specFilePath = Join-Path $repoRoot 'simple-markdown-gui.spec'
$iconPath = Join-Path $resourceDir 'simple-markdown-gui.ico'
$versionFilePath = Join-Path $resourceDir 'version_info.txt'
$exeName = 'simple-markdown-gui.exe'


if (-not (Test-Path $pythonExe)) {
    throw 'Virtual environment interpreter was not found at .venv\Scripts\python.exe'
}

# Build from the repository root so relative paths in the spec file stay stable.
Push-Location $repoRoot

try {
    if (-not $SkipDependencyInstall) {
        & $pythonExe -m pip install -r requirements-build.txt
        if ($LASTEXITCODE -ne 0) {
            throw 'Failed to install build dependencies.'
        }
    }

    $resourceArgs = @(
        $resourceHelper,
        '--png', $faviconPath,
        '--ico', $iconPath,
        '--version-file', $versionFilePath,
        '--version', $Version,
        '--company-name', $CompanyName,
        '--product-name', $ProductName,
        '--file-description', $FileDescription,
        '--internal-name', 'simple-markdown-gui',
        '--original-filename', $exeName,
        '--copyright', $Copyright
    )

    & $pythonExe @resourceArgs
    if ($LASTEXITCODE -ne 0) {
        throw 'Failed to prepare icon or version metadata resources.'
    }

    $env:SMG_ICON_PATH = $iconPath
    $env:SMG_VERSION_FILE = $versionFilePath

    $pyInstallerArgs = @(
        '-m', 'PyInstaller',
        '--noconfirm',
        '--clean',
        '--log-level', 'WARN',
        '--distpath', $pyInstallerDistDir,
        '--workpath', $workDir,
        $specFilePath
    )

    & $pythonExe @pyInstallerArgs
    $pyInstallerExitCode = $LASTEXITCODE
    Remove-Item Env:SMG_ICON_PATH -ErrorAction SilentlyContinue
    Remove-Item Env:SMG_VERSION_FILE -ErrorAction SilentlyContinue

    if ($pyInstallerExitCode -ne 0) {
        throw 'PyInstaller build failed.'
    }

    $builtExePath = Join-Path $pyInstallerDistDir $exeName
    $targetExePath = Join-Path $distDir $exeName

    if (-not (Test-Path $builtExePath)) {
        throw 'PyInstaller completed without producing the expected executable.'
    }

    New-Item -ItemType Directory -Path $distDir -Force | Out-Null
    if (Test-Path $targetExePath) {
        try {
            Remove-Item $targetExePath -Force
        }
        catch {
            throw 'Existing dist/simple-markdown-gui.exe is locked by another process. Close the running app or file handle and run the build again.'
        }
    }

    Copy-Item $builtExePath -Destination $targetExePath -Force

    Write-Host ''
    Write-Host 'Build completed successfully:'
    Write-Host $targetExePath

    if (Test-Path $buildRoot) {
        Remove-Item $buildRoot -Recurse -Force -ErrorAction SilentlyContinue
    }
}
finally {
    Pop-Location
}