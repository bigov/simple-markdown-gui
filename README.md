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
├── build_windows.ps1         # Build standalone Windows executable
├── build_release_zip.ps1     # Package release ZIP and checksum
├── clean_release_artifacts.ps1
├── docs/                     # Project documentation
│   ├── index.md
│   ├── build-windows.md
│   └── release-checklist.md
├── release/                  # Release archives and checksums
├── tools/                    # Build helper scripts
├── src/
│   ├── main.py               # Application entry point
│   ├── master_panel.py       # Central browser/editor panel logic
│   ├── config.py             # Runtime config and embedded defaults
│   ├── filesystem.py         # File loading and saving helpers
│   ├── markdown_rendering.py # Markdown-to-HTML rendering helpers
│   ├── markdown_roundtrip.py # Stable round-trip markdown preservation
│   ├── sidebar.py            # File tree sidebar helpers
│   ├── toolbar.py            # Edit toolbar and formatting actions
│   └── resources/            # Build resources such as the app icon
├── tests/                    # Unit and regression tests
│   ├── test_app_paths.py
│   ├── test_markdown_roundtrip.py
│   └── test_master_panel.py
├── .vscode/                 # VS Code workspace settings
│   ├── extensions.json
│   ├── launch.json
│   ├── tasks.json
│   └── settings.json
├── LICENSE                   # MIT License (this project)
├── LICENSE_LGPL              # GNU LGPLv3 (PySide6 / Qt)
├── NOTICE                    # Third-party license notices
├── README.md
├── requirements.txt
├── requirements-build.txt
└── simple-markdown-gui.spec  # PyInstaller spec file
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
- embed fallback application templates in the Python sources;
- generate a Windows .ico from src/resources/icon.png;
- attach Windows executable metadata such as product name, description, and version resource.

The current verified Windows release is 1.0.4.

To set the executable version metadata explicitly:

```powershell
./build_windows.ps1 -Version 1.0.4
```

To create a distributable release archive:

```powershell
./build_release_zip.ps1 -Version 1.0.4
```

If the executable is already built and you only want to package it into ZIP again:

```powershell
./build_release_zip.ps1 -Version 1.0.4 -SkipBuild
```

To remove stale build artifacts, logs, and older release files in one step:

```powershell
./clean_release_artifacts.ps1 -CurrentVersion 1.0.4
```

At startup, the application always uses the user-specific directory derived from `app_name`: `%LOCALAPPDATA%/Markdown GUI` on Windows. If config.ini or styles.css is missing there, the file is recreated from embedded templates in [src/config.py](src/config.py).

---

## Pre-release check

Before a release, run the full automated test suite (includes Markdown round-trip regression coverage):

```bash
python -m pytest -q
```

For a short release workflow, see [docs/release-checklist.md](docs/release-checklist.md).

For build-specific notes, see [docs/build-windows.md](docs/build-windows.md).

---

## License

This project is distributed under the **MIT License** — see [LICENSE](LICENSE) for details.

PySide6 (Qt for Python) is distributed under the **GNU Lesser General Public License v3** — see [LICENSE_LGPL](LICENSE_LGPL) for details.
