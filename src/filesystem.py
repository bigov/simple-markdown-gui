"""File loading and saving helpers for the application."""

import os
from PySide6.QtWidgets import QFileDialog
from PySide6.QtCore import QItemSelectionModel

from markdown_rendering import render_markdown_with_styles


def _files_view(widget):
    panel = getattr(widget, "files_panel", None)
    if panel is not None:
        return panel.files
    return getattr(widget, "files", None)


def _file_model(widget):
    panel = getattr(widget, "files_panel", None)
    if panel is not None:
        return panel.model
    return getattr(widget, "file_model", None)


def _to_proxy_index(widget, model_index):
    """Convert source file model index to files model index when proxy is used."""
    if hasattr(widget, "files_panel") and widget.files_panel.proxy_model is not None:
        return widget.files_panel.proxy_model.mapFromSource(model_index)
    if hasattr(widget, "files_proxy_model") and widget.files_proxy_model is not None:
        return widget.files_proxy_model.mapFromSource(model_index)
    return model_index


def write_text_to_file(file_path, text):
    # Keep line endings from the produced markdown text unchanged.
    with open(file_path, "w", encoding="utf-8", newline="") as file:
        file.write(text)


def _get_markdown_text(widget):
    if hasattr(widget, "get_editor_markdown_text"):
        return widget.get_editor_markdown_text()
    return widget.editor.toMarkdown()


def _save_markdown_to_path(widget, file_path, update_current_file=False):
    markdown_text = _get_markdown_text(widget)
    write_text_to_file(file_path, markdown_text)

    if update_current_file:
        widget.current_file_path = file_path
        if hasattr(widget, "_set_markdown_cache"):
            getattr(widget, "_set_markdown_cache")(markdown_text, markdown_text)
        else:
            setattr(widget, "_original_markdown", markdown_text)
            setattr(widget, "_editor_markdown", markdown_text)
        if hasattr(widget, "notify_current_file_changed"):
            widget.notify_current_file_changed()

    return True


def _display_file(file_path, widget):
    file_path = os.path.abspath(file_path)

    try:
        with open(file_path, "r", encoding="utf-8", newline="") as f:
            text = f.read()

        widget.current_file_path = file_path
        if hasattr(widget, "_set_markdown_cache"):
            getattr(widget, "_set_markdown_cache")(text, text)
        else:
            setattr(widget, "_original_markdown", text)
            setattr(widget, "_editor_markdown", text)
        if hasattr(widget, "notify_current_file_changed"):
            widget.notify_current_file_changed()

        is_source_mode = (
            hasattr(widget, "preview_action") and widget.preview_action.isChecked()
        )

        if file_path.endswith(".md") and not is_source_mode:
            render_markdown_with_styles(widget.editor, text)
            if hasattr(widget, "set_status_mode"):
                widget.set_status_mode("Режим форматированного редактирования")
        else:
            widget.editor.setPlainText(text)
            if hasattr(widget, "set_status_mode") and file_path.endswith(".md"):
                widget.set_status_mode("Режим исходного текста")

        widget.editor.document().setModified(False)
        if hasattr(widget, "update_save_action_state"):
            widget.update_save_action_state()

        os.chdir(os.path.dirname(file_path))

        file_model = _file_model(widget)
        files_view = _files_view(widget)
        if file_model is None or files_view is None:
            return

        file_index = file_model.index(file_path)
        if file_index.isValid():
            files_index = _to_proxy_index(widget, file_index)
            if not files_index.isValid():
                return

            files_view.setCurrentIndex(files_index)
            files_view.selectionModel().select(
                files_index,
                QItemSelectionModel.SelectionFlag.ClearAndSelect,
            )
            files_view.scrollTo(files_index)
    except (OSError, UnicodeError) as error:
        print(f"Error loading file: {error}")


def load_file(file_model, index, widget):
    """Load and display a file in the editor.

    Args:
        file_model: The file system model
        index: The model index of the file to load
        widget: The main widget containing the editor
    """
    if file_model.isDir(index):
        return

    _display_file(file_model.filePath(index), widget)


def load_file_by_path(file_path, widget):
    """Load and display a file by its path in the editor.

    Args:
        file_path: The absolute path to the file to load
        widget: The main widget containing the editor
    """
    _display_file(file_path, widget)


def save_md(widget):
    """Save markdown content to a file.

    Args:
        widget: The main widget containing the editor
    """
    file_path, _ = QFileDialog.getSaveFileName(
        widget, "Save Markdown", "", "Markdown Files (*.md);;All Files (*)"
    )
    if not file_path:
        return

    if not file_path.lower().endswith(".md"):
        file_path += ".md"

    _save_markdown_to_path(widget, file_path)


def save_current_file(widget):
    file_path = getattr(widget, "current_file_path", None)
    if not file_path:
        return False

    return _save_markdown_to_path(widget, file_path, update_current_file=True)
