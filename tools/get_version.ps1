function Get-CurrentRepoVersion {
    param(
        [string]$RepoRoot = (Split-Path -Parent $PSScriptRoot)
    )

    $versionFilePath = Join-Path $RepoRoot 'src\__init__.py'
    if (-not (Test-Path $versionFilePath)) {
        throw "Version source file was not found: $versionFilePath"
    }

    $versionLine = Get-Content -Path $versionFilePath |
    Where-Object { $_ -match '^__version__\s*=' } |
    Select-Object -First 1

    if (-not $versionLine) {
        throw "Unable to locate __version__ in $versionFilePath"
    }

    $versionValue = $versionLine.Split('=')[1].Trim().Trim('"').Trim("'")
    if (-not $versionValue) {
        throw "Unable to parse __version__ in $versionFilePath"
    }

    return $versionValue
}