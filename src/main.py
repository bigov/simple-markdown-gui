"""Main window and application entry point for Simple Markdown GUI."""

import configparser
import sys
import os

from PySide6.QtCore import Qt, QTimer, QByteArray
from PySide6.QtGui import QAction, QCloseEvent, QPalette
from PySide6.QtWidgets import QMenu
from PySide6.QtWidgets import QApplication, QFrame, QLabel, QMainWindow
from PySide6.QtWidgets import QMessageBox

from config import AppConfig, setup_app_icon, configure_app_identity

try:
    from . import __version__
except ImportError:
    from __init__ import __version__

try:
    from .master_panel import MasterPanel
except ImportError:
    from master_panel import MasterPanel

from toolbar import create_toolbar
from menubar import create_menu_bar
from files_panel import initialize_sidebar
from filesystem import load_file, load_file_by_path, save_current_file


class MyApp(MasterPanel, QMainWindow):
    """Main class Simple Markdown GUI"""

    app_title = "Simple Markdown GUI"
    config_section_name = "Default"
    legacy_window_section_name = "Window"
    panel_margin = 4
    panel_spacing = 1

    # Class attribute declarations with types for actions assigned during UI setup.
    save_action: QAction
    preview_action: QAction
    bold_action: QAction
    underline_action: QAction
    italic_action: QAction
    strikethrough_action: QAction
    edit_menu: QMenu

    def __init__(self):
        QMainWindow.__init__(self)
        self.config_path = AppConfig.ensure_config_exists()
        self.current_file_path = None
        self.current_sidebar_directory = None
        self._original_markdown = ""  # Store original markdown when in preview mode
        self._editor_markdown = ""
        self._status_mode = "Режим форматированного редактирования"
        self._hovered_link = ""
        self._status_message = ""
        self._initialize_master_panel()

        self.toolbar = create_toolbar(self)
        self.toolbar.setObjectName("edit_toolbar")
        self.toolbar.setMovable(False)
        self.addToolBar(Qt.ToolBarArea.TopToolBarArea, self.toolbar)

        # Load window size and base dir from config
        config = configparser.ConfigParser()
        config.read(self.config_path)

        self.resize(800, 600)

        # Create sidebar with file list
        (
            self.sidebar,
            self.file_model,
            self.sidebar_container,
            self.sidebar_layout,
            self.sidebar_dock,
            self.base_dir,
            startup_file,
        ) = initialize_sidebar(
            self,
            config,
            self.config_section_name,
            self.on_sidebar_clicked,
            self._apply_panel_frame_style,
            self._sync_panel_layout,
        )

        self._configure_panel_appearance()
        create_menu_bar(self)
        self.status_message_label = QLabel()
        self.status_message_label.setMinimumWidth(260)
        self.status_message_label.setContentsMargins(self.panel_margin, 0, 0, 0)
        self.statusBar().addWidget(self.status_message_label, 1)
        self.status_context_label = QLabel()
        self.modified_status_label = QLabel()
        self.modified_status_label.setMinimumWidth(90)
        self.modified_status_label.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )
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
        self.update_save_action_state()

        if startup_file:
            load_file_by_path(startup_file, self)

    def on_sidebar_clicked(self, index):
        """Handle sidebar file selection."""
        clicked_path = self.file_model.filePath(index)
        if self.file_model.isDir(index):
            self.current_sidebar_directory = clicked_path
        else:
            self.current_sidebar_directory = os.path.dirname(clicked_path)
            if not self.confirm_close_editor():
                return
            load_file(self.file_model, index, self)

    def update_save_action_state(self):
        is_modified = self.editor.document().isModified()

        if hasattr(self, "save_action"):
            self.save_action.setEnabled(is_modified and bool(self.current_file_path))
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
        border_color = panel.palette().color(QPalette.ColorRole.Mid).lighter(150).name()
        bottom_border_color = (
            panel.palette().color(QPalette.ColorRole.Mid).lighter(112).name()
        )
        background_color = panel.palette().color(QPalette.ColorRole.Base).name()

        panel.setFrameShape(QFrame.Shape.StyledPanel)
        panel.setFrameShadow(QFrame.Shadow.Plain)
        panel.setLineWidth(1)
        panel.setMidLineWidth(0)
        panel.setAutoFillBackground(True)
        if hasattr(panel, "viewport"):
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
            if dock_area == Qt.DockWidgetArea.LeftDockWidgetArea:
                sidebar_right = inner_margin
                content_left = inner_margin
            elif dock_area == Qt.DockWidgetArea.RightDockWidgetArea:
                sidebar_left = inner_margin
                content_right = inner_margin

        self.content_layout.setContentsMargins(
            content_left, outer_margin, content_right, outer_margin
        )
        self.sidebar_layout.setContentsMargins(
            sidebar_left, outer_margin, sidebar_right, outer_margin
        )

    def show_status_message(self, message, timeout=0):
        self.status_message_timer.stop()
        self._status_message = message
        self._render_status_message(message)
        if timeout > 0:
            self.status_message_timer.start(timeout)

    def _is_source_mode(self):
        return hasattr(self, "preview_action") and self.preview_action.isChecked()

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
        self.status_context_label.setText(
            f"{self._status_mode} | {self._current_file_label()}"
        )

    def _update_modified_indicator(self):
        if self.editor.document().isModified():
            self.modified_status_label.setText("Изменено")
        else:
            self.modified_status_label.setText("")

    def _update_window_title(self):
        title = self.app_title
        if self.current_file_path:
            title = f"{os.path.basename(self.current_file_path)} - {self.app_title}"
        if self.editor.document().isModified():
            title = f"* {title}"
        self.setWindowTitle(title)

    def _update_edit_actions_state(self):
        is_source_mode = self._is_source_mode()
        can_format = not is_source_mode

        if hasattr(self, "edit_menu"):
            self.edit_menu.setEnabled(True)
        if hasattr(self, "preview_action"):
            self.preview_action.setEnabled(True)
        for action_name in (
            "bold_action",
            "underline_action",
            "italic_action",
            "strikethrough_action",
        ):
            if hasattr(self, action_name):
                getattr(self, action_name).setEnabled(can_format)

    def _clear_link_status_if_needed(self):
        self._hovered_link = ""
        self._restore_status_message()

    def _render_status_message(self, message):
        self.status_message_label.setText(message)
        self.status_message_label.update()
        self.statusBar().update()

    def _restore_status_message(self):
        self.status_message_timer.stop()
        if self._hovered_link:
            self._render_status_message(self._hovered_link)
            return
        self._status_message = ""
        self._render_status_message("")

    def show_about_dialog(self):
        QMessageBox.about(
            self,
            "About",
            "Simple Markdown GUI\n"
            f"Version {__version__}\n\n"
            "Markdown viewer and editor with a file panel and round-trip save mode.",
        )

    def _parse_state_fields(self, value):
        fields = {}
        for part in value.split(","):
            key, separator, raw_value = part.partition("=")
            if not separator:
                continue
            fields[key.strip().lower()] = raw_value.strip().lower()
        return fields

    def _restore_human_geometry(self, geometry_value, width, height):
        geometry_fields = self._parse_state_fields(geometry_value)
        try:
            x = int(geometry_fields["x"])
            y = int(geometry_fields["y"])
        except (KeyError, ValueError):
            return False

        self.setGeometry(x, y, width, height)
        return True

    def _get_config_value(
        self, config, option_name, fallback="", legacy_option_name=None
    ):
        if config.has_option(self.config_section_name, option_name):
            return config.get(self.config_section_name, option_name, fallback=fallback)

        legacy_option_name = legacy_option_name or option_name
        if config.has_option(self.legacy_window_section_name, legacy_option_name):
            return config.get(
                self.legacy_window_section_name, legacy_option_name, fallback=fallback
            )

        return fallback

    def _get_config_int(self, config, option_name, fallback=0, legacy_option_name=None):
        if config.has_option(self.config_section_name, option_name):
            try:
                return config.getint(self.config_section_name, option_name)
            except ValueError:
                return fallback

        legacy_option_name = legacy_option_name or option_name
        if config.has_option(self.legacy_window_section_name, legacy_option_name):
            try:
                return config.getint(
                    self.legacy_window_section_name, legacy_option_name
                )
            except ValueError:
                return fallback

        return fallback

    def _restore_window_position(self, config, width, height):
        if not any(
            config.has_option(self.config_section_name, option_name)
            or config.has_option(self.legacy_window_section_name, legacy_option_name)
            for option_name, legacy_option_name in (
                ("window_left", "left"),
                ("window_top", "top"),
            )
        ):
            return False

        try:
            left = self._get_config_int(
                config, "window_left", legacy_option_name="left"
            )
            top = self._get_config_int(config, "window_top", legacy_option_name="top")
        except ValueError:
            return False

        self.setGeometry(left, top, width, height)
        return True

    def _restore_human_state(self, state_value):
        state_fields = self._parse_state_fields(state_value)
        if not state_fields:
            return False

        window_state = state_fields.get("window", "normal")
        if window_state == "maximized":
            self.showMaximized()
        elif window_state == "fullscreen":
            self.showFullScreen()
        else:
            self.showNormal()

        sidebar_state = state_fields.get("sidebar", "left")
        if sidebar_state == "hidden":
            self.sidebar_dock.hide()
        else:
            self.sidebar_dock.show()
            dock_area = (
                Qt.DockWidgetArea.RightDockWidgetArea
                if sidebar_state == "right"
                else Qt.DockWidgetArea.LeftDockWidgetArea
            )
            self.addDockWidget(dock_area, self.sidebar_dock)

        toolbar_state = state_fields.get("toolbar", "hidden")
        self.toolbar.setVisible(toolbar_state == "visible")
        return True

    def _restore_window_layout(self, config):
        if (
            self.config_section_name not in config
            and self.legacy_window_section_name not in config
        ):
            return False

        window_state = self._get_config_value(config, "window_state").strip().lower()
        sidebar_position = (
            self._get_config_value(config, "sidebar_position").strip().lower()
        )

        toolbar_status = (
            self._get_config_value(config, "toolbar_status").strip().lower()
        )
        if not toolbar_status:
            legacy_toolbar_visibility = (
                self._get_config_value(config, "toolbar_visibility").strip().lower()
            )
            if legacy_toolbar_visibility == "visible":
                toolbar_status = "on"
            elif legacy_toolbar_visibility == "hidden":
                toolbar_status = "off"

        if not any((window_state, sidebar_position, toolbar_status)):
            return False

        if window_state == "maximized":
            self.showMaximized()
        elif window_state == "fullscreen":
            self.showFullScreen()
        else:
            self.showNormal()

        if sidebar_position == "hidden":
            self.sidebar_dock.hide()
        else:
            self.sidebar_dock.show()
            dock_area = (
                Qt.DockWidgetArea.RightDockWidgetArea
                if sidebar_position == "right"
                else Qt.DockWidgetArea.LeftDockWidgetArea
            )
            self.addDockWidget(dock_area, self.sidebar_dock)

        self.toolbar.setVisible(toolbar_status != "off")
        return True

    def _serialize_state(self):
        if self.isFullScreen():
            window_state = "fullscreen"
        elif self.isMaximized():
            window_state = "maximized"
        else:
            window_state = "normal"

        if not self.sidebar_dock.isVisible():
            sidebar_state = "hidden"
        elif (
            self.dockWidgetArea(self.sidebar_dock)
            == Qt.DockWidgetArea.RightDockWidgetArea
        ):
            sidebar_state = "right"
        else:
            sidebar_state = "left"

        toolbar_state = "visible" if self.toolbar.isVisible() else "hidden"
        return window_state, sidebar_state, toolbar_state

    def _restore_window_state(self, config):
        width = self._get_config_int(
            config, "window_width", fallback=800, legacy_option_name="width"
        )
        height = self._get_config_int(
            config, "window_height", fallback=600, legacy_option_name="height"
        )
        self.resize(width, height)
        self._queue_panel_sizes_restore(config)

        restored_position = self._restore_window_position(config, width, height)

        geometry_value = self._get_config_value(
            config, "window_geometry", legacy_option_name="geometry"
        )
        if geometry_value and not restored_position:
            if not self._restore_human_geometry(geometry_value, width, height):
                geometry = QByteArray.fromBase64(geometry_value.encode("ascii"))
                if not geometry.isEmpty():
                    self.restoreGeometry(geometry)

        restored_layout = self._restore_window_layout(config)

        state_value = self._get_config_value(
            config, "window_legacy_state", legacy_option_name="state"
        )
        if state_value and not restored_layout:
            if not self._restore_human_state(state_value):
                state = QByteArray.fromBase64(state_value.encode("ascii"))
                if not state.isEmpty():
                    self.restoreState(state)

    def _save_window_state(self, config):
        if not config.has_section(self.config_section_name):
            config.add_section(self.config_section_name)

        geometry = self.geometry()
        config.set(self.config_section_name, "window_width", str(self.width()))
        config.set(self.config_section_name, "window_height", str(self.height()))
        config.set(self.config_section_name, "window_left", str(geometry.x()))
        config.set(self.config_section_name, "window_top", str(geometry.y()))
        config.set(
            self.config_section_name, "sidebar_width", str(self.sidebar_dock.width())
        )
        config.remove_option(self.config_section_name, "window_geometry")
        window_state, sidebar_state, toolbar_state = self._serialize_state()
        config.set(self.config_section_name, "window_state", window_state)
        config.set(self.config_section_name, "sidebar_position", sidebar_state)
        config.set(
            self.config_section_name,
            "toolbar_status",
            "on" if toolbar_state == "visible" else "off",
        )
        config.remove_option(self.config_section_name, "toolbar_visibility")
        config.remove_option(self.config_section_name, "window_legacy_state")
        if config.has_section(self.legacy_window_section_name):
            config.remove_section(self.legacy_window_section_name)
        if config.has_section("Panels"):
            config.remove_section("Panels")

    def _queue_panel_sizes_restore(self, config):
        sidebar_width = self._get_config_int(config, "sidebar_width", fallback=0)

        if sidebar_width <= 0 and "Panels" in config:
            try:
                sidebar_width = config.getint("Panels", "sidebar_width", fallback=0)
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

        available_width = max(
            1, self.sidebar_dock.width() + self.content_widget.width()
        )
        sidebar_width = min(self._pending_sidebar_width, available_width - 1)
        self.resizeDocks(
            [self.sidebar_dock], [sidebar_width], Qt.Orientation.Horizontal
        )
        self._panel_sizes_restored = True

    def showEvent(self, event):
        super().showEvent(event)
        QTimer.singleShot(0, self._apply_pending_panel_sizes)

    def handle_save_action(self):
        try:
            if not save_current_file(self):
                QMessageBox.warning(
                    self,
                    "Save error",
                    "Could not determine the source file to save.",
                )
                return
        except OSError as error:
            QMessageBox.warning(self, "Save error", f"Could not save file:\n{error}")
            return

        self.editor.document().setModified(False)
        self.update_save_action_state()
        self.notify_current_file_changed()
        self.show_status_message("Файл сохранен", 3000)

    def closeEvent(self, event: QCloseEvent):
        # Save window geometry and dock/toolbar layout to config
        config = configparser.ConfigParser()
        config.read(self.config_path)
        self._save_window_state(config)

        AppConfig.write_config(config)
        event.accept()


if __name__ == "__main__":
    configure_app_identity()
    qt_app = QApplication(sys.argv)
    widget = MyApp()
    setup_app_icon(qt_app, widget)
    widget.show()
    sys.exit(qt_app.exec())
