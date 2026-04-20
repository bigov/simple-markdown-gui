import configparser
import sys
import os

from app_paths import AppPaths
from markdown_rendering import render_markdown_with_styles
from markdown_roundtrip import preserve_roundtrip_markdown

from PySide6.QtCore import QEvent, Qt, QUrl, Slot
from PySide6.QtGui import QCloseEvent, QDesktopServices
from PySide6.QtWidgets import QApplication, QMessageBox, QTextBrowser, QTextEdit, QVBoxLayout, QSplitter, QWidget

from toolbar import create_toolbar
from sidebar import create_sidebar
from filesystem import load_file, load_file_by_path, save_current_file


class MyWidget(QWidget):
    config_dir = AppPaths.config_dir

    def __init__(self):
        QWidget.__init__(self)
        self.config_path = AppPaths.get_config_path()
        self.browser = QTextBrowser()
        self.editor = QTextEdit()
        self.current_editor = self.browser
        self.current_file_path = None
        self._original_markdown = ""  # Store original markdown when in preview mode
        self._editor_markdown = ""

        self.browser.setCursor(Qt.ArrowCursor)
        self.browser.viewport().setCursor(Qt.ArrowCursor)
        self.browser.setOpenExternalLinks(False)  # Disable automatic link opening
        self.browser.setOpenLinks(False)  # Disable automatic link opening
        self.browser.anchorClicked.connect(self.open_link)  # Connect to custom handler
        self.browser.viewport().installEventFilter(self)

        self.editor.setCursor(Qt.IBeamCursor)
        self.editor.viewport().setCursor(Qt.IBeamCursor)
        self.editor.installEventFilter(self)
        self.editor.document().modificationChanged.connect(self.on_editor_modification_changed)

        self.toolbar = create_toolbar(self)

        # Load window size and base dir from config
        config = configparser.ConfigParser()
        config.read(self.config_path)

        if 'Window' in config:
            width = config.getint('Window', 'width', fallback=800)
            height = config.getint('Window', 'height', fallback=600)
            self.resize(width, height)
        
        base_dir = './'        
        if 'Default' in config:
            base_dir = config.get('Default', 'base_dir', fallback='./')

        # Create sidebar with file browser
        self.sidebar, self.file_model = create_sidebar(base_dir)
        self.sidebar.clicked.connect(self.on_sidebar_clicked)
        
        panel_margin = 4
        panel_spacing = 4

        # Create main content layout
        self.content_layout = QVBoxLayout()
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.setSpacing(panel_spacing)
        self.content_layout.addWidget(self.toolbar)
        self.content_layout.addWidget(self.browser)

        self.content_widget = QWidget()
        self.content_widget.setLayout(self.content_layout)

        # Create main horizontal layout for panels
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(panel_margin, panel_margin, panel_margin, panel_margin)
        self.layout.setSpacing(0)

        self.panel_splitter = QSplitter(Qt.Horizontal)
        self.panel_splitter.setChildrenCollapsible(False)
        self.panel_splitter.setHandleWidth(panel_spacing)
        self.panel_splitter.addWidget(self.sidebar)
        self.panel_splitter.addWidget(self.content_widget)
        self.panel_splitter.setStretchFactor(0, 1)
        self.panel_splitter.setStretchFactor(1, 2)

        try:
            saved_sidebar_width = config.getint('Panels', 'sidebar_width', fallback=0)
            saved_content_width = config.getint('Panels', 'content_width', fallback=0)
        except ValueError:
            saved_sidebar_width = 0
            saved_content_width = 0
        if saved_sidebar_width > 0 and saved_content_width > 0:
            self.panel_splitter.setSizes([saved_sidebar_width, saved_content_width])
        else:
            self.panel_splitter.setSizes([1, 2])

        self.layout.addWidget(self.panel_splitter)
        
        # Hide toolbar initially (show only in edit mode)
        self.toolbar.hide()

        startup_file = os.path.join(os.path.abspath(base_dir), 'index.md')
        if os.path.isfile(startup_file):
            load_file_by_path(startup_file, self)

    def on_sidebar_clicked(self, index):
        """Handle sidebar file selection."""
        if self.current_editor == self.editor and not self.confirm_close_editor():
            return
        load_file(self.file_model, index, self)

    def render_markdown(self, editor, markdown_text):
        render_markdown_with_styles(editor, markdown_text)

    def update_save_action_state(self):
        if hasattr(self, 'save_action'):
            self.save_action.setEnabled(
                self.current_editor == self.editor
                and self.editor.document().isModified()
                and bool(self.current_file_path)
            )

    def on_editor_modification_changed(self, _modified):
        self.update_save_action_state()

    def handle_save_action(self):
        try:
            if not save_current_file(self):
                QMessageBox.warning(self, "Ошибка сохранения", "Не удалось определить исходный файл для сохранения.")
                return
        except OSError as error:
            QMessageBox.warning(self, "Ошибка сохранения", f"Не удалось сохранить файл:\n{error}")
            return

        self.editor.document().setModified(False)
        self.update_save_action_state()

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
            QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel,
            QMessageBox.Save,
        )

        if result == QMessageBox.Cancel:
            return False

        if result == QMessageBox.Save:
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
        
        # Load the markdown document directly to keep round-trip saving stable.
        if hasattr(self, '_original_markdown'):
            self._editor_markdown = self._original_markdown
            self.editor.setMarkdown(self._original_markdown)
        
        self.editor.show()
        self.editor.setFocus()
        self.current_editor = self.editor
        self.toolbar.show()
        
        # Reset source mode when switching to edit (show preview by default)
        if hasattr(self, 'preview_action'):
            self.preview_action.setChecked(False)

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
        
        # Reset source mode when switching to browse
        if hasattr(self, 'preview_action'):
            self.preview_action.setChecked(False)

    def eventFilter(self, obj, event):
        if obj == self.browser.viewport() and event.type() == QEvent.MouseButtonDblClick:
            self.switch_to_edit(event)
            return True
        if obj == self.editor and event.type() == QEvent.KeyPress:
            if event.key() == Qt.Key_Escape:
                # If source mode is active, switch back to preview
                if hasattr(self, 'preview_action') and self.preview_action.isChecked():
                    self.preview_action.setChecked(False)
                    # Trigger the toggle_preview function to switch back to HTML
                    from toolbar import toggle_preview
                    toggle_preview(self, self.preview_action)
                    return True
                else:
                    # Otherwise, switch to browse mode
                    return self.confirm_close_editor()
        return super().eventFilter(obj, event)

    def closeEvent(self, event: QCloseEvent):
        # Save window and panel sizes to config
        config = configparser.ConfigParser()
        config.read(self.config_path)
        if not config.has_section('Window'):
            config.add_section('Window')
        config.set('Window', 'width', str(self.width()))
        config.set('Window', 'height', str(self.height()))

        if not config.has_section('Panels'):
            config.add_section('Panels')
        sidebar_width, content_width = self.panel_splitter.sizes()
        config.set('Panels', 'sidebar_width', str(sidebar_width))
        config.set('Panels', 'content_width', str(content_width))

        with open(self.config_path, 'w', encoding='utf-8') as configfile:
            config.write(configfile)
        event.accept()

    @Slot(QUrl)
    def open_link(self, url):
        if url.scheme() == '':
            # Handle relative URLs as local files
            url = QUrl.fromLocalFile(url.toString())
        
        if url.scheme() == 'file' and url.toLocalFile().endswith('.md'):
            # Load local Markdown file with styles
            load_file_by_path(url.toLocalFile(), self)
        else:
            # Open external links in system browser
            QDesktopServices.openUrl(url)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    widget = MyWidget()
    widget.show()
    sys.exit(app.exec())