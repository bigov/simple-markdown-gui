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

To stamp a specific version into the Windows executable metadata:

```powershell
./build_windows.ps1 -Version 1.0.2
```

The script installs build dependencies, cleans previous PyInstaller output, and produces:

```text
dist/simple-markdown-gui.exe
```

## Runtime behavior

- The executable bundles the Python runtime and required PySide6 dependencies.
- CSS and config template files are embedded into the executable as fallback defaults.
- A Windows .ico file is generated from src/assets/icon.png during the build.
- Version metadata is embedded into the executable resource table.
- The build writes editable runtime files to dist/assets/config.ini and dist/assets/styles.css.
- At runtime, the app prefers editable files next to the executable in assets/. If that directory is not writable, it falls back to %APPDATA%/Simple Markdown GUI/assets.

## Release ZIP

Run the release packaging script from the repository root:

```powershell
./build_release_zip.ps1 -Version 1.0.2
```

If dist/simple-markdown-gui.exe is already present and only the archive needs to be rebuilt:

```powershell
./build_release_zip.ps1 -Version 1.0.2 -SkipBuild
```

The script builds the executable and creates:

```text
release/simple-markdown-gui-windows-x64-v1.0.2.zip
release/simple-markdown-gui-windows-x64-v1.0.2.sha256.txt
```

The ZIP archive contains the executable, editable assets/config.ini and assets/styles.css, together with README and license files.

## Cleanup

To remove stale build artifacts, logs, and older release files while keeping the current release:

```powershell
./clean_release_artifacts.ps1 -CurrentVersion 1.0.2
```

## Notes

- The generated executable is intended to be built on Windows for Windows.
- If SmartScreen warns on an unsigned binary, sign the executable as part of the release process.
- A packaged installer is not generated yet; the current release scenario is ZIP-based.
