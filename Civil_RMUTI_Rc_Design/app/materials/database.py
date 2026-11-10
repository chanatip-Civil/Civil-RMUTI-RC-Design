"""Persistent user material library.

The library combines read-only **built-in** items with **user** items that
are stored in ``material_library.json`` in the user data folder. Every
project copies the materials it needs, so project files stay self-contained
and keep working on other computers (or in the web version).

The storage format is isolated in :meth:`MaterialLibrary._serialize` /
``_deserialize`` so it can be moved to SQLite later without API changes.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from app.core.exceptions import MaterialError, ProjectFileError
from app.core.logger import get_logger
from app.materials.concrete import DEFAULT_CONCRETE_GRADES, Concrete
from app.materials.reinforcement import (
    DEFAULT_REBAR_GRADES,
    DEFAULT_REBAR_SIZES,
    RebarGrade,
    RebarSize,
)
from app.materials.schema import MaterialItem, MaterialKind, item_from_dict
from app.utils.file_manager import read_json, write_json

_log = get_logger("materials")

LIBRARY_FILE_NAME: str = "material_library.json"
LIBRARY_FORMAT_ID: str = "CIVIL_RMUTI_RC_DESIGN_MATERIAL_LIBRARY"
LIBRARY_FORMAT_VERSION: int = 1

_BUILTINS: dict[MaterialKind, tuple[MaterialItem, ...]] = {
    MaterialKind.CONCRETE: DEFAULT_CONCRETE_GRADES,
    MaterialKind.REBAR_GRADE: DEFAULT_REBAR_GRADES,
    MaterialKind.REBAR_SIZE: DEFAULT_REBAR_SIZES,
}


def _same(a: str, b: str) -> bool:
    return a.strip().lower() == b.strip().lower()


class MaterialLibrary:
    """Built-in + user materials with CRUD and JSON persistence."""

    def __init__(self, path: Path | None = None, autoload: bool = True) -> None:
        """Create the library.

        Args:
            path: Library file. None = in-memory only (built-ins + session items).
            autoload: Load user items from *path* immediately.
        """
        self._path = path
        self._user: dict[MaterialKind, list[MaterialItem]] = {kind: [] for kind in MaterialKind}
        if path is not None and autoload:
            self.load()

    @classmethod
    def default(cls) -> "MaterialLibrary":
        """Library stored in the per-user data folder."""
        from app.core.settings import app_data_dir

        return cls(app_data_dir() / LIBRARY_FILE_NAME)

    @property
    def path(self) -> Path | None:
        """Library file location."""
        return self._path

    # ---------------------------------------------------------------- queries
    def items(self, kind: MaterialKind) -> list[MaterialItem]:
        """Built-in followed by user items of *kind*."""
        return [*_BUILTINS[kind], *self._user[kind]]

    def user_items(self, kind: MaterialKind) -> list[MaterialItem]:
        """User items of *kind*."""
        return list(self._user[kind])

    def find(self, kind: MaterialKind, name: str) -> MaterialItem | None:
        """Item called *name* (case-insensitive), or None."""
        return next((i for i in self.items(kind) if _same(i.name, name)), None)

    def is_builtin(self, kind: MaterialKind, name: str) -> bool:
        """True for read-only built-in items."""
        return any(_same(i.name, name) for i in _BUILTINS[kind])

    # Backwards compatible convenience accessors (used by Phase 1 code).
    @property
    def concretes(self) -> list[Concrete]:
        """All concrete grades."""
        return self.items(MaterialKind.CONCRETE)  # type: ignore[return-value]

    @property
    def rebar_grades(self) -> list[RebarGrade]:
        """All steel grades."""
        return self.items(MaterialKind.REBAR_GRADE)  # type: ignore[return-value]

    @property
    def rebar_sizes(self) -> list[RebarSize]:
        """All bar sizes."""
        return self.items(MaterialKind.REBAR_SIZE)  # type: ignore[return-value]

    def find_concrete(self, name: str) -> Concrete | None:
        """Concrete grade called *name*."""
        return self.find(MaterialKind.CONCRETE, name)  # type: ignore[return-value]

    def find_rebar_grade(self, name: str) -> RebarGrade | None:
        """Steel grade called *name*."""
        return self.find(MaterialKind.REBAR_GRADE, name)  # type: ignore[return-value]

    # ------------------------------------------------------------------- CRUD
    def add(self, kind: MaterialKind, item: MaterialItem) -> None:
        """Add a user item.

        Raises:
            MaterialError: If the name already exists.
        """
        if self.find(kind, item.name) is not None:
            raise MaterialError(f"{kind.singular} '{item.name}' already exists in the library.")
        self._user[kind].append(item)

    def update(self, kind: MaterialKind, old_name: str, item: MaterialItem) -> None:
        """Replace user item *old_name* with *item* (may rename).

        Raises:
            MaterialError: Built-in item, unknown item or name collision.
        """
        if self.is_builtin(kind, old_name):
            raise MaterialError(f"Built-in {kind.singular.lower()} '{old_name}' cannot be modified. "
                                "Use Duplicate to create an editable copy.")
        items = self._user[kind]
        index = next((i for i, x in enumerate(items) if _same(x.name, old_name)), None)
        if index is None:
            raise MaterialError(f"{kind.singular} '{old_name}' was not found in the library.")
        if not _same(old_name, item.name) and self.find(kind, item.name) is not None:
            raise MaterialError(f"{kind.singular} '{item.name}' already exists in the library.")
        items[index] = item

    def remove(self, kind: MaterialKind, name: str) -> None:
        """Delete user item *name*.

        Raises:
            MaterialError: Built-in or unknown item.
        """
        if self.is_builtin(kind, name):
            raise MaterialError(f"Built-in {kind.singular.lower()} '{name}' cannot be deleted.")
        before = len(self._user[kind])
        self._user[kind] = [x for x in self._user[kind] if not _same(x.name, name)]
        if len(self._user[kind]) == before:
            raise MaterialError(f"{kind.singular} '{name}' was not found in the library.")

    def unique_name(self, kind: MaterialKind, base: str) -> str:
        """Return *base* or ``base (2)``, ``base (3)`` ... that is not used yet."""
        if self.find(kind, base) is None:
            return base
        index = 2
        while self.find(kind, f"{base} ({index})") is not None:
            index += 1
        return f"{base} ({index})"

    # ------------------------------------------------------------ persistence
    def _serialize(self) -> dict[str, Any]:
        return {
            "file_format": LIBRARY_FORMAT_ID,
            "format_version": LIBRARY_FORMAT_VERSION,
            **{kind.value: [item.to_dict() for item in self._user[kind]] for kind in MaterialKind},
        }

    @staticmethod
    def _deserialize(data: Any) -> dict[MaterialKind, list[MaterialItem]]:
        if not isinstance(data, dict) or data.get("file_format") != LIBRARY_FORMAT_ID:
            raise ProjectFileError("The file is not a Civil RMUTI Rc Design material library.")
        version = data.get("format_version")
        if not isinstance(version, int) or version > LIBRARY_FORMAT_VERSION:
            raise ProjectFileError("The material library was created by a newer program version.")
        result: dict[MaterialKind, list[MaterialItem]] = {kind: [] for kind in MaterialKind}
        for kind in MaterialKind:
            for raw in data.get(kind.value) or []:
                try:
                    result[kind].append(item_from_dict(kind, raw))
                except (KeyError, TypeError, ValueError) as exc:
                    _log.warning("Skipped invalid %s entry %r: %s", kind.value, raw, exc)
        return result

    def load(self) -> None:
        """Load user items from the library file (missing file = empty)."""
        if self._path is None or not self._path.exists():
            return
        try:
            loaded = self._deserialize(read_json(self._path))
        except ProjectFileError:
            _log.exception("Material library could not be loaded: %s", self._path)
            return
        self._user = {kind: [] for kind in MaterialKind}
        for kind, items in loaded.items():
            for item in items:
                if self.find(kind, item.name) is None:  # ignore duplicates of built-ins
                    self._user[kind].append(item)

    def save(self) -> None:
        """Write user items to the library file.

        Raises:
            ProjectFileError: If the file cannot be written.
        """
        if self._path is None:
            return
        write_json(self._path, self._serialize())

    def export_to(self, path: Path) -> Path:
        """Export user items to *path* (for sharing with colleagues)."""
        return write_json(path, self._serialize(), keep_backup=False)

    def import_from(self, path: Path) -> tuple[int, int]:
        """Import items from an exported library file.

        Returns:
            ``(added, skipped)`` - items whose name already exists are skipped.

        Raises:
            ProjectFileError: If the file is invalid.
        """
        loaded = self._deserialize(read_json(path))
        added = skipped = 0
        for kind, items in loaded.items():
            for item in items:
                if self.find(kind, item.name) is None:
                    self._user[kind].append(item)
                    added += 1
                else:
                    skipped += 1
        return added, skipped


#: Phase 1 name kept for compatibility.
MaterialDatabase = MaterialLibrary
