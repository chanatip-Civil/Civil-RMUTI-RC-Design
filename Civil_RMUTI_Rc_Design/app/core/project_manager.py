"""Project life-cycle management: new / open / save / close.

``ProjectManager`` owns the current :class:`Project`, its file path and the
"modified" flag. It is GUI independent; the GUI subscribes to change events
through :meth:`add_listener`.

File layout of ``.rcproj`` (UTF-8 JSON)::

    {
      "file_format": "CIVIL_RMUTI_RC_DESIGN_PROJECT",
      "format_version": 1,
      "application": {"name": ..., "version": ...},
      "saved_at": "...",
      "project": { ...Project.to_dict()... }
    }

The ``project`` payload is isolated from the header so the storage back-end
can later be swapped for SQLite while keeping the same model.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable

from app.core.constants import (
    APP_NAME,
    APP_VERSION,
    FILE_FORMAT_ID,
    FILE_FORMAT_VERSION,
    PROJECT_FILE_EXTENSION,
)
from app.core.exceptions import ProjectFileError, ProjectStateError
from app.core.logger import get_logger
from app.core.project_model import DesignSettings, Project, ProjectInformation
from app.utils.file_manager import ensure_extension, read_json, write_json

_log = get_logger("project_manager")


class ProjectEvent(str, Enum):
    """Events broadcast to listeners."""

    OPENED = "opened"          # new project created or file opened
    CLOSED = "closed"
    SAVED = "saved"
    MODIFIED = "modified"      # data changed (modified flag set)


ProjectListener = Callable[[ProjectEvent], None]


class ProjectManager:
    """Holds the current project and performs file operations."""

    def __init__(self) -> None:
        self._project: Project | None = None
        self._file_path: Path | None = None
        self._modified: bool = False
        self._listeners: list[ProjectListener] = []

    # ------------------------------------------------------------- properties
    @property
    def project(self) -> Project | None:
        """The open project, or None."""
        return self._project

    @property
    def has_project(self) -> bool:
        """True if a project is open."""
        return self._project is not None

    @property
    def file_path(self) -> Path | None:
        """Path of the open project file (None until first save)."""
        return self._file_path

    @property
    def is_modified(self) -> bool:
        """True when there are unsaved changes."""
        return self._modified

    def require_project(self) -> Project:
        """Return the open project or raise :class:`ProjectStateError`."""
        if self._project is None:
            raise ProjectStateError("No project is open. Create or open a project first.")
        return self._project

    @property
    def display_name(self) -> str:
        """Name for title bars: project name, file name or 'Untitled'."""
        if self._project and self._project.information.project_name.strip():
            return self._project.information.project_name.strip()
        if self._file_path:
            return self._file_path.stem
        return "Untitled"

    # -------------------------------------------------------------- listeners
    def add_listener(self, listener: ProjectListener) -> None:
        """Subscribe to project events."""
        if listener not in self._listeners:
            self._listeners.append(listener)

    def remove_listener(self, listener: ProjectListener) -> None:
        """Unsubscribe from project events."""
        if listener in self._listeners:
            self._listeners.remove(listener)

    def _emit(self, event: ProjectEvent) -> None:
        for listener in list(self._listeners):
            try:
                listener(event)
            except Exception:  # A faulty listener must not break file operations.
                _log.exception("Project listener failed for event %s", event.value)

    # ------------------------------------------------------------ operations
    def new_project(self, information: ProjectInformation,
                    settings: DesignSettings | None = None,
                    materials: dict[str, list[Any]] | None = None) -> Project:
        """Create a new, unsaved project and make it current.

        Args:
            information: Project information.
            settings: Design settings (defaults if None).
            materials: Optional initial material lists with the keys
                ``"concretes"``, ``"rebar_grades"``, ``"rebar_sizes"``
                (e.g. copied from the user material library). Missing or
                empty lists keep the built-in defaults.
        """
        project = Project(information=information, settings=settings or DesignSettings())
        for key, items in (materials or {}).items():
            if key in ("concretes", "rebar_grades", "rebar_sizes") and items:
                setattr(project, key, list(items))
        self._project = project
        self._file_path = None
        self._modified = True
        _log.info("New project created: %s", self.display_name)
        self._emit(ProjectEvent.OPENED)
        return self._project

    def open_project(self, path: Path | str) -> Project:
        """Load a project file and make it current.

        Raises:
            ProjectFileError: If the file is missing, corrupted or incompatible.
        """
        file_path = Path(path)
        project = self.load_file(file_path)
        self._project = project
        self._file_path = file_path.resolve()
        self._modified = False
        _log.info("Project opened: %s", self._file_path)
        self._emit(ProjectEvent.OPENED)
        return project

    def save_project(self, path: Path | str | None = None) -> Path:
        """Save the current project.

        Args:
            path: Target path for "Save As". When None the current path is used.

        Returns:
            The path that was written.

        Raises:
            ProjectStateError: No project is open or no path is known.
            ProjectFileError: Writing failed (the previous file is untouched).
        """
        project = self.require_project()
        target = Path(path) if path is not None else self._file_path
        if target is None:
            raise ProjectStateError("The project has not been saved yet; choose a file name.")
        target = ensure_extension(target, PROJECT_FILE_EXTENSION)

        project.modified_at = datetime.now().isoformat(timespec="seconds")
        project.app_version = APP_VERSION
        write_json(target, self.serialize(project))

        self._file_path = target.resolve()
        self._modified = False
        _log.info("Project saved: %s", self._file_path)
        self._emit(ProjectEvent.SAVED)
        return self._file_path

    def close_project(self) -> None:
        """Close the current project (unsaved changes are discarded)."""
        if self._project is None:
            return
        _log.info("Project closed: %s", self.display_name)
        self._project = None
        self._file_path = None
        self._modified = False
        self._emit(ProjectEvent.CLOSED)

    def mark_modified(self) -> None:
        """Flag the project as changed and notify listeners."""
        if self._project is None:
            return
        self._modified = True
        self._emit(ProjectEvent.MODIFIED)

    def save_recovery_copy(self, directory: Path) -> Path | None:
        """Write an emergency copy of the open project (used on crashes).

        Returns:
            Path of the recovery file, or None when nothing was written.
        """
        if self._project is None:
            return None
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_name = "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in self.display_name)
        target = Path(directory) / f"recovery_{safe_name}_{stamp}{PROJECT_FILE_EXTENSION}"
        try:
            write_json(target, self.serialize(self._project), keep_backup=False)
        except ProjectFileError:
            _log.exception("Recovery copy could not be written")
            return None
        _log.warning("Recovery copy written: %s", target)
        return target

    # --------------------------------------------------------- serialization
    @staticmethod
    def serialize(project: Project) -> dict[str, Any]:
        """Return the full file content (header + project payload)."""
        return {
            "file_format": FILE_FORMAT_ID,
            "format_version": FILE_FORMAT_VERSION,
            "application": {"name": APP_NAME, "version": APP_VERSION},
            "saved_at": datetime.now().isoformat(timespec="seconds"),
            "project": project.to_dict(),
        }

    @staticmethod
    def deserialize(data: Any) -> Project:
        """Validate the file header and rebuild the :class:`Project`.

        Raises:
            ProjectFileError: For foreign or newer file formats.
        """
        if not isinstance(data, dict) or data.get("file_format") != FILE_FORMAT_ID:
            raise ProjectFileError(f"The selected file is not a {APP_NAME} project file.")
        version = data.get("format_version")
        if not isinstance(version, int) or version < 1:
            raise ProjectFileError("The project file has an invalid format version.")
        if version > FILE_FORMAT_VERSION:
            raise ProjectFileError(
                f"This project was created with a newer version of {APP_NAME} "
                f"(file format {version}). Please update the program."
            )
        payload = data.get("project")
        if not isinstance(payload, dict):
            raise ProjectFileError("The project file does not contain project data.")
        try:
            return Project.from_dict(ProjectManager._migrate(payload, version))
        except (KeyError, TypeError, ValueError) as exc:
            raise ProjectFileError(f"The project data is damaged: {exc}") from exc

    @staticmethod
    def _migrate(payload: dict[str, Any], version: int) -> dict[str, Any]:
        """Upgrade older payloads to the current format version.

        Version 1 is the first format, so no conversion is required yet. New
        format versions add an ``if version < N`` step here.
        """
        return payload

    @classmethod
    def load_file(cls, path: Path | str) -> Project:
        """Read and parse a project file without changing the current project."""
        file_path = Path(path)
        # ".json" is accepted for files saved by the web version (*.rcproj.json);
        # the file header is validated either way.
        if file_path.suffix.lower() not in (PROJECT_FILE_EXTENSION, ".json"):
            raise ProjectFileError(
                f"Unsupported file type '{file_path.suffix}'. "
                f"Please select a {PROJECT_FILE_EXTENSION} file."
            )
        return cls.deserialize(read_json(file_path))
