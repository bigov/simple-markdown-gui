"""Configuration management for Simple Markdown GUI."""

import configparser
import os
import ctypes
from pathlib import Path
import sys
from typing import NoReturn

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication, QMessageBox

WINDOWS_APP_ID = "MarkdownGui.Application"


class AppConfig:
    """Utility class for managing user application files."""

    app_name = "Markdown GUI"
    styles_file_name = "styles.css"
    config_file_name = "config.ini"
    localappdata_var_name = "LOCALAPPDATA"
    # Backward-compatible alias used by older tests/integration points.
    appdata_var_name = localappdata_var_name
    startup_error_title = "Startup error"
    missing_appdata_message = (
        "Unable to determine the user application data folder from LOCALAPPDATA."
    )
    unsupported_platform_message = "Only Windows platform is supported."

    @classmethod
    def _get_app_data_dir(cls) -> Path:
        appdata_dir = cls._get_environment_local_app_data_dir()
        if appdata_dir is not None:
            return appdata_dir / cls.app_name

        cls._abort_missing_app_data_dir()

    @classmethod
    def _get_environment_local_app_data_dir(cls) -> Path | None:
        appdata_dir = os.environ.get(cls.localappdata_var_name)
        if appdata_dir:
            return Path(appdata_dir)
        return None

    @classmethod
    def _get_legacy_package_app_data_dir(cls) -> Path | None:
        local_app_data_dir = os.environ.get(cls.localappdata_var_name)
        if not local_app_data_dir:
            return None

        packages_dir = Path(local_app_data_dir) / "Packages"
        if not packages_dir.is_dir():
            return None

        package_roaming_dirs = sorted(packages_dir.glob("*/LocalCache/Roaming"))
        for roaming_dir in package_roaming_dirs:
            legacy_dir = roaming_dir / cls.app_name
            if legacy_dir.exists():
                return legacy_dir
        return None

    @classmethod
    def _migrate_legacy_user_files(cls, app_data_dir: Path) -> None:
        legacy_dir = cls._get_legacy_package_app_data_dir()
        if legacy_dir is None or legacy_dir == app_data_dir or not legacy_dir.exists():
            return

        for file_name in (cls.config_file_name, cls.styles_file_name):
            source_path = legacy_dir / file_name
            target_path = app_data_dir / file_name
            if source_path.exists() and not target_path.exists():
                target_path.write_text(
                    source_path.read_text(encoding="utf-8"), encoding="utf-8"
                )

    @classmethod
    def _abort_missing_app_data_dir(cls) -> NoReturn:
        cls.show_startup_error(cls.missing_appdata_message)
        raise SystemExit(1)

    @classmethod
    def show_startup_error(cls, message: str) -> None:
        app = QApplication.instance()
        created_app = False
        if app is None:
            app = QApplication([])
            created_app = True

        QMessageBox.critical(None, cls.startup_error_title, message)

        if created_app:
            app.quit()

    @classmethod
    def get_config_dir(cls) -> str:
        return str(cls._get_app_data_dir())

    @classmethod
    def get_config_path(cls) -> str:
        return str(cls._get_app_data_dir() / cls.config_file_name)

    @classmethod
    def get_styles_path(cls) -> str:
        return str(cls._get_app_data_dir() / cls.styles_file_name)

    @classmethod
    def ensure_user_files_exist(cls) -> str:
        app_data_dir = cls._get_app_data_dir()
        app_data_dir.mkdir(parents=True, exist_ok=True)
        cls._migrate_legacy_user_files(app_data_dir)

        config_path = app_data_dir / cls.config_file_name
        if not config_path.exists():
            config_path.write_text(DEFAULT_CONFIG_TEMPLATE, encoding="utf-8")

        styles_path = app_data_dir / cls.styles_file_name
        if not styles_path.exists():
            styles_path.write_text(DEFAULT_STYLES_TEMPLATE, encoding="utf-8")

        return str(app_data_dir)

    @classmethod
    def ensure_config_exists(cls) -> str:
        app_data_dir = Path(cls.ensure_user_files_exist())
        return str(app_data_dir / cls.config_file_name)

    @classmethod
    def write_config(cls, config: configparser.ConfigParser) -> str:
        config_path = Path(cls.ensure_config_exists())
        config_path.write_text(cls._render_config_text(config), encoding="utf-8")
        return str(config_path)

    @classmethod
    def _render_config_text(cls, config: configparser.ConfigParser) -> str:
        rendered_config = configparser.ConfigParser()
        rendered_config.read_string(DEFAULT_CONFIG_TEMPLATE)

        for section in config.sections():
            if not rendered_config.has_section(section):
                rendered_config.add_section(section)
            for option, value in config.items(section):
                rendered_config.set(section, option, value)

        output_lines = []
        current_section = None
        seen_sections = set()
        seen_options = set()

        for line in DEFAULT_CONFIG_TEMPLATE.splitlines():
            stripped_line = line.strip()

            if stripped_line.startswith("[") and stripped_line.endswith("]"):
                current_section = stripped_line[1:-1]
                seen_sections.add(current_section)
                output_lines.append(line)
                continue

            if not stripped_line or stripped_line.startswith((";", "#")):
                output_lines.append(line)
                continue

            if "=" in line and current_section:
                option_name, _, _ = line.partition("=")
                option_name = option_name.strip()
                option_value = rendered_config.get(
                    current_section, option_name, fallback=""
                )
                seen_options.add((current_section, option_name))
                output_lines.append(f"{option_name} = {option_value}")
                continue

            output_lines.append(line)

        for section in rendered_config.sections():
            extra_options = [
                (option_name, option_value)
                for option_name, option_value in rendered_config.items(section)
                if (section, option_name) not in seen_options
            ]
            if not extra_options:
                continue

            if section not in seen_sections:
                if output_lines and output_lines[-1] != "":
                    output_lines.append("")
                output_lines.append(f"[{section}]")

            for option_name, option_value in extra_options:
                output_lines.append(f"{option_name} = {option_value}")

        return "\n".join(output_lines) + "\n"


