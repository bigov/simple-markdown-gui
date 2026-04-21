"""Master panel setup and hyperlink helpers for the editor-only layout."""

import os
from collections.abc import Callable
from typing import TYPE_CHECKING, cast

from PySide6.QtCore import QEvent, QObject, Qt, QUrl
from PySide6.QtGui import QCursor, QDesktopServices
from PySide6.QtWidgets import (
    QMainWindow,
    QMessageBox,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from filesystem import load_file_by_path
from markdown_rendering import render_markdown_with_styles
from markdown_roundtrip import preserve_roundtrip_markdown

if TYPE_CHECKING:
    from PySide6.QtGui import QAction
    from PySide6.QtWidgets import QToolBar


class MasterPanel:
    """Provides the central editor panel behavior for the main window."""

    panel_margin: int
    base_dir: str
    current_file_path: str | None
    editor: QTextEdit
    content_layout: QVBoxLayout
    content_widget: QWidget
    _original_markdown: str
    _editor_markdown: str
    _hovered_link: str

    if TYPE_CHECKING:
        toolbar: QToolBar
        preview_action: QAction
        _apply_panel_frame_style: Callable[[QWidget], None]
        on_editor_modification_changed: Callable[[bool], None]
        handle_save_action: Callable[[], None]
        update_save_action_state: Callable[[], None]
        _clear_link_status_if_needed: Callable[[], None]
        set_status_mode: Callable[[str], None]
        show_status_message: Callable[..., None]

    def _initialize_master_panel(self):
        self.editor = QTextEdit()
        self._apply_panel_frame_style(self.editor)

        self.editor.setCursor(Qt.CursorShape.IBeamCursor)
        self.editor.viewport().setCursor(Qt.CursorShape.IBeamCursor)
        self.editor.setMouseTracking(True)
        self.editor.viewport().setMouseTracking(True)
        event_filter = cast(QObject, self)
        self.editor.installEventFilter(event_filter)
        self.editor.viewport().installEventFilter(event_filter)
        self.editor.document().modificationChanged.connect(
            self.on_editor_modification_changed
        )

        self.content_layout = QVBoxLayout()
        self.content_layout.setContentsMargins(
            self.panel_margin,
            self.panel_margin,
            self.panel_margin,
            self.panel_margin,
        )
        self.content_layout.setSpacing(0)
        self.content_layout.addWidget(self.editor)

        self.content_widget = QWidget()
        self.content_widget.setLayout(self.content_layout)
        main_window = cast(QMainWindow, self)
        main_window.setCentralWidget(self.content_widget)

    def render_markdown(self, editor, markdown_text):
        render_markdown_with_styles(editor, markdown_text)

    def _set_markdown_cache(self, original_markdown, editor_markdown=None):
        self._original_markdown = original_markdown
        if editor_markdown is None:
            editor_markdown = original_markdown
        self._editor_markdown = editor_markdown

    def _set_editor_markdown(self, markdown_text):
        self._editor_markdown = markdown_text

    def get_editor_markdown_text(self):
        if not self.editor.document().isModified():
            return self._original_markdown

        if hasattr(self, "preview_action") and self.preview_action.isChecked():
            return self.editor.toPlainText()
        self._editor_markdown = self.get_visual_editor_markdown_text()
        return self._editor_markdown

    def get_visual_editor_markdown_text(self):
        return preserve_roundtrip_markdown(
            self._original_markdown, self.editor.toMarkdown()
        )

    def confirm_close_editor(self):
        if not self.editor.document().isModified():
            return True

        result = QMessageBox.question(
            cast(QWidget, self),
            "Сохранить изменения",
            "Текст был изменен. Сохранить изменения в исходный файл?",
            QMessageBox.StandardButton.Save
            | QMessageBox.StandardButton.Discard
            | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Save,
        )

        if result == QMessageBox.StandardButton.Cancel:
            return False

        if result == QMessageBox.StandardButton.Save:
            was_modified = self.editor.document().isModified()
            self.handle_save_action()
            if was_modified and self.editor.document().isModified():
                return False

        return True

    def eventFilter(self, obj, event):
        if obj == self.editor.viewport() and event.type() == QEvent.Type.MouseMove:
            link = self.editor.anchorAt(event.position().toPoint())
            if link:
                formatted_link = self._format_hover_link(link)
                self._hovered_link = formatted_link
                self.show_status_message(formatted_link)
            elif self._hovered_link:
                self._clear_link_status_if_needed()
            self._update_editor_link_cursor(link)
        if (
            obj == self.editor.viewport()
            and event.type() == QEvent.Type.MouseButtonRelease
            and event.button() == Qt.MouseButton.LeftButton
        ):
            link = self.editor.anchorAt(event.position().toPoint())
            if link:
                self._open_link_from_editor(link)
                return True
        if obj == self.editor.viewport() and event.type() == QEvent.Type.Leave:
            self._clear_link_status_if_needed()
            self._set_editor_cursor_shape(Qt.CursorShape.IBeamCursor)
        if obj == self.editor and event.type() == QEvent.Type.KeyPress:
            if event.key() == Qt.Key.Key_Escape:
                return self.confirm_close_editor()
        return QMainWindow.eventFilter(cast(QMainWindow, self), obj, event)

    def _set_editor_cursor_shape(self, cursor_shape):
        self.editor.setCursor(cursor_shape)
        self.editor.viewport().setCursor(cursor_shape)

    def _update_editor_link_cursor(self, link=None):
        if link is None:
            viewport_pos = self.editor.viewport().mapFromGlobal(QCursor.pos())
            link = self.editor.anchorAt(viewport_pos)

        if link:
            self._set_editor_cursor_shape(Qt.CursorShape.PointingHandCursor)
            return
        self._set_editor_cursor_shape(Qt.CursorShape.IBeamCursor)

    def _open_link_from_editor(self, link_text):
        url = self._resolve_link_url(link_text)
        if not url.isValid():
            return

        if self._is_internal_markdown_link(url):
            if not self.confirm_close_editor():
                return
            self._load_markdown_link_into_editor(url)
            return

        QDesktopServices.openUrl(url)

    def _resolve_link_url(self, link_text):
        url = QUrl(link_text)
        if url.scheme() == "file":
            return url
        if url.scheme():
            return url

        base_dir = (
            os.path.dirname(self.current_file_path)
            if self.current_file_path
            else os.getcwd()
        )
        path_part, _, fragment = link_text.partition("#")

        if path_part:
            local_path = os.path.abspath(os.path.join(base_dir, path_part))
        elif self.current_file_path:
            local_path = self.current_file_path
        else:
            local_path = os.path.abspath(base_dir)

        resolved_url = QUrl.fromLocalFile(local_path)
        if fragment:
            resolved_url.setFragment(fragment)
        return resolved_url

    def _is_internal_markdown_link(self, url):
        return url.scheme() == "file" and url.toLocalFile().lower().endswith(".md")

    def _load_markdown_link_into_editor(self, url):
        load_file_by_path(url.toLocalFile(), self)
        self.editor.setFocus()
        self._update_editor_link_cursor()

        is_source_mode = (
            hasattr(self, "preview_action") and self.preview_action.isChecked()
        )
        if url.hasFragment() and not is_source_mode:
            self.editor.scrollToAnchor(url.fragment())

    def _format_hover_link(self, link_text):
        if not link_text:
            return ""

        url = QUrl(link_text)
        if url.scheme() == "file":
            local_path = url.toLocalFile()
            if local_path:
                formatted_link = os.path.abspath(local_path)
                if url.hasFragment():
                    formatted_link = f"{formatted_link}#{url.fragment()}"
                return self._format_link_relative_to_base_dir(formatted_link)

        if url.scheme():
            return link_text

        base_dir = (
            os.path.dirname(self.current_file_path)
            if self.current_file_path
            else os.getcwd()
        )
        path_part, separator, fragment = link_text.partition("#")

        if path_part:
            formatted_link = os.path.abspath(os.path.join(base_dir, path_part))
        elif self.current_file_path:
            formatted_link = self.current_file_path
        else:
            formatted_link = link_text

        if separator:
            formatted_link = f"{formatted_link}#{fragment}"
        return self._format_link_relative_to_base_dir(formatted_link)

    def _format_link_relative_to_base_dir(self, link_text):
        path_part, separator, fragment = link_text.partition("#")
        try:
            common_path = os.path.commonpath(
                [os.path.abspath(path_part), self.base_dir]
            )
        except ValueError:
            return link_text

        if common_path != self.base_dir:
            return link_text

        relative_path = os.path.relpath(path_part, self.base_dir)
        if separator:
            return f"{relative_path}#{fragment}"
        return relative_path
