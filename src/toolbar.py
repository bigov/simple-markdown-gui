"""Toolbar creation and editing actions."""

from PySide6.QtGui import QAction, QFont, QKeySequence, QTextCharFormat
from PySide6.QtWidgets import QToolBar

from markdown_rendering import render_markdown_with_styles


def create_toolbar(widget):
    toolbar = QToolBar("Edit toolbar", widget)

    save_action = QAction("Save", widget)
    save_action.setEnabled(False)
    save_action.triggered.connect(widget.handle_save_action)
    toolbar.addAction(save_action)
    widget.save_action = save_action

    preview_action = QAction("Source", widget)
    preview_action.setCheckable(True)
    preview_action.triggered.connect(lambda: toggle_preview(widget, preview_action))
    toolbar.addAction(preview_action)
    widget.preview_action = preview_action  # Store reference for external access

    bold_action = QAction("Bold", widget)
    bold_action.setShortcut(QKeySequence.StandardKey.Bold)
    bold_action.triggered.connect(lambda: toggle_bold(widget))
    toolbar.addAction(bold_action)
    widget.addAction(bold_action)
    widget.editor.addAction(bold_action)
    widget.bold_action = bold_action  # Store reference for external access

    underline_action = QAction("Underline", widget)
    underline_action.setShortcut(QKeySequence.StandardKey.Underline)
    underline_action.triggered.connect(lambda: toggle_underline(widget))
    toolbar.addAction(underline_action)
    widget.addAction(underline_action)
    widget.editor.addAction(underline_action)
    widget.underline_action = underline_action  # Store reference for external access

    italic_action = QAction("Italic", widget)
    italic_action.setShortcut(QKeySequence.StandardKey.Italic)
    italic_action.triggered.connect(lambda: toggle_italic(widget))
    toolbar.addAction(italic_action)
    widget.addAction(italic_action)
    widget.editor.addAction(italic_action)
    widget.italic_action = italic_action  # Store reference for external access

    strikethrough_action = QAction("Strikethrough", widget)
    strikethrough_action.triggered.connect(lambda: toggle_strikethrough(widget))
    toolbar.addAction(strikethrough_action)
    widget.addAction(strikethrough_action)
    widget.editor.addAction(strikethrough_action)
    widget.strikethrough_action = (
        strikethrough_action  # Store reference for external access
    )

    return toolbar


def toggle_bold(widget):
    cursor = widget.editor.textCursor()
    if not cursor.hasSelection():
        return

    selected_format = cursor.charFormat()
    new_format = QTextCharFormat(selected_format)
    if selected_format.fontWeight() == QFont.Weight.Bold:
        new_format.setFontWeight(QFont.Weight.Normal)
    else:
        new_format.setFontWeight(QFont.Weight.Bold)

    cursor.mergeCharFormat(new_format)
    widget.editor.mergeCurrentCharFormat(new_format)


def toggle_underline(widget):
    cursor = widget.editor.textCursor()
    if not cursor.hasSelection():
        return

    selected_format = cursor.charFormat()
    new_format = QTextCharFormat(selected_format)
    new_format.setFontUnderline(not selected_format.fontUnderline())

    cursor.mergeCharFormat(new_format)
    widget.editor.mergeCurrentCharFormat(new_format)


def toggle_italic(widget):
    cursor = widget.editor.textCursor()
    if not cursor.hasSelection():
        return

    selected_format = cursor.charFormat()
    new_format = QTextCharFormat(selected_format)
    new_format.setFontItalic(not selected_format.fontItalic())

    cursor.mergeCharFormat(new_format)
    widget.editor.mergeCurrentCharFormat(new_format)


def toggle_strikethrough(widget):
    cursor = widget.editor.textCursor()
    if not cursor.hasSelection():
        return

    selected_format = cursor.charFormat()
    new_format = QTextCharFormat(selected_format)
    new_format.setFontStrikeOut(not selected_format.fontStrikeOut())

    cursor.mergeCharFormat(new_format)
    widget.editor.mergeCurrentCharFormat(new_format)


def _set_format_actions_enabled(widget, enabled):
    for action_name in (
        "bold_action",
        "underline_action",
        "italic_action",
        "strikethrough_action",
    ):
        if hasattr(widget, action_name):
            getattr(widget, action_name).setEnabled(enabled)


def _cache_editor_markdown(widget, markdown_text):
    if hasattr(widget, "_set_editor_markdown"):
        getattr(widget, "_set_editor_markdown")(markdown_text)
    else:
        setattr(widget, "_editor_markdown", markdown_text)


def toggle_preview(widget, action):
    was_modified = widget.editor.document().isModified()

    if action.isChecked():
        # Keep exact source markdown when no visual edits were made,
        # avoiding Qt toMarkdown() normalization side effects.
        if not was_modified and hasattr(widget, "_original_markdown"):
            markdown_text = widget._original_markdown
        elif hasattr(widget, "get_visual_editor_markdown_text"):
            markdown_text = widget.get_visual_editor_markdown_text()
        else:
            markdown_text = widget.editor.toMarkdown()
        _cache_editor_markdown(widget, markdown_text)
        widget.editor.setPlainText(markdown_text)
        _set_format_actions_enabled(widget, False)
        if hasattr(widget, "set_status_mode"):
            widget.set_status_mode("Режим исходного текста")
    else:
        if hasattr(widget, "_original_markdown"):
            markdown_text = widget.editor.toPlainText()
            _cache_editor_markdown(widget, markdown_text)
            render_markdown_with_styles(widget.editor, markdown_text)
        _set_format_actions_enabled(widget, True)
        if hasattr(widget, "set_status_mode"):
            widget.set_status_mode("Режим форматированного редактирования")

    widget.editor.document().setModified(was_modified)
    if hasattr(widget, "update_save_action_state"):
        widget.update_save_action_state()
