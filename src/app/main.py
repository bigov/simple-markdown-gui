import configparser
import sys
import os
from pathlib import Path

from app_paths import AppPaths
from markdown_rendering import render_markdown_with_styles
from markdown_roundtrip import preserve_roundtrip_markdown

from PySide6.QtCore import QEvent, Qt, QTimer, QUrl, Slot, QByteArray
from PySide6.QtGui import QAction, QCloseEvent, QDesktopServices, QKeySequence, QPalette
from PySide6.QtWidgets import QApplication, QDockWidget, QFrame, QLabel, QMainWindow, QMessageBox, QTextBrowser, QTextEdit, QVBoxLayout, QWidget

from toolbar import create_toolbar
from sidebar import create_sidebar
from filesystem import load_file, load_file_by_path, save_current_file


class MyWidget(QMainWindow):
    app_title = "Simple Markdown GUI"
    panel_margin = 4
    panel_spacing = 1

    def __init__(self):
        QMainWindow.__init__(self)
        self.config_path = AppPaths.ensure_config_exists()
        self.browser = QTextBrowser()
        self.editor = QTextEdit()
        self._apply_panel_frame_style(self.browser)
        self._apply_panel_frame_style(self.editor)
        self.current_editor = self.browser
        self.current_file_path = None
        self._original_markdown = ""  # Store original markdown when in preview mode
        self._editor_markdown = ""
        self._status_mode = "Режим просмотра"
        self._hovered_link = ""
        self._status_message = ""

        self.browser.setCursor(Qt.ArrowCursor)
        self.browser.viewport().setCursor(Qt.ArrowCursor)
        self.browser.setMouseTracking(True)
        self.browser.viewport().setMouseTracking(True)
        self.browser.setOpenExternalLinks(False)  # Disable automatic link opening
        self.browser.setOpenLinks(False)  # Disable automatic link opening
        self.browser.anchorClicked.connect(self.open_link)  # Connect to custom handler
        self.browser.highlighted.connect(self.on_link_highlighted)
        self.browser.viewport().installEventFilter(self)

        self.editor.setCursor(Qt.IBeamCursor)
        self.editor.viewport().setCursor(Qt.IBeamCursor)
        self.editor.installEventFilter(self)
        self.editor.document().modificationChanged.connect(self.on_editor_modification_changed)

        self.toolbar = create_toolbar(self)
        self.toolbar.setObjectName("edit_toolbar")
        self.toolbar.setMovable(False)
        self.addToolBar(Qt.TopToolBarArea, self.toolbar)

        # Load window size and base dir from config
        config = configparser.ConfigParser()
        config.read(self.config_path)

        self.resize(800, 600)
        
        base_dir = './'        
        if 'Default' in config:
            base_dir = config.get('Default', 'base_dir', fallback='./')
        self.base_dir = self._resolve_base_dir(base_dir)

        # Create sidebar with file browser
        self.sidebar, self.file_model = create_sidebar(base_dir)
        self._apply_panel_frame_style(self.sidebar)
        self.sidebar.clicked.connect(self.on_sidebar_clicked)
        self.sidebar_container = QWidget()
        self.sidebar_layout = QVBoxLayout(self.sidebar_container)
        self.sidebar_layout.setContentsMargins(self.panel_margin, self.panel_margin, self.panel_margin, self.panel_margin)
        self.sidebar_layout.setSpacing(0)
        self.sidebar_layout.addWidget(self.sidebar)
        self.sidebar_dock = QDockWidget("Files", self)
        self.sidebar_dock.setObjectName("sidebar_dock")
        self.sidebar_dock.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)
        self.sidebar_dock.setWidget(self.sidebar_container)
        self.sidebar_dock.setTitleBarWidget(QWidget())
        self.addDockWidget(Qt.LeftDockWidgetArea, self.sidebar_dock)
        self.sidebar_dock.dockLocationChanged.connect(self._sync_panel_layout)
        self.sidebar_dock.visibilityChanged.connect(self._sync_panel_layout)

        # Create main content layout
        self.content_layout = QVBoxLayout()
        self.content_layout.setContentsMargins(self.panel_margin, self.panel_margin, self.panel_margin, self.panel_margin)
        self.content_layout.setSpacing(0)
        self.content_layout.addWidget(self.browser)

        self.content_widget = QWidget()
        self.content_widget.setLayout(self.content_layout)
        self.setCentralWidget(self.content_widget)
        self._configure_panel_appearance()
        self._create_menu_bar()
        self.status_message_label = QLabel()
        self.status_message_label.setMinimumWidth(260)
        self.status_message_label.setContentsMargins(self.panel_margin, 0, 0, 0)
        self.statusBar().addWidget(self.status_message_label, 1)
        self.status_context_label = QLabel()
        self.modified_status_label = QLabel()
        self.modified_status_label.setMinimumWidth(90)
        self.modified_status_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.statusBar().addPermanentWidget(self.modified_status_label)
        self.statusBar().addPermanentWidget(self.status_context_label)
        self.status_message_timer = QTimer(self)
        self.status_message_timer.setSingleShot(True)
        self.status_message_timer.timeout.connect(self._restore_status_message)
        self._update_status_context()
        self._render_status_message("")
        self._pending_sidebar_width = None
        self._panel_sizes_restored = False
        self._restore_window_state(config)
        
        # Hide toolbar initially (show only in edit mode)
        self.toolbar.hide()
        self.update_save_action_state()

        startup_file = os.path.join(self.base_dir, 'index.md')
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
        is_edit_mode = self.current_editor == self.editor
        is_modified = self.editor.document().isModified()

        if hasattr(self, 'save_action'):
            self.save_action.setEnabled(
                is_edit_mode
                and is_modified
                and bool(self.current_file_path)
            )
        self._update_modified_indicator()
        self._update_edit_actions_state()
        self._update_window_title()

    def on_editor_modification_changed(self, _modified):
        self.update_save_action_state()

    def _configure_panel_appearance(self):
        self.setStyleSheet(
            f"QMainWindow::separator {{ width: {self.panel_spacing}px; height: {self.panel_spacing}px; background: transparent; }}"
            "QDockWidget { margin: 0px; }"
        )
        self._sync_panel_layout()

    def _apply_panel_frame_style(self, panel):
        border_color = panel.palette().color(QPalette.Mid).lighter(150).name()
        bottom_border_color = panel.palette().color(QPalette.Mid).lighter(112).name()
        background_color = panel.palette().color(QPalette.Base).name()

        panel.setFrameShape(QFrame.StyledPanel)
        panel.setFrameShadow(QFrame.Plain)
        panel.setLineWidth(1)
        panel.setMidLineWidth(0)
        panel.setAutoFillBackground(True)
        if hasattr(panel, 'viewport'):
            panel.viewport().setAutoFillBackground(True)
        panel.setStyleSheet(
            f"border-top: 1px solid {border_color};"
            f"border-left: 1px solid {border_color};"
            f"border-right: 1px solid {border_color};"
            f"border-bottom: 1px solid {bottom_border_color};"
            f"background-color: {background_color};"
        )

    def _sync_panel_layout(self, *_args):
        outer_margin = self.panel_margin
        inner_margin = 0

        content_left = outer_margin
        content_right = outer_margin
        sidebar_left = outer_margin
        sidebar_right = outer_margin

        if self.sidebar_dock.isVisible():
            dock_area = self.dockWidgetArea(self.sidebar_dock)
            if dock_area == Qt.LeftDockWidgetArea:
                sidebar_right = inner_margin
                content_left = inner_margin
            elif dock_area == Qt.RightDockWidgetArea:
                sidebar_left = inner_margin
                content_right = inner_margin

        self.content_layout.setContentsMargins(content_left, outer_margin, content_right, outer_margin)
        self.sidebar_layout.setContentsMargins(sidebar_left, outer_margin, sidebar_right, outer_margin)

    def _create_menu_bar(self):
        file_menu = self.menuBar().addMenu("&File")
        file_menu.addAction(self.save_action)

        self.exit_action = QAction("Exit", self)
        self.exit_action.setShortcut(QKeySequence.Quit)
        self.exit_action.triggered.connect(self.close)
        file_menu.addSeparator()
        file_menu.addAction(self.exit_action)

        self.edit_menu = self.menuBar().addMenu("&Edit")
        self.edit_menu.addAction(self.preview_action)
        self.edit_menu.addSeparator()
        self.edit_menu.addAction(self.bold_action)
        self.edit_menu.addAction(self.underline_action)
        self.edit_menu.addAction(self.italic_action)
        self.edit_menu.addAction(self.strikethrough_action)

        view_menu = self.menuBar().addMenu("&View")
        view_menu.addAction(self.sidebar_dock.toggleViewAction())
        view_menu.addAction(self.toolbar.toggleViewAction())

        help_menu = self.menuBar().addMenu("&Help")
        self.about_action = QAction("About", self)
        self.about_action.triggered.connect(self.show_about_dialog)
        help_menu.addAction(self.about_action)

    def show_status_message(self, message, timeout=0):
        self.status_message_timer.stop()
        self._status_message = message
        self._render_status_message(message)
        if timeout > 0:
            self.status_message_timer.start(timeout)

    def _is_source_mode(self):
        return self.current_editor == self.editor and hasattr(self, 'preview_action') and self.preview_action.isChecked()

    def set_status_mode(self, mode):
        self._status_mode = mode
        self._update_status_context()

    def notify_current_file_changed(self):
        self._update_status_context()
        self._update_window_title()

    def _current_file_label(self):
        if self.current_file_path:
            return os.path.basename(self.current_file_path)
        return "Без файла"

    def _update_status_context(self):
        self.status_context_label.setText(f"{self._status_mode} | {self._current_file_label()}")

    def _update_modified_indicator(self):
        if self.current_editor == self.editor and self.editor.document().isModified():
            self.modified_status_label.setText("Изменено")
        else:
            self.modified_status_label.setText("")

    def _update_window_title(self):
        title = self.app_title
        if self.current_file_path:
            title = f"{os.path.basename(self.current_file_path)} - {self.app_title}"
        if self.current_editor == self.editor and self.editor.document().isModified():
            title = f"* {title}"
        self.setWindowTitle(title)

    def _update_edit_actions_state(self):
        is_edit_mode = self.current_editor == self.editor
        is_source_mode = self._is_source_mode()
        can_format = is_edit_mode and not is_source_mode

        if hasattr(self, 'edit_menu'):
            self.edit_menu.setEnabled(is_edit_mode)
        if hasattr(self, 'preview_action'):
            self.preview_action.setEnabled(is_edit_mode)
        for action_name in ('bold_action', 'underline_action', 'italic_action', 'strikethrough_action'):
            if hasattr(self, action_name):
                getattr(self, action_name).setEnabled(can_format)

    def _clear_link_status_if_needed(self):
        self._hovered_link = ""
        self._restore_status_message()

    def _render_status_message(self, message):
        self.status_message_label.setText(message)
        self.status_message_label.update()
        self.statusBar().update()

    def _resolve_base_dir(self, base_dir):
        base_path = Path(base_dir).resolve()
        if not base_path.exists():
            base_path = Path('./').resolve()
        return str(base_path)

    def _restore_status_message(self):
        self.status_message_timer.stop()
        if self._hovered_link and self.current_editor == self.browser:
            self._render_status_message(self._hovered_link)
            return
        self._status_message = ""
        self._render_status_message("")

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

    def show_about_dialog(self):
        QMessageBox.about(
            self,
            "О программе",
            "Simple Markdown GUI\n\nПросмотр и редактирование Markdown с файловой панелью и режимом round-trip сохранения.",
        )

    def _parse_state_fields(self, value):
        fields = {}
        for part in value.split(','):
            key, separator, raw_value = part.partition('=')
            if not separator:
                continue
            fields[key.strip().lower()] = raw_value.strip().lower()
        return fields

    def _restore_human_geometry(self, geometry_value, width, height):
        geometry_fields = self._parse_state_fields(geometry_value)
        try:
            x = int(geometry_fields['x'])
            y = int(geometry_fields['y'])
        except (KeyError, ValueError):
            return False

        self.setGeometry(x, y, width, height)
        return True

    def _restore_window_position(self, config, width, height):
        if 'Window' not in config:
            return False

        try:
            left = config.getint('Window', 'left')
            top = config.getint('Window', 'top')
        except (configparser.NoOptionError, ValueError):
            return False

        self.setGeometry(left, top, width, height)
        return True

    def _restore_human_state(self, state_value):
        state_fields = self._parse_state_fields(state_value)
        if not state_fields:
            return False

        window_state = state_fields.get('window', 'normal')
        if window_state == 'maximized':
            self.showMaximized()
        elif window_state == 'fullscreen':
            self.showFullScreen()
        else:
            self.showNormal()

        sidebar_state = state_fields.get('sidebar', 'left')
        if sidebar_state == 'hidden':
            self.sidebar_dock.hide()
        else:
            self.sidebar_dock.show()
            dock_area = Qt.RightDockWidgetArea if sidebar_state == 'right' else Qt.LeftDockWidgetArea
            self.addDockWidget(dock_area, self.sidebar_dock)

        toolbar_state = state_fields.get('toolbar', 'hidden')
        self.toolbar.setVisible(toolbar_state == 'visible')
        return True

    def _restore_window_layout(self, config):
        if 'Window' not in config:
            return False

        window_state = config.get('Window', 'window_state', fallback='').strip().lower()
        sidebar_position = config.get('Window', 'sidebar_position', fallback='').strip().lower()
        toolbar_visibility = config.get('Window', 'toolbar_visibility', fallback='').strip().lower()

        if not any((window_state, sidebar_position, toolbar_visibility)):
            return False

        if window_state == 'maximized':
            self.showMaximized()
        elif window_state == 'fullscreen':
            self.showFullScreen()
        else:
            self.showNormal()

        if sidebar_position == 'hidden':
            self.sidebar_dock.hide()
        else:
            self.sidebar_dock.show()
            dock_area = Qt.RightDockWidgetArea if sidebar_position == 'right' else Qt.LeftDockWidgetArea
            self.addDockWidget(dock_area, self.sidebar_dock)

        self.toolbar.setVisible(toolbar_visibility == 'visible')
        return True

    def _serialize_state(self):
        if self.isFullScreen():
            window_state = 'fullscreen'
        elif self.isMaximized():
            window_state = 'maximized'
        else:
            window_state = 'normal'

        if not self.sidebar_dock.isVisible():
            sidebar_state = 'hidden'
        elif self.dockWidgetArea(self.sidebar_dock) == Qt.RightDockWidgetArea:
            sidebar_state = 'right'
        else:
            sidebar_state = 'left'

        toolbar_state = 'visible' if self.toolbar.isVisible() else 'hidden'
        return window_state, sidebar_state, toolbar_state

    def _restore_window_state(self, config):
        width = config.getint('Window', 'width', fallback=800)
        height = config.getint('Window', 'height', fallback=600)
        self.resize(width, height)
        self._queue_panel_sizes_restore(config)

        restored_position = self._restore_window_position(config, width, height)

        geometry_value = config.get('Window', 'geometry', fallback='') if 'Window' in config else ''
        if geometry_value and not restored_position:
            if not self._restore_human_geometry(geometry_value, width, height):
                geometry = QByteArray.fromBase64(geometry_value.encode('ascii'))
                if not geometry.isEmpty():
                    self.restoreGeometry(geometry)

        restored_layout = self._restore_window_layout(config)

        state_value = config.get('Window', 'state', fallback='') if 'Window' in config else ''
        if state_value and not restored_layout:
            if not self._restore_human_state(state_value):
                state = QByteArray.fromBase64(state_value.encode('ascii'))
                if not state.isEmpty():
                    self.restoreState(state)

    def _save_window_state(self, config):
        if not config.has_section('Window'):
            config.add_section('Window')

        geometry = self.geometry()
        config.set('Window', 'width', str(self.width()))
        config.set('Window', 'height', str(self.height()))
        config.set('Window', 'left', str(geometry.x()))
        config.set('Window', 'top', str(geometry.y()))
        config.set('Window', 'sidebar_width', str(self.sidebar_dock.width()))
        config.remove_option('Window', 'geometry')
        window_state, sidebar_state, toolbar_state = self._serialize_state()
        config.set('Window', 'window_state', window_state)
        config.set('Window', 'sidebar_position', sidebar_state)
        config.set('Window', 'toolbar_visibility', toolbar_state)
        config.remove_option('Window', 'state')
        if config.has_section('Panels'):
            config.remove_section('Panels')

    def _queue_panel_sizes_restore(self, config):
        try:
            sidebar_width = config.getint('Window', 'sidebar_width', fallback=0)
        except ValueError:
            sidebar_width = 0

        if sidebar_width <= 0 and 'Panels' in config:
            try:
                sidebar_width = config.getint('Panels', 'sidebar_width', fallback=0)
            except ValueError:
                sidebar_width = 0

        self._pending_sidebar_width = sidebar_width if sidebar_width > 0 else None
        self._panel_sizes_restored = False

    def _apply_pending_panel_sizes(self):
        if self._panel_sizes_restored or self._pending_sidebar_width is None:
            return
        if not self.sidebar_dock.isVisible():
            return
        if self.width() <= 0 or self.content_widget.width() <= 0:
            return

        available_width = max(1, self.sidebar_dock.width() + self.content_widget.width())
        sidebar_width = min(self._pending_sidebar_width, available_width - 1)
        self.resizeDocks([self.sidebar_dock], [sidebar_width], Qt.Horizontal)
        self._panel_sizes_restored = True

    def showEvent(self, event):
        super().showEvent(event)
        QTimer.singleShot(0, self._apply_pending_panel_sizes)

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
        self.notify_current_file_changed()
        self.show_status_message("Файл сохранен", 3000)

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
        
        # Reset source mode when switching to browse
        if hasattr(self, 'preview_action'):
            self.preview_action.setChecked(False)

    def eventFilter(self, obj, event):
        if obj == self.browser.viewport() and event.type() == QEvent.MouseButtonDblClick:
            self.switch_to_edit(event)
            return True
        if obj == self.browser.viewport() and event.type() == QEvent.MouseMove:
            link = self.browser.anchorAt(event.position().toPoint())
            if link:
                formatted_link = self._format_hover_link(link)
                self._hovered_link = formatted_link
                self.show_status_message(formatted_link)
            elif self._hovered_link:
                self._clear_link_status_if_needed()
        if obj == self.browser.viewport() and event.type() == QEvent.Leave:
            self._clear_link_status_if_needed()
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

    def closeEvent(self, event: QCloseEvent):
        # Save window geometry and dock/toolbar layout to config
        config = configparser.ConfigParser()
        config.read(self.config_path)
        self._save_window_state(config)

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