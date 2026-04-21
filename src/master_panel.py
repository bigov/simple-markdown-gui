"""Master panel setup and mode switching helpers."""

import os
from collections.abc import Callable
from typing import TYPE_CHECKING

from PySide6.QtCore import QEvent, Qt, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QMainWindow, QMessageBox, QTextBrowser, QTextEdit, QVBoxLayout, QWidget

from filesystem import load_file_by_path
from markdown_rendering import render_markdown_with_styles
from markdown_roundtrip import preserve_roundtrip_markdown
from toolbar import toggle_preview

if TYPE_CHECKING:
    from PySide6.QtGui import QAction
    from PySide6.QtWidgets import QToolBar

    class MasterPanelBase(QMainWindow):
        """Type-checking base so Pylance sees QMainWindow APIs on the mixin."""
else:
    class MasterPanelBase:
        """Runtime-only empty base to keep the mixin hierarchy lightweight."""


class MasterPanelMixin(MasterPanelBase):
    """Encapsulates the central browser/editor area for the main window.

    There are two MasterPanel* classes on purpose:
    - MasterPanelBase is a tiny compatibility layer for static analysis.
    - MasterPanelMixin contains the actual shared panel behavior used by MyApp.

    During type checking, MasterPanelBase inherits from QMainWindow so Pylance
    understands Qt methods like setCentralWidget and eventFilter. At runtime,
    MasterPanelBase is an empty class, which keeps the multiple-inheritance chain
    simple and avoids changing application behavior.
    """

    panel_margin: int
    base_dir: str
    current_file_path: str | None
    current_editor: QTextBrowser | QTextEdit
    browser: QTextBrowser
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
        self.browser = QTextBrowser()
        self.editor = QTextEdit()
        self._apply_panel_frame_style(self.browser)
        self._apply_panel_frame_style(self.editor)
        self.current_editor = self.browser

        self.browser.setCursor(Qt.CursorShape.ArrowCursor)
        self.browser.viewport().setCursor(Qt.CursorShape.ArrowCursor)
        self.browser.setMouseTracking(True)
        self.browser.viewport().setMouseTracking(True)
        self.browser.setOpenExternalLinks(False)
        self.browser.setOpenLinks(False)
        self.browser.anchorClicked.connect(self.open_link)
        self.browser.highlighted.connect(self.on_link_highlighted)
        self.browser.viewport().installEventFilter(self)

        self.editor.setCursor(Qt.CursorShape.IBeamCursor)
        self.editor.viewport().setCursor(Qt.CursorShape.IBeamCursor)
        self.editor.installEventFilter(self)
        self.editor.document().modificationChanged.connect(self.on_editor_modification_changed)

        self.content_layout = QVBoxLayout()
        self.content_layout.setContentsMargins(
            self.panel_margin,
            self.panel_margin,
            self.panel_margin,
            self.panel_margin,
        )
        self.content_layout.setSpacing(0)
        self.content_layout.addWidget(self.browser)

        self.content_widget = QWidget()
        self.content_widget.setLayout(self.content_layout)
        self.setCentralWidget(self.content_widget)

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

        if hasattr(self, 'preview_action') and self.preview_action.isChecked():
            return self.editor.toPlainText()
        self._editor_markdown = self.get_visual_editor_markdown_text()
        return self._editor_markdown

    def get_visual_editor_markdown_text(self):
        return preserve_roundtrip_markdown(self._original_markdown, self.editor.toMarkdown())

    def confirm_close_editor(self):
        if not self.editor.document().isModified():
            self.switch_to_browse(self._original_markdown)
            return True

        result = QMessageBox.question(
            self,
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
            if self.current_editor != self.editor:
                return False

            was_modified = self.editor.document().isModified()
            self.handle_save_action()
            if was_modified and self.editor.document().isModified():
                return False

        self.switch_to_browse(self._original_markdown)
        return True

    def switch_to_edit(self, event):
        self.content_layout.removeWidget(self.browser)
        self.browser.hide()
        self.content_layout.addWidget(self.editor)

        if hasattr(self, '_original_markdown'):
            self._editor_markdown = self._original_markdown
            self.editor.setMarkdown(self._original_markdown)

        self.editor.show()
        self.editor.setFocus()
        self.current_editor = self.editor
        self.toolbar.show()

        if hasattr(self, 'preview_action'):
            self.preview_action.setChecked(False)
        self.set_status_mode("Режим форматированного редактирования")

        self.editor.document().setModified(False)
        self.update_save_action_state()

        event.accept()

    def switch_to_browse(self, markdown_text=None):
        if markdown_text is None:
            markdown_text = self._original_markdown

        self.content_layout.removeWidget(self.editor)
        self.editor.hide()
        self.content_layout.addWidget(self.browser)
        self.render_markdown(self.browser, markdown_text)
        self.current_editor = self.browser
        self.browser.show()
        self.browser.setFocus()
        self.toolbar.hide()
        self.editor.document().setModified(False)
        self.update_save_action_state()
        self._clear_link_status_if_needed()
        self.set_status_mode("Режим просмотра")

        if hasattr(self, 'preview_action'):
            self.preview_action.setChecked(False)

    def eventFilter(self, obj, event):
        if obj == self.browser.viewport() and event.type() == QEvent.Type.MouseButtonDblClick:
            self.switch_to_edit(event)
            return True
        if obj == self.browser.viewport() and event.type() == QEvent.Type.MouseMove:
            link = self.browser.anchorAt(event.position().toPoint())
            if link:
                formatted_link = self._format_hover_link(link)
                self._hovered_link = formatted_link
                self.show_status_message(formatted_link)
            elif self._hovered_link:
                self._clear_link_status_if_needed()
        if obj == self.browser.viewport() and event.type() == QEvent.Type.Leave:
            self._clear_link_status_if_needed()
        if obj == self.editor and event.type() == QEvent.Type.KeyPress:
            if event.key() == Qt.Key.Key_Escape:
                if hasattr(self, 'preview_action') and self.preview_action.isChecked():
                    self.preview_action.setChecked(False)
                    toggle_preview(self, self.preview_action)
                    return True
                return self.confirm_close_editor()
        return super().eventFilter(obj, event)

    def on_link_highlighted(self, link):
        if self.current_editor != self.browser:
            return

        if isinstance(link, QUrl):
            link_text = link.toString()
        else:
            link_text = str(link)

        if link_text:
            formatted_link = self._format_hover_link(link_text)
            self._hovered_link = formatted_link
            self.show_status_message(formatted_link)
        else:
            self._clear_link_status_if_needed()

    def open_link(self, url):
        if url.scheme() == '':
            url = QUrl.fromLocalFile(url.toString())

        if url.scheme() == 'file' and url.toLocalFile().endswith('.md'):
            load_file_by_path(url.toLocalFile(), self)
        else:
            QDesktopServices.openUrl(url)

    def _format_hover_link(self, link_text):
        if not link_text:
            return ""

        url = QUrl(link_text)
        if url.scheme() == 'file':
            local_path = url.toLocalFile()
            if local_path:
                formatted_link = os.path.abspath(local_path)
                if url.hasFragment():
                    formatted_link = f"{formatted_link}#{url.fragment()}"
                return self._format_link_relative_to_base_dir(formatted_link)

        if url.scheme():
            return link_text

        base_dir = os.path.dirname(self.current_file_path) if self.current_file_path else os.getcwd()
        path_part, separator, fragment = link_text.partition('#')

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
        path_part, separator, fragment = link_text.partition('#')
        try:
            common_path = os.path.commonpath([os.path.abspath(path_part), self.base_dir])
        except ValueError:
            return link_text

        if common_path != self.base_dir:
            return link_text

        relative_path = os.path.relpath(path_part, self.base_dir)
        if separator:
            return f"{relative_path}#{fragment}"
        return relative_path