def _get_app_icon_path():
    base_path = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    icon_candidates = (
        base_path / "resources" / "icon.png",
        Path(__file__).resolve().parent / "resources" / "icon.png",
    )

    for icon_path in icon_candidates:
        if icon_path.is_file():
            return icon_path

    return None


def setup_app_icon(qt_application, window):
    icon_path = _get_app_icon_path()
    if icon_path is None:
        return

    icon = QIcon(str(icon_path))
    if icon.isNull():
        return

    qt_application.setWindowIcon(icon)
    window.setWindowIcon(icon)


def configure_app_identity():
    if sys.platform != "win32":
        AppConfig.show_startup_error(AppConfig.unsupported_platform_message)
        return

    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(WINDOWS_APP_ID)
    except (AttributeError, OSError):
        return


DEFAULT_CONFIG_TEMPLATE = """[Default]
base_dir = docs
window_width = 1025
window_height = 941
window_left = 40
window_top = 40
sidebar_width = 226
; allowed: normal, maximized, fullscreen
window_state = normal
; allowed: left, right, hidden
sidebar_position = left
; allowed: on, off
toolbar_status = off
"""


DEFAULT_STYLES_TEMPLATE = """
/* Styles for Markdown content in QTextBrowser */

/* Body styles */
body {
    font-family: 'Segoe UI', 'Noto Sans', Arial, Helvetica, sans-serif;
    font-size: 10pt;
    color: #333;
    background-color: #fff;
    margin: 12px 8px 12px 12px;
}

/* Headings */
h1, h2, h3, h4, h5, h6, .h1, .h2, .h3, .h4, .h5, .h6 {
    display: block;
    color: #2c3e50;
    font-weight: bold;
}
.h6, h6 {
    font-size: 10pt;
}

.h5, h5 {
    font-size: 11pt;
}
.h4, h4 {
    font-size: 12pt;
}
.h3, h3 {
    font-size: 13pt;
}
.h2, h2 {
    font-size: 14pt;
    margin-bottom: 0.2em;
}
.h1, h1 {
    font-size: 15pt;
    margin-top: 1.5em;
    margin-bottom: 0.3em;
}

/* Paragraphs */
p {
    margin-bottom: 1em;
}

/* Links */
a {
    color: #2659D1;
    text-decoration: none;
}

a:hover {
    text-decoration: underline;
}

/* Lists */
ul {
    margin-left: -1em;
}

ol, li {
    margin: 0 0 0.2em 0;
    padding: 0;
}

/* Code blocks */
pre, code {
    font-family: 'Noto Sans Mono Condensed Medium', 'Noto Sans Mono Condensed', 'Noto Sans Mono', 'Cascadia Mono', monospace;
    font-size: 10pt;
    background-color: #f1f1f1;
}

pre {
	margin: 0;
	overflow-x: auto;
}

pre code {
	background-color: transparent;
}

table.code-block {
    width: 100%;
    border-collapse: separate;
    border-spacing: 0;
    margin: 0;
    margin-top: 0.5em;
    border: 1px solid #d9d9d9;
    background-color: #f1f1f1;
}

table.code-block td {
    border: 1px solid #f1f1f1;
    padding: 0;
    padding-top: 0.5em;
    text-align: left;
}

td.code-block-gutter,
td.code-block-content,
table.code-block pre {
    background-color: #f1f1f1;
}

/* Blockquotes */
blockquote {
    border-left: 4px solid #3498db;
    padding-left: 1em;
    margin-left: 1em;
    margin-bottom: 1em;
    color: #555;
    font-style: italic;
}

/* Tables */
table {
    border-collapse: collapse;
    margin: 0.5em 0 1em 0;
}

th, td {
    border: 1px solid #ddd;
    padding: 0.5em;
    text-align: left;
}

th {
    background-color: #f2f2f2;
    font-weight: bold;
}

/* Horizontal rules */
hr {
    border: none;
    border-top: 1px solid #ddd;
    margin: 2em 0;
}

/* Images */
img {
    max-width: 100%;
    height: auto;
    display: block;
    margin: 1em auto;
}

/* Emphasis */
strong {
    font-weight: bold;
}

em {
    font-style: italic;
}

"""
