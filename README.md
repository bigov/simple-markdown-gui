# Simple Markdown GUI

A simple open-source Markdown editor with a graphical interface, written in Python using the [PySide6](https://doc.qt.io/qtforpython/) library.

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
│   └── app/
│       ├── __init__.py
│       └── main.py          # Application entry point
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
python src/app/main.py
```

---

## License

This project is distributed under the **MIT License** — see [LICENSE](LICENSE) for details.

PySide6 (Qt for Python) is distributed under the **GNU Lesser General Public License v3** — see [LICENSE_LGPL](LICENSE_LGPL) for details.
