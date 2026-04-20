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
python src/app/main.py
```
