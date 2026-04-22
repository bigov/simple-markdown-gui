"""Menu bar creation helpers."""

import configparser
import os
import pathlib

from PySide6.QtCore import QItemSelectionModel
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import QFileDialog, QInputDialog, QMessageBox, QLineEdit

from config import AppConfig


def _current_directory(window):
    """Return the working directory based on sidebar selection or open file."""
    if (
        hasattr(window, "current_sidebar_directory")
        and window.current_sidebar_directory
    ):
        return window.current_sidebar_directory
    if window.current_file_path:
        return os.path.dirname(window.current_file_path)
    if hasattr(window, "base_dir"):
        return window.base_dir
    return os.getcwd()


def _selected_sidebar_item(window):
    """Return selected sidebar path info as (path, is_dir) or (None, False)."""
    if not hasattr(window, "sidebar") or not hasattr(window, "file_model"):
        return None, False

    current_index = window.sidebar.currentIndex()
    if not current_index.isValid():
        return None, False

    selected_path = window.file_model.filePath(current_index)
    if not selected_path:
        return None, False

    return selected_path, window.file_model.isDir(current_index)


def _is_empty_directory(path):
    """Return True when path exists, is directory, and has no entries."""
    directory = pathlib.Path(path)
    return directory.is_dir() and not any(directory.iterdir())


def _select_sidebar_path(window, abs_path):
    """Select the provided absolute path in sidebar if model can resolve it."""
    file_index = window.file_model.index(abs_path)
    if file_index.isValid():
        window.sidebar.setCurrentIndex(file_index)
        window.sidebar.selectionModel().select(
            file_index,
            QItemSelectionModel.SelectionFlag.ClearAndSelect,
        )


def rename_selected_item(window):
    """Rename selected file or directory from the sidebar."""
    selected_path, _is_dir = _selected_sidebar_item(window)
    if not selected_path:
        QMessageBox.information(
            window,
            "Rename",
            "Select a file or folder in the file panel.",
        )
        return

    source_path = pathlib.Path(selected_path)
    current_name = source_path.name

    new_name, ok = QInputDialog.getText(
        window,
        "Rename",
        "New name:",
        QLineEdit.EchoMode.Normal,
        current_name,
    )
    if not ok:
        return

    new_name = new_name.strip()
    if not new_name or new_name == current_name:
        return

    if pathlib.PurePath(new_name).name != new_name:
        QMessageBox.warning(
            window,
            "Invalid name",
            "The name must not contain path separators.",
        )
        return

    target_path = source_path.with_name(new_name)
    if target_path.exists():
        QMessageBox.warning(
            window,
            "Item already exists",
            f'An item named "{new_name}" already exists in this folder.',
        )
        return

    try:
        source_path.rename(target_path)
    except OSError as exc:
        QMessageBox.critical(
            window,
            "Rename error",
            f"Could not rename item:\n{exc}",
        )
        return

    old_abs_path = str(source_path.resolve())
    new_abs_path = str(target_path.resolve())

    if getattr(window, "current_file_path", None) == old_abs_path:
        window.current_file_path = new_abs_path
        if hasattr(window, "notify_current_file_changed"):
            window.notify_current_file_changed()

    if getattr(window, "current_sidebar_directory", None):
        sidebar_dir = pathlib.Path(window.current_sidebar_directory)
        try:
            relative = sidebar_dir.relative_to(source_path)
            window.current_sidebar_directory = str(target_path / relative)
        except ValueError:
            if sidebar_dir == source_path:
                window.current_sidebar_directory = new_abs_path

    _select_sidebar_path(window, new_abs_path)


