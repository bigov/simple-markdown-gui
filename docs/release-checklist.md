# Release Checklist

Use this checklist before publishing a release.

1. Install dependencies in the project virtual environment.

```bash
pip install -r requirements.txt
```

1. Run the Markdown round-trip regression test.

```bash
python -m unittest tests.test_markdown_roundtrip -v
```

1. Start the application and do a quick smoke test of opening, editing, and saving a Markdown document.

```bash
python src/main.py
```

1. Build the standalone Windows executable and verify that it starts outside the repository.

```powershell
./build_windows.ps1 -Version 1.0.2
```

Confirm that the first launch recreates missing config.ini or styles.css in `%APPDATA%/Markdown GUI` from embedded defaults when either file is removed.

1. Build the Windows release ZIP and attach the generated archive and checksum to the release.

```powershell
./build_release_zip.ps1 -Version 1.0.2
```

1. Clean stale build artifacts and keep only the current release files.

```powershell
./clean_release_artifacts.ps1 -CurrentVersion 1.0.2
```
