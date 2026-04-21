# Simple Markdown GUI

A simple open-source Markdown notes WYSIWYG editor with a graphical interface, written in Python using the [PySide6](https://doc.qt.io/qtforpython/) library.

**License:** MIT

---

## Requirements

- Python 3.10 or newer
- PySide6 6.0 or newer

---

## Installing PySide6

### Install

```bash
pip install PySide6
```

Or install all project dependencies at once using `requirements.txt`:

```bash
pip install -r requirements.txt
```

### Update to the latest version

```bash
pip install --upgrade PySide6
```

### Install a specific version

```bash
pip install PySide6==6.7.0
```

> **Note:** It is recommended to use a virtual environment to avoid conflicts with other Python projects.
>
> ```bash
> git clone https://github.com/bigov/simple-markdown-gui.git
> cd simple-markdown-gui
> python -m pip install --upgrade pip setuptools virtualenv
> python -m venv .venv
> # Activate on Linux / macOS:
> source .venv/bin/activate
> # Activate on Windows:
> .venv\Scripts\activate
>
> pip install -r requirements.txt
> ```

---

## Project structure

```
simple-markdown-gui/
├── src/
│   ├── assets/
│   ├── config.py
│   └── main.py              # Application entry point
├── tests/                   # Unit tests
├── docs/                    # Documentation
├── .vscode/                 # VS Code workspace settings
│   ├── extensions.json
│   ├── launch.json
│   └── settings.json
├── LICENSE                  # MIT License (this project)
├── LICENSE_LGPL             # GNU LGPLv3 (PySide6 / Qt)
├── NOTICE                   # Third-party license notices
├── README.md
└── requirements.txt
```

---

## Running the application

```bash
python src/main.py
```

## Building a standalone Windows executable

The project includes a PowerShell build script that creates a self-contained Windows executable with PyInstaller. The resulting file does not depend on a system-wide Python installation.

```powershell
./build_windows.ps1
```

The script will:

- install build dependencies from requirements-build.txt into the project virtual environment;
- package src/main.py into dist/simple-markdown-gui.exe;
- embed fallback application assets needed at runtime;
- generate a Windows .ico from src/assets/icon.png;
- attach Windows executable metadata such as product name, description, and version resource.

The current verified Windows release is 1.0.2.

To set the executable version metadata explicitly:

```powershell
./build_windows.ps1 -Version 1.0.2
```

To create a distributable release archive:

```powershell
./build_release_zip.ps1 -Version 1.0.2
```

If the executable is already built and you only want to package it into ZIP again:

```powershell
./build_release_zip.ps1 -Version 1.0.2 -SkipBuild
```

To remove stale build artifacts, logs, and older release files in one step:

```powershell
./clean_release_artifacts.ps1 -CurrentVersion 1.0.2
```

The build also places editable runtime files in dist/assets: config.ini and styles.css. The packaged application uses these external files when they are available. If the executable directory is not writable, it falls back to %APPDATA%/Simple Markdown GUI/assets.

---

## Pre-release check

Before a release, run the Markdown round-trip regression test to verify that opening and saving documents in visual mode does not corrupt the original Markdown structure:

```bash
python -m unittest tests.test_markdown_roundtrip -v
```

For a short release workflow, see [docs/release-checklist.md](docs/release-checklist.md).

For build-specific notes, see [docs/build-windows.md](docs/build-windows.md).

---

## License

This project is distributed under the **MIT License** — see [LICENSE](LICENSE) for details.

PySide6 (Qt for Python) is distributed under the **GNU Lesser General Public License v3** — see [LICENSE_LGPL](LICENSE_LGPL) for details.
