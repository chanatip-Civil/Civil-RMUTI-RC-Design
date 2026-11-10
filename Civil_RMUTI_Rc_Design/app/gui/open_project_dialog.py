"""File dialogs for opening and saving ``.rcproj`` project files."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import QFileDialog, QWidget

from app.core.constants import APP_NAME, PROJECT_FILE_EXTENSION, PROJECT_FILE_FILTER
from app.utils.file_manager import ensure_extension

_ALL_FILES_FILTER = "All files (*)"


def _start_directory(start_dir: str | Path | None) -> str:
    if start_dir and Path(start_dir).is_dir():
        return str(start_dir)
    documents = Path.home() / "Documents"
    return str(documents if documents.is_dir() else Path.home())


class ProjectFileDialog:
    """Static helpers wrapping :class:`QFileDialog`."""

    @staticmethod
    def get_open_path(parent: QWidget | None, start_dir: str | Path | None = None) -> Path | None:
        """Ask the user for a project file to open; None if cancelled."""
        path, _ = QFileDialog.getOpenFileName(
            parent,
            f"Open Project — {APP_NAME}",
            _start_directory(start_dir),
            f"{PROJECT_FILE_FILTER};;{_ALL_FILES_FILTER}",
        )
        return Path(path) if path else None

    @staticmethod
    def get_save_path(parent: QWidget | None, start_dir: str | Path | None = None,
                      suggested_name: str = "Untitled") -> Path | None:
        """Ask for a target file name; the extension is appended if missing."""
        safe = "".join(ch if ch.isalnum() or ch in " -_" else "_" for ch in suggested_name).strip()
        initial = Path(_start_directory(start_dir)) / f"{safe or 'Untitled'}{PROJECT_FILE_EXTENSION}"
        path, _ = QFileDialog.getSaveFileName(
            parent, f"Save Project As — {APP_NAME}", str(initial), PROJECT_FILE_FILTER
        )
        return ensure_extension(Path(path), PROJECT_FILE_EXTENSION) if path else None
