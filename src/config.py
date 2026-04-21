"""Configuration management for Simple Markdown GUI."""
import configparser
import os
import ctypes
from pathlib import Path
import sys
from typing import NoReturn

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication, QMessageBox

WINDOWS_APP_ID = 'MarkdownGui.Application'

class AppConfig:
    """Utility class for managing user application files."""
    app_name = 'Markdown GUI'
    styles_file_name = 'styles.css'
    config_file_name = 'config.ini'
    appdata_var_name = 'APPDATA'
    startup_error_title = 'Startup error'
    missing_appdata_message = 'Unable to determine the user application data directory from APPDATA.'
    unsupported_platform_message = 'Only Windows platform is supported.'

    @classmethod
    def _get_app_data_dir(cls) -> Path:
        appdata_dir = os.environ.get(cls.appdata_var_name)
        if appdata_dir:
            return Path(appdata_dir) / cls.app_name
        cls._abort_missing_app_data_dir()

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

        config_path = app_data_dir / cls.config_file_name
        if not config_path.exists():
            config_path.write_text(DEFAULT_CONFIG_TEMPLATE, encoding='utf-8')

        styles_path = app_data_dir / cls.styles_file_name
        if not styles_path.exists():
            styles_path.write_text(DEFAULT_STYLES_TEMPLATE, encoding='utf-8')

        return str(app_data_dir)

    @classmethod
    def ensure_config_exists(cls) -> str:
        app_data_dir = Path(cls.ensure_user_files_exist())
        return str(app_data_dir / cls.config_file_name)

    @classmethod
    def write_config(cls, config: configparser.ConfigParser) -> str:
        config_path = Path(cls.ensure_config_exists())
        config_path.write_text(cls._render_config_text(config), encoding='utf-8')
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

            if stripped_line.startswith('[') and stripped_line.endswith(']'):
                current_section = stripped_line[1:-1]
                seen_sections.add(current_section)
                output_lines.append(line)
                continue

            if not stripped_line or stripped_line.startswith((';', '#')):
                output_lines.append(line)
                continue

            if '=' in line and current_section:
                option_name, _, _ = line.partition('=')
                option_name = option_name.strip()
                option_value = rendered_config.get(current_section, option_name, fallback='')
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
                if output_lines and output_lines[-1] != '':
                    output_lines.append('')
                output_lines.append(f'[{section}]')

            for option_name, option_value in extra_options:
                output_lines.append(f"{option_name} = {option_value}")

        return '\n'.join(output_lines) + '\n'


def _get_app_icon_path():
    base_path = Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parent))
    icon_candidates = (
        base_path / 'resources' / 'icon.png',
        Path(__file__).resolve().parent / 'resources' / 'icon.png',
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
    if sys.platform != 'win32':
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
; allowed: visible, hidden
toolbar_visibility = hidden
"""


DEFAULT_STYLES_TEMPLATE = """/* Styles for Markdown content in QTextBrowser */

/* Body styles */
body {
    font-family: 'Adwaita Sans', Arial, sans-serif;
    font-size: 11pt;
    color: #333;
    background-color: #fff;
    margin: 12px 8px 12px 12px;
}

/* Headings */
h1, h2, h3, h4, h5, h6 {
    color: #2c3e50;
    font-weight: bold;
}

h1 {
    margin-top: 1.5em;
    font-size: 200%;
    border-bottom: 2px solid #3498db;
    padding-bottom: 0.3em;
}

h2 {
    font-size: 180%;
    border-bottom: 1px solid #bdc3c7;
    padding-bottom: 0.2em;
}

h3 {
    font-size: 160%;
}

h4 {
    font-size: 150%;
}

h5, h6 {
    font-size: 125%;
}

/* Paragraphs */
p {
    margin-bottom: 1em;
}

/* Links */
a {
    color: #3498db;
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
pre {
    background-color: #f1f1f1;
    overflow-x: auto;
}

code {
    background-color: #f1f1f1;
    font-family: 'Adwaita Mono', 'Courier New', monospace;
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
    width: 100%;
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
