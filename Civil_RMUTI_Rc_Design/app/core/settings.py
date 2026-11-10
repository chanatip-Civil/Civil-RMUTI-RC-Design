"""User application settings stored as JSON in the user data folder.

Default location: ``~/.civil_rmuti_rc_design/settings.json``. The folder can
be overridden with the ``RCDESIGN_HOME`` environment variable (used by tests
and portable installations).
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field, fields
from pathlib import Path
from typing import Any

from app.core.constants import MAX_RECENT_PROJECTS, DesignStandard, UnitSystem
from app.core.exceptions import ProjectFileError
from app.core.logger import get_logger
from app.utils.file_manager import read_json, write_json

_log = get_logger("settings")

SETTINGS_FILE_NAME: str = "settings.json"
HOME_ENV_VAR: str = "RCDESIGN_HOME"


def app_data_dir() -> Path:
    """Return (and create) the per-user application data folder."""
    override = os.environ.get(HOME_ENV_VAR)
    base = Path(override) if override else Path.home() / ".civil_rmuti_rc_design"
    try:
        base.mkdir(parents=True, exist_ok=True)
    except OSError:
        _log.warning("Cannot create data folder %s", base)
    return base


def logs_dir() -> Path:
    """Folder for log files."""
    return app_data_dir() / "logs"


def recovery_dir() -> Path:
    """Folder for emergency recovery copies."""
    return app_data_dir() / "recovery"


@dataclass
class AppSettings:
    """Persisted user preferences."""

    default_designer: str = ""
    default_organization: str = "Rajamangala University of Technology Isan (RMUTI)"
    default_design_standard: str = DesignStandard.EIT_1008.value
    default_unit_system: str = UnitSystem.SI.value
    last_directory: str = ""
    recent_projects: list[str] = field(default_factory=list)
    window_geometry: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a JSON compatible dict."""
        return {f.name: getattr(self, f.name) for f in fields(self)}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AppSettings":
        """Create settings from a dict, ignoring unknown or invalid keys."""
        settings = cls()
        for f in fields(cls):
            if f.name not in data:
                continue
            value = data[f.name]
            if f.name == "recent_projects":
                if isinstance(value, list):
                    settings.recent_projects = [str(v) for v in value][:MAX_RECENT_PROJECTS]
            elif isinstance(value, str):
                setattr(settings, f.name, value)
        return settings


class SettingsManager:
    """Loads and saves :class:`AppSettings`."""

    def __init__(self, directory: Path | None = None) -> None:
        self._path: Path = (directory or app_data_dir()) / SETTINGS_FILE_NAME
        self.settings: AppSettings = self._load()

    @property
    def path(self) -> Path:
        """Location of the settings file."""
        return self._path

    def _load(self) -> AppSettings:
        if not self._path.exists():
            return AppSettings()
        try:
            data = read_json(self._path)
            return AppSettings.from_dict(data if isinstance(data, dict) else {})
        except ProjectFileError:
            _log.warning("Settings file unreadable, defaults are used: %s", self._path)
            return AppSettings()

    def save(self) -> None:
        """Write settings to disk (errors are logged, never raised)."""
        try:
            write_json(self._path, self.settings.to_dict(), keep_backup=False)
        except ProjectFileError:
            _log.exception("Settings could not be saved")

    def add_recent_project(self, path: Path | str) -> None:
        """Move *path* to the top of the recent project list and save."""
        text = str(Path(path))
        recent = [p for p in self.settings.recent_projects if p != text]
        self.settings.recent_projects = [text, *recent][:MAX_RECENT_PROJECTS]
        self.settings.last_directory = str(Path(path).parent)
        self.save()

    def remove_recent_project(self, path: Path | str) -> None:
        """Remove *path* from the recent list and save."""
        text = str(Path(path))
        self.settings.recent_projects = [p for p in self.settings.recent_projects if p != text]
        self.save()

    def reset(self) -> None:
        """Restore default settings (recent projects and window size included) and save."""
        self.settings = AppSettings()
        self.save()

    def clear_recent_projects(self) -> None:
        """Empty the recent project list and save."""
        self.settings.recent_projects = []
        self.save()
