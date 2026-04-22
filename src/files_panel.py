"""Files panel creation helpers."""

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDockWidget, QFileSystemModel, QTreeView, QVBoxLayout
from PySide6.QtWidgets import QWidget


def resolve_base_dir(base_dir=None):
    """Resolve the configured base directory to an existing absolute path."""
    if base_dir is None:
        base_dir = "./"

    base_path = Path(base_dir).resolve()
    if not base_path.exists():
        base_path = Path("./").resolve()

    return str(base_path)


def get_sidebar_base_dir(config, section_name="Default"):
    """Read and resolve the sidebar base directory from app config."""
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


def create_sidebar(base_dir=None):
    """Create a sidebar with file system tree view."""
    base_path = Path(resolve_base_dir(base_dir))

    sidebar = QTreeView()
    model = QFileSystemModel()
    model.setRootPath(str(base_path))

    sidebar.setModel(model)
    sidebar.setRootIndex(model.index(str(base_path)))
    sidebar.setHeaderHidden(True)

    # Hide columns except name
    sidebar.hideColumn(1)  # Size column
    sidebar.hideColumn(2)  # Type column
    sidebar.hideColumn(3)  # Date Modified column

    sidebar.setColumnWidth(0, 100)

    return sidebar, model


# Qt panel setup intentionally accepts config and callback hooks in one place.
# pylint: disable=too-many-arguments,too-many-positional-arguments
def initialize_sidebar(
    window,
    config=None,
    config_section_name="Default",
    click_handler=None,
    frame_style_handler=None,
    layout_sync_handler=None,
):
    """Create and attach the sidebar widgets to the main window."""
    if config is None:
        base_dir = resolve_base_dir()
    else:
        base_dir = get_sidebar_base_dir(config, config_section_name)

    sidebar, model = create_sidebar(base_dir)

    if click_handler is not None:
        sidebar.clicked.connect(click_handler)

    if frame_style_handler is not None:
        frame_style_handler(sidebar)

    sidebar_container = QWidget()
    sidebar_layout = QVBoxLayout(sidebar_container)
    sidebar_layout.setContentsMargins(
        window.panel_margin,
        window.panel_margin,
        window.panel_margin,
        window.panel_margin,
    )
    sidebar_layout.setSpacing(0)
    sidebar_layout.addWidget(sidebar)

    sidebar_dock = QDockWidget("Files", window)
    sidebar_dock.setObjectName("sidebar_dock")
    sidebar_dock.setAllowedAreas(
        Qt.DockWidgetArea.LeftDockWidgetArea | Qt.DockWidgetArea.RightDockWidgetArea
    )
    sidebar_dock.setWidget(sidebar_container)
    sidebar_dock.setTitleBarWidget(QWidget())
    window.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, sidebar_dock)

    if layout_sync_handler is not None:
        sidebar_dock.dockLocationChanged.connect(layout_sync_handler)
        sidebar_dock.visibilityChanged.connect(layout_sync_handler)

    startup_file = get_startup_file_path(base_dir)

    return (
        sidebar,
        model,
        sidebar_container,
        sidebar_layout,
        sidebar_dock,
        base_dir,
        startup_file,
    )
