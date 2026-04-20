from pathlib import Path

from PySide6.QtCore import QDir
from PySide6.QtWidgets import QTreeView, QFileSystemModel


def create_sidebar(base_dir=None):
    """Create a sidebar with file system tree view."""
    if base_dir is None:
        base_dir = './'
    
    # Resolve base_dir to absolute path
    base_path = Path(base_dir).resolve()
    if not base_path.exists():
        base_path = Path('./').resolve()
    
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
