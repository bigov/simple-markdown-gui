# Project documentation

Markdown GUI application project.

Current verified Windows release: 1.0.4.

 - [Windows Build](build-windows.md)
 - [Release Checklist](release-checklist.md)

Runtime defaults for config.ini and styles.css are embedded in [../src/config.py](../src/config.py); editable copies are recreated in the user-specific application directory when missing.

Current source layout highlights:

- [../src/main.py](../src/main.py): application entry point and top-level window orchestration.
- [../src/master_panel.py](../src/master_panel.py): central browser/editor panel behavior.
- [../src/sidebar.py](../src/sidebar.py) and [../src/toolbar.py](../src/toolbar.py): UI helper modules.
- [../tests/test_markdown_roundtrip.py](../tests/test_markdown_roundtrip.py) and [../tests/test_master_panel.py](../tests/test_master_panel.py): regression coverage for editor behavior.