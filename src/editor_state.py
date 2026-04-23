"""Editor state container for the main window."""

from dataclasses import dataclass


@dataclass
class EditorState:
    """Mutable editor-specific state used across modules."""

    current_file_path: str | None = None
