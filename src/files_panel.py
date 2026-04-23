"""Files panel creation helpers."""

from pathlib import Path

from PySide6.QtCore import Qt, QSortFilterProxyModel
from PySide6.QtWidgets import QDockWidget, QFileSystemModel, QTreeView, QVBoxLayout
from PySide6.QtWidgets import QWidget


class DotEntryFilterProxyModel(QSortFilterProxyModel):
    """Hide files and directories whose names start with a dot."""

    def filterAcceptsRow(self, source_row, source_parent):
        source_model = self.sourceModel()
        if source_model is None:
            return False

        source_index = source_model.index(source_row, 0, source_parent)
        if not source_index.isValid():
            return False

        entry_name = source_model.fileName(source_index)
        return not entry_name.startswith(".")


def resolve_base_dir(base_dir=None):
    """Resolve the configured base directory to an existing absolute path."""
    if base_dir is None:
        base_dir = "./"

    base_path = Path(base_dir).resolve()
    if not base_path.exists():
        base_path = Path("./").resolve()

    return str(base_path)


def get_files_base_dir(config, section_name="Default"):
    """Read and resolve the files base directory from app config."""
    configured_base_dir = "./"
    if config.has_section(section_name):
        configured_base_dir = config.get(section_name, "base_dir", fallback="./")

    return resolve_base_dir(configured_base_dir)


def get_startup_file_path(base_dir, startup_file_name="index.md"):
    """Return the startup markdown file path if it exists."""
    startup_file = Path(base_dir) / startup_file_name
    if startup_file.is_file():
        return str(startup_file)
    return None


def create_files(base_dir=None):
    """Create a files with file system tree view."""
    base_path = Path(resolve_base_dir(base_dir))

    files = QTreeView()
    model = QFileSystemModel()
    model.setRootPath(str(base_path))
    proxy_model = DotEntryFilterProxyModel(files)
    proxy_model.setRecursiveFilteringEnabled(True)
    proxy_model.setSourceModel(model)

    files.setModel(proxy_model)
    files.setRootIndex(proxy_model.mapFromSource(model.index(str(base_path))))
    files.setHeaderHidden(True)

    # Hide columns except name
    files.hideColumn(1)  # Size column
    files.hideColumn(2)  # Type column
    files.hideColumn(3)  # Date Modified column

    files.setColumnWidth(0, 100)

    return files, model, proxy_model


# Qt panel setup intentionally accepts config and callback hooks in one place.
# pylint: disable=too-many-arguments,too-many-positional-arguments
def initialize_files(
    window,
    config=None,
    config_section_name="Default",
    click_handler=None,
    frame_style_handler=None,
    layout_sync_handler=None,
):
    """Create and attach the files widgets to the main window."""
    if config is None:
        base_dir = resolve_base_dir()
    else:
        base_dir = get_files_base_dir(config, config_section_name)

    files, model, proxy_model = create_files(base_dir)

    if click_handler is not None:
        files.clicked.connect(click_handler)

    if frame_style_handler is not None:
        frame_style_handler(files)

    files_container = QWidget()
    files_layout = QVBoxLayout(files_container)
    files_layout.setContentsMargins(
        window.panel_margin,
        window.panel_margin,
        window.panel_margin,
        window.panel_margin,
    )
    files_layout.setSpacing(0)
    files_layout.addWidget(files)

    files_dock = QDockWidget("Files", window)
    files_dock.setObjectName("files_dock")
    files_dock.setAllowedAreas(
        Qt.DockWidgetArea.LeftDockWidgetArea | Qt.DockWidgetArea.RightDockWidgetArea
    )
    files_dock.setWidget(files_container)
    files_dock.setTitleBarWidget(QWidget())
    window.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, files_dock)

    if layout_sync_handler is not None:
        files_dock.dockLocationChanged.connect(layout_sync_handler)
        files_dock.visibilityChanged.connect(layout_sync_handler)

    startup_file = get_startup_file_path(base_dir)

    return (
        files,
        model,
        proxy_model,
        files_container,
        files_layout,
        files_dock,
        base_dir,
        startup_file,
    )

