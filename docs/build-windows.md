# Windows Build

This project can be packaged into a standalone Windows executable with PyInstaller and then wrapped into a release ZIP archive.

## Prerequisites

- Windows
- Project virtual environment in .venv

## Build

Run the build script from the repository root:

```powershell
./build_windows.ps1
```

The script reads the executable version from [../src/__init__.py](../src/__init__.py).

The script installs build dependencies, cleans previous PyInstaller output, and produces:

```text
dist/simple-markdown-gui.exe
```

## Runtime behavior

- The executable bundles the Python runtime and required PySide6 dependencies.
- CSS and config templates are embedded in the Python sources as fallback defaults.
- A Windows .ico file is generated from src/resources/icon.png during the build.
- Version metadata is embedded into the executable resource table.
- At startup, the app always uses the user-specific directory derived from `app_name`: `%LOCALAPPDATA%/Markdown GUI` on Windows.
- If config.ini or styles.css is missing in that directory, the app recreates the file from the embedded template in [../src/config.py](../src/config.py).

## Release ZIP

Run the release packaging script from the repository root:

```powershell
./build_release_zip.ps1
```

If dist/simple-markdown-gui.exe is already present and only the archive needs to be rebuilt:

```powershell
./build_release_zip.ps1 -SkipBuild
```

The script builds the executable and creates:

```text
release/simple-markdown-gui-windows-x64-v1.0.4.zip
release/simple-markdown-gui-windows-x64-v1.0.4.sha256.txt
```

The archive version in the file name is derived from [../src/__init__.py](../src/__init__.py).

The ZIP archive contains the executable together with README and license files.

## Cleanup

To remove stale build artifacts, logs, and older release files while keeping the current release:

```powershell
./clean_release_artifacts.ps1
```

## Notes

- The generated executable is intended to be built on Windows for Windows.
- If SmartScreen warns on an unsigned binary, sign the executable as part of the release process.
- A packaged installer is not generated yet; the current release scenario is ZIP-based.
