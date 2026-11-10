"""Management of the materials stored inside a project.

Rules:

* names are unique per material kind (case-insensitive);
* renaming a material updates every member and the project defaults;
* changing a material invalidates the stored results of members using it;
* a material that is used by a member or as a project default cannot be
  removed, and at least one item of every kind must remain.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.core.constants import DesignType
from app.core.exceptions import MaterialError
from app.core.project_model import DesignMember, Project
from app.materials.database import MaterialLibrary
from app.materials.schema import MaterialItem, MaterialKind

ROLE_CONCRETE: str = "concrete"
ROLE_MAIN_REBAR: str = "main_rebar"
ROLE_TIE_REBAR: str = "tie_rebar"

#: Member attributes and project default attributes that reference each kind.
_MEMBER_ATTRS: dict[MaterialKind, tuple[str, ...]] = {
    MaterialKind.CONCRETE: ("concrete",),
    MaterialKind.REBAR_GRADE: ("main_rebar", "tie_rebar"),
    MaterialKind.REBAR_SIZE: (),
}
_DEFAULT_ATTRS: dict[MaterialKind, tuple[str, ...]] = {
    MaterialKind.CONCRETE: ("default_concrete",),
    MaterialKind.REBAR_GRADE: ("default_main_rebar", "default_tie_rebar"),
    MaterialKind.REBAR_SIZE: (),
}


def _same(a: str, b: str) -> bool:
    return a.strip().lower() == b.strip().lower()


@dataclass(frozen=True)
class MaterialUsage:
    """Where a material is referenced."""

    members: tuple[str, ...]
    defaults: tuple[str, ...]

    @property
    def is_used(self) -> bool:
        """True if referenced anywhere."""
        return bool(self.members or self.defaults)

    def describe(self, limit: int = 8) -> str:
        """Readable multi-line description."""
        lines = [f"Project default: {d}" for d in self.defaults]
        lines += list(self.members[:limit])
        if len(self.members) > limit:
            lines.append(f"... and {len(self.members) - limit} more member(s)")
        return "\n".join(lines)


class ProjectMaterials:
    """CRUD operations on the materials of one :class:`Project`."""

    def __init__(self, project: Project) -> None:
        self.project = project

    # ---------------------------------------------------------------- access
    def items(self, kind: MaterialKind) -> list[MaterialItem]:
        """Live list of project items of *kind*."""
        return {
            MaterialKind.CONCRETE: self.project.concretes,
            MaterialKind.REBAR_GRADE: self.project.rebar_grades,
            MaterialKind.REBAR_SIZE: self.project.rebar_sizes,
        }[kind]  # type: ignore[return-value]

    def find(self, kind: MaterialKind, name: str) -> MaterialItem | None:
        """Project item called *name* (case-insensitive)."""
        return next((i for i in self.items(kind) if _same(i.name, name)), None)

    def _members(self) -> list[DesignMember]:
        return [m for dt in DesignType for m in self.project.members_of(dt)]

    def usage(self, kind: MaterialKind, name: str) -> MaterialUsage:
        """Members and defaults that reference *name*."""
        members = []
        for member in self._members():
            for attr in _MEMBER_ATTRS[kind]:
                if _same(getattr(member, attr), name):
                    role = attr.replace("_", " ")
                    members.append(f"{member.design_type.title} {member.name} ({role})")
        defaults = tuple(
            attr.replace("default_", "").replace("_", " ")
            for attr in _DEFAULT_ATTRS[kind]
            if _same(getattr(self.project.settings, attr), name)
        )
        return MaterialUsage(tuple(members), defaults)

    # ------------------------------------------------------------------ CRUD
    def add(self, kind: MaterialKind, item: MaterialItem) -> None:
        """Add *item* to the project.

        Raises:
            MaterialError: If the name already exists in the project.
        """
        if self.find(kind, item.name) is not None:
            raise MaterialError(f"{kind.singular} '{item.name}' already exists in the project.")
        self.items(kind).append(item)

    def update(self, kind: MaterialKind, old_name: str, item: MaterialItem) -> int:
        """Replace *old_name* with *item*, propagating renames.

        Returns:
            Number of members whose stored results were cleared.

        Raises:
            MaterialError: Unknown item or name collision.
        """
        items = self.items(kind)
        index = next((i for i, x in enumerate(items) if _same(x.name, old_name)), None)
        if index is None:
            raise MaterialError(f"{kind.singular} '{old_name}' was not found in the project.")
        if not _same(old_name, item.name) and self.find(kind, item.name) is not None:
            raise MaterialError(f"{kind.singular} '{item.name}' already exists in the project.")
        changed = items[index] != item
        items[index] = item

        affected = 0
        for member in self._members():
            uses = False
            for attr in _MEMBER_ATTRS[kind]:
                if _same(getattr(member, attr), old_name):
                    setattr(member, attr, item.name)
                    uses = True
            if uses and changed and member.result is not None:
                member.result = None  # results were based on the old properties
                member.touch()
                affected += 1
        for attr in _DEFAULT_ATTRS[kind]:
            if _same(getattr(self.project.settings, attr), old_name):
                setattr(self.project.settings, attr, item.name)
        return affected

    def remove(self, kind: MaterialKind, name: str) -> None:
        """Remove *name* from the project.

        Raises:
            MaterialError: Unknown, still used, or last item of its kind.
        """
        if self.find(kind, name) is None:
            raise MaterialError(f"{kind.singular} '{name}' was not found in the project.")
        usage = self.usage(kind, name)
        if usage.is_used:
            raise MaterialError(
                f"{kind.singular} '{name}' is still used and cannot be removed:\n{usage.describe()}"
            )
        if len(self.items(kind)) <= 1:
            raise MaterialError(f"The project must contain at least one {kind.singular.lower()}.")
        items = self.items(kind)
        items[:] = [x for x in items if not _same(x.name, name)]

    def import_from_library(self, library: MaterialLibrary, kind: MaterialKind,
                            names: list[str]) -> tuple[int, int]:
        """Copy library items into the project.

        Returns:
            ``(added, skipped)``; existing names are skipped, not overwritten.
        """
        added = skipped = 0
        for name in names:
            item = library.find(kind, name)
            if item is None or self.find(kind, name) is not None:
                skipped += 1
                continue
            self.items(kind).append(item)
            added += 1
        return added, skipped

    def set_default(self, role: str, name: str) -> None:
        """Set the project default concrete / main rebar / tie rebar.

        Raises:
            MaterialError: Unknown role or material.
        """
        kind = MaterialKind.CONCRETE if role == ROLE_CONCRETE else MaterialKind.REBAR_GRADE
        if role not in (ROLE_CONCRETE, ROLE_MAIN_REBAR, ROLE_TIE_REBAR):
            raise MaterialError(f"Unknown default material role '{role}'.")
        item = self.find(kind, name)
        if item is None:
            raise MaterialError(f"{kind.singular} '{name}' is not defined in the project.")
        setattr(self.project.settings, f"default_{role}", item.name)
