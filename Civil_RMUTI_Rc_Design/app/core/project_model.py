"""Project data model.

The model is a tree of plain dataclasses that maps 1:1 onto the ``.rcproj``
JSON layout::

    Project
    ├── project_information
    ├── design_settings      (design standard, unit system, default materials)
    ├── materials            (concrete grades used by the project)
    ├── reinforcement        (steel grades used by the project)
    ├── columns / beams / slabs / stairs / footings   (DesignMember lists)

Every class offers ``to_dict`` / ``from_dict``. ``from_dict`` is tolerant of
missing keys so older files keep loading when new fields are added.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any

from app.core.constants import (
    APP_VERSION,
    DesignStandard,
    DesignType,
    UnitSystem,
)
from app.materials.concrete import DEFAULT_CONCRETE_GRADES, Concrete
from app.materials.reinforcement import (
    DEFAULT_REBAR_GRADES,
    DEFAULT_REBAR_SIZES,
    RebarGrade,
    RebarSize,
)


def _now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _str(data: dict[str, Any], key: str, default: str = "") -> str:
    value = data.get(key, default)
    return default if value is None else str(value)


@dataclass
class ProjectInformation:
    """General project data shown on reports and title blocks."""

    project_name: str = ""
    project_number: str = ""
    designer: str = ""
    checker: str = ""
    organization: str = ""
    project_date: str = field(default_factory=lambda: date.today().isoformat())
    location: str = ""
    description: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a JSON compatible dict."""
        return dict(self.__dict__)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ProjectInformation":
        """Create an instance from a dict (missing keys use defaults)."""
        default = cls()
        return cls(**{key: _str(data, key, getattr(default, key)) for key in default.__dict__})


@dataclass
class DesignSettings:
    """Project-wide design settings."""

    design_standard: str = DesignStandard.EIT_1008.value
    unit_system: str = UnitSystem.SI.value
    default_concrete: str = "fc' 240 ksc"
    default_main_rebar: str = "SD40"
    default_tie_rebar: str = "SR24"

    @property
    def standard(self) -> DesignStandard:
        """Design standard as enum."""
        return DesignStandard.from_value(self.design_standard)

    @property
    def units(self) -> UnitSystem:
        """Unit system as enum."""
        return UnitSystem.from_value(self.unit_system)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a JSON compatible dict."""
        return dict(self.__dict__)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "DesignSettings":
        """Create an instance from a dict (missing keys use defaults)."""
        default = cls()
        return cls(**{key: _str(data, key, getattr(default, key)) for key in default.__dict__})


@dataclass
class DesignMember:
    """One designed structural member (e.g. column C1).

    Attributes:
        design_type: Member type.
        name: User visible mark, unique within its type.
        inputs: Input values keyed by field key (see design FIELD_SPECS).
        concrete: Concrete grade name.
        main_rebar: Main reinforcement grade name.
        tie_rebar: Stirrup / tie grade name.
        result: Last calculation result (dict) or None.
        notes: Free text.
    """

    design_type: DesignType
    name: str
    inputs: dict[str, Any] = field(default_factory=dict)
    concrete: str = ""
    main_rebar: str = ""
    tie_rebar: str = ""
    result: dict[str, Any] | None = None
    notes: str = ""
    member_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    created_at: str = field(default_factory=_now_iso)
    modified_at: str = field(default_factory=_now_iso)

    def touch(self) -> None:
        """Update the modification time stamp."""
        self.modified_at = _now_iso()

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a JSON compatible dict."""
        return {
            "member_id": self.member_id,
            "name": self.name,
            "inputs": dict(self.inputs),
            "concrete": self.concrete,
            "main_rebar": self.main_rebar,
            "tie_rebar": self.tie_rebar,
            "result": self.result,
            "notes": self.notes,
            "created_at": self.created_at,
            "modified_at": self.modified_at,
        }

    @classmethod
    def from_dict(cls, design_type: DesignType, data: dict[str, Any]) -> "DesignMember":
        """Create an instance from a dict produced by :meth:`to_dict`."""
        inputs = data.get("inputs") or {}
        result = data.get("result")
        return cls(
            design_type=design_type,
            name=_str(data, "name", design_type.name_prefix),
            inputs=dict(inputs) if isinstance(inputs, dict) else {},
            concrete=_str(data, "concrete"),
            main_rebar=_str(data, "main_rebar"),
            tie_rebar=_str(data, "tie_rebar"),
            result=result if isinstance(result, dict) else None,
            notes=_str(data, "notes"),
            member_id=_str(data, "member_id") or uuid.uuid4().hex,
            created_at=_str(data, "created_at") or _now_iso(),
            modified_at=_str(data, "modified_at") or _now_iso(),
        )