def delete_selected_empty_directory(window):
    """Delete the selected directory only when it is empty."""
    selected_path, is_dir = _selected_sidebar_item(window)
    if not selected_path or not is_dir:
        QMessageBox.information(
            window,
            "Delete folder",
            "Select a folder in the file panel.",
        )
        return

    if not _is_empty_directory(selected_path):
        QMessageBox.information(
            window,
            "Delete folder",
            "The folder is not empty and cannot be deleted.",
        )
        return

    dir_path = pathlib.Path(selected_path)
    answer = QMessageBox.question(
        window,
        "Confirm deletion",
        f'Delete empty folder "{dir_path.name}"?',
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        QMessageBox.StandardButton.No,
    )
    if answer != QMessageBox.StandardButton.Yes:
        return

    try:
        dir_path.rmdir()
    except OSError as exc:
        QMessageBox.critical(
            window,
            "Delete error",
            f"Could not delete folder:\n{exc}",
        )
        return

    parent_dir = str(dir_path.parent.resolve())
    window.current_sidebar_directory = parent_dir
    _select_sidebar_path(window, parent_dir)


def update_file_menu_actions_state(window):
    """Enable or disable file menu actions based on current sidebar selection."""
    selected_path, is_dir = _selected_sidebar_item(window)
    has_selection = bool(selected_path)

    if hasattr(window, "rename_item_action"):
        window.rename_item_action.setEnabled(has_selection)

    can_delete_empty_dir = (
        has_selection and is_dir and _is_empty_directory(selected_path)
    )
    if hasattr(window, "delete_empty_dir_action"):
        window.delete_empty_dir_action.setEnabled(can_delete_empty_dir)


def delete_current_file(window):
    """Delete the currently open file after user confirmation."""
    file_path = window.current_file_path
    if not file_path:
        QMessageBox.information(window, "Delete file", "No open file.")
        return

    file_name = os.path.basename(file_path)
    answer = QMessageBox.question(
        window,
        "Confirm deletion",
        f'Delete file "{file_name}"?\n\nThis action cannot be undone.',
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        QMessageBox.StandardButton.No,
    )
    if answer != QMessageBox.StandardButton.Yes:
        return

    try:
        os.remove(file_path)
    except OSError as exc:
        QMessageBox.critical(window, "Delete error", f"Could not delete file:\n{exc}")
        return

    window.current_file_path = None
    window.editor.clear()
    window.editor.document().setModified(False)
    if hasattr(window, "update_save_action_state"):
        window.update_save_action_state()
    if hasattr(window, "notify_current_file_changed"):
        window.notify_current_file_changed()


def create_file_in_current_directory(window):
    """Create a new file in the directory of the currently open file."""
    directory = _current_directory(window)

    name, ok = QInputDialog.getText(
        window,
        "Create file",
        "New file name:",
    )
    if not ok or not name.strip():
        return

    name = name.strip()
    file_path = pathlib.Path(directory) / name

    if file_path.exists():
        QMessageBox.warning(
            window,
            "File already exists",
            f'A file named "{name}" already exists in this folder.',
        )
        return

    try:
        initial_content = f"# {file_path.stem}\nFile content ...\n"
        file_path.write_text(initial_content, encoding="utf-8")
    except OSError as exc:
        QMessageBox.critical(
            window, "Create file error", f"Could not create file:\n{exc}"
        )
        return

    abs_path = str(file_path.resolve())
    if hasattr(window, "load_file_by_path_fn"):
        window.load_file_by_path_fn(abs_path)
    else:
        from filesystem import (
            load_file_by_path,
        )

        load_file_by_path(abs_path, window)

    file_index = window.file_model.index(abs_path)
    if file_index.isValid():
        window.sidebar.setCurrentIndex(file_index)
        window.sidebar.selectionModel().select(
            file_index,
            QItemSelectionModel.SelectionFlag.ClearAndSelect,
        )
        window.current_sidebar_directory = os.path.dirname(abs_path)


def create_subdirectory_in_current_directory(window):
    """Create a new subdirectory in the directory of the currently open file."""
    directory = _current_directory(window)

    name, ok = QInputDialog.getText(
        window,
        "Create folder",
        "New folder name:",
    )
    if not ok or not name.strip():
        return

    name = name.strip()
    dir_path = pathlib.Path(directory) / name

    if dir_path.exists():
        QMessageBox.warning(
            window,
            "Folder already exists",
            f'A folder named "{name}" already exists in this folder.',
        )
        return

    try:
        dir_path.mkdir()
    except OSError as exc:
        QMessageBox.critical(
            window, "Create folder error", f"Could not create folder:\n{exc}"
        )


