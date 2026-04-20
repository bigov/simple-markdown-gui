# Windows Build

This project can be packaged into a standalone Windows executable with PyInstaller.

## Prerequisites

- Windows
- Project virtual environment in .venv

## Build

Run the build script from the repository root:

```powershell
./build_windows.ps1
```

The script installs build dependencies, cleans previous PyInstaller output, and produces:

```text
dist/simple-markdown-gui.exe
```

## Runtime behavior

- The executable bundles the Python runtime and required PySide6 dependencies.
- CSS and config template files are embedded into the executable during packaging.
- On first launch, the app creates a writable config file in %APPDATA%/Simple Markdown GUI/config.ini.

## Notes

- The generated executable is intended to be built on Windows for Windows.
- If SmartScreen warns on an unsigned binary, sign the executable as part of the release process.