@dataclass
class Project:
    """Root object of a design project."""

    information: ProjectInformation = field(default_factory=ProjectInformation)
    settings: DesignSettings = field(default_factory=DesignSettings)
    concretes: list[Concrete] = field(default_factory=lambda: list(DEFAULT_CONCRETE_GRADES))
    rebar_grades: list[RebarGrade] = field(default_factory=lambda: list(DEFAULT_REBAR_GRADES))
    rebar_sizes: list[RebarSize] = field(default_factory=lambda: list(DEFAULT_REBAR_SIZES))
    members: dict[DesignType, list[DesignMember]] = field(
        default_factory=lambda: {dt: [] for dt in DesignType}
    )
    created_at: str = field(default_factory=_now_iso)
    modified_at: str = field(default_factory=_now_iso)
    app_version: str = APP_VERSION

    # ------------------------------------------------------------------ members
    def members_of(self, design_type: DesignType) -> list[DesignMember]:
        """Return the (live) member list of *design_type*."""
        return self.members.setdefault(design_type, [])

    def member_count(self, design_type: DesignType) -> int:
        """Number of members of *design_type*."""
        return len(self.members_of(design_type))

    def find_member(self, design_type: DesignType, member_id: str) -> DesignMember | None:
        """Return the member with *member_id*, or None."""
        return next((m for m in self.members_of(design_type) if m.member_id == member_id), None)

    def is_name_taken(self, design_type: DesignType, name: str,
                      exclude_id: str | None = None) -> bool:
        """True if another member of the same type already uses *name*."""
        wanted = name.strip().lower()
        return any(
            m.name.strip().lower() == wanted and m.member_id != exclude_id
            for m in self.members_of(design_type)
        )

    def next_member_name(self, design_type: DesignType) -> str:
        """Return the next free default name, e.g. ``C3``."""
        index = 1
        while self.is_name_taken(design_type, f"{design_type.name_prefix}{index}"):
            index += 1
        return f"{design_type.name_prefix}{index}"

    def add_member(self, member: DesignMember) -> DesignMember:
        """Append *member* and return it."""
        self.members_of(member.design_type).append(member)
        return member

    def remove_member(self, design_type: DesignType, member_id: str) -> bool:
        """Remove a member; return True if something was removed."""
        members = self.members_of(design_type)
        before = len(members)
        members[:] = [m for m in members if m.member_id != member_id]
        return len(members) != before

    # --------------------------------------------------------------- materials
    def find_concrete(self, name: str) -> Concrete | None:
        """Return the project concrete grade called *name*."""
        return next((c for c in self.concretes if c.name == name), None)

    def find_rebar_grade(self, name: str) -> RebarGrade | None:
        """Return the project steel grade called *name*."""
        return next((g for g in self.rebar_grades if g.name == name), None)

    def find_rebar_size(self, designation: str) -> RebarSize | None:
        """Return the project bar size called *designation*."""
        return next((s for s in self.rebar_sizes if s.designation == designation), None)

    # ----------------------------------------------------------- serialization
    def to_dict(self) -> dict[str, Any]:
        """Serialize the whole project (without the file header)."""
        data: dict[str, Any] = {
            "project_information": self.information.to_dict(),
            "design_settings": self.settings.to_dict(),
            "design_standard": {
                "code": self.settings.design_standard,
                "label": self.settings.standard.label,
            },
            "materials": {"concrete": [c.to_dict() for c in self.concretes]},
            "reinforcement": {
                "grades": [g.to_dict() for g in self.rebar_grades],
                "sizes": [s.to_dict() for s in self.rebar_sizes],
            },
            "metadata": {
                "created_at": self.created_at,
                "modified_at": self.modified_at,
                "app_version": self.app_version,
            },
        }
        for design_type in DesignType:
            data[design_type.project_key] = [m.to_dict() for m in self.members_of(design_type)]
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Project":
        """Rebuild a project from :meth:`to_dict` output."""
        info = ProjectInformation.from_dict(data.get("project_information") or {})
        settings = DesignSettings.from_dict(data.get("design_settings") or {})

        concrete_data = (data.get("materials") or {}).get("concrete")
        concretes = (
            [Concrete.from_dict(item) for item in concrete_data]
            if isinstance(concrete_data, list) and concrete_data
            else list(DEFAULT_CONCRETE_GRADES)
        )
        reinforcement = data.get("reinforcement") or {}
        grade_data = reinforcement.get("grades")
        grades = (
            [RebarGrade.from_dict(item) for item in grade_data]
            if isinstance(grade_data, list) and grade_data
            else list(DEFAULT_REBAR_GRADES)
        )
        size_data = reinforcement.get("sizes")
        sizes = (
            [RebarSize.from_dict(item) for item in size_data]
            if isinstance(size_data, list) and size_data
            else list(DEFAULT_REBAR_SIZES)
        )

        members: dict[DesignType, list[DesignMember]] = {}
        for design_type in DesignType:
            raw = data.get(design_type.project_key) or []
            members[design_type] = [
                DesignMember.from_dict(design_type, item) for item in raw if isinstance(item, dict)
            ]

        meta = data.get("metadata") or {}
        return cls(
            information=info,
            settings=settings,
            concretes=concretes,
            rebar_grades=grades,
            rebar_sizes=sizes,
            members=members,
            created_at=_str(meta, "created_at") or _now_iso(),
            modified_at=_str(meta, "modified_at") or _now_iso(),
            app_version=_str(meta, "app_version", APP_VERSION),
        )