def open_markdown_file(window):
    """Open a markdown file and persist its directory as configured base_dir."""
    start_directory = _current_directory(window)

    file_path, _ = QFileDialog.getOpenFileName(
        window,
        "Open Markdown",
        start_directory,
        "Markdown Files (*.md);;All Files (*)",
    )
    if not file_path:
        return

    if hasattr(window, "confirm_close_editor") and not window.confirm_close_editor():
        return

    abs_path = os.path.abspath(file_path)
    base_dir = os.path.dirname(abs_path)

    if hasattr(window, "file_model") and hasattr(window, "sidebar"):
        root_index = window.file_model.setRootPath(base_dir)
        window.sidebar.setRootIndex(root_index)

    if hasattr(window, "load_file_by_path_fn"):
        window.load_file_by_path_fn(abs_path)
    else:
        from filesystem import (
            load_file_by_path,
        )

        load_file_by_path(abs_path, window)

    window.base_dir = base_dir
    window.current_sidebar_directory = base_dir

    try:
        config = configparser.ConfigParser()
        config.read(window.config_path)
        if not config.has_section(window.config_section_name):
            config.add_section(window.config_section_name)
        config.set(window.config_section_name, "base_dir", base_dir)
        window.config_path = AppConfig.write_config(config)
    except OSError as exc:
        QMessageBox.warning(
            window,
            "Open file",
            f"The file was opened, but base_dir could not be saved:\n{exc}",
        )


def create_menu_bar(window):
    """Create and attach the main application menu bar."""
    file_menu = window.menuBar().addMenu("&File")

    window.open_action = QAction("Open", window)
    window.open_action.setShortcut(QKeySequence.StandardKey.Open)
    window.open_action.triggered.connect(lambda: open_markdown_file(window))
    file_menu.addAction(window.open_action)

    file_menu.addAction(window.save_action)

    file_menu.addSeparator()

    window.new_file_action = QAction("New file", window)
    window.new_file_action.triggered.connect(
        lambda: create_file_in_current_directory(window)
    )
    file_menu.addAction(window.new_file_action)

    window.new_dir_action = QAction("New folder", window)
    window.new_dir_action.triggered.connect(
        lambda: create_subdirectory_in_current_directory(window)
    )
    file_menu.addAction(window.new_dir_action)

    window.rename_item_action = QAction("Rename", window)
    window.rename_item_action.triggered.connect(lambda: rename_selected_item(window))
    file_menu.addAction(window.rename_item_action)

    file_menu.addSeparator()

    window.delete_file_action = QAction("Delete file", window)
    window.delete_file_action.triggered.connect(lambda: delete_current_file(window))
    file_menu.addAction(window.delete_file_action)

    window.delete_empty_dir_action = QAction("Delete folder", window)
    window.delete_empty_dir_action.triggered.connect(
        lambda: delete_selected_empty_directory(window)
    )
    file_menu.addAction(window.delete_empty_dir_action)

    window.exit_action = QAction("Exit", window)
    window.exit_action.setShortcut(QKeySequence.StandardKey.Quit)
    window.exit_action.triggered.connect(window.close)
    file_menu.addSeparator()
    file_menu.addAction(window.exit_action)

    file_menu.aboutToShow.connect(lambda: update_file_menu_actions_state(window))

    window.edit_menu = window.menuBar().addMenu("&Edit")
    window.edit_menu.addAction(window.preview_action)
    window.edit_menu.addSeparator()
    window.edit_menu.addAction(window.bold_action)
    window.edit_menu.addAction(window.underline_action)
    window.edit_menu.addAction(window.italic_action)
    window.edit_menu.addAction(window.strikethrough_action)

    view_menu = window.menuBar().addMenu("&View")
    view_menu.addAction(window.sidebar_dock.toggleViewAction())
    view_menu.addAction(window.toolbar.toggleViewAction())

    help_menu = window.menuBar().addMenu("&Help")
    window.about_action = QAction("About", window)
    window.about_action.triggered.connect(window.show_about_dialog)
    help_menu.addAction(window.about_action)
