"""Declarative schema of every material kind.

The schema drives validation, conversion between raw form values and
material objects, and table/form generation in any user interface
(desktop now, web later). All material items expose a unique ``name``.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Union

from app.materials.concrete import DEFAULT_UNIT_WEIGHT_KG_M3, Concrete
from app.materials.reinforcement import BAR_TYPES, DEFORMED_BAR, RebarGrade, RebarSize
from app.utils.validators import (
    ValidationResult,
    is_blank,
    parse_number,
    validate_choice,
    validate_number,
    validate_required_text,
)

MaterialItem = Union[Concrete, RebarGrade, RebarSize]

TEXT: str = "text"
NUMBER: str = "number"
OPTIONAL_NUMBER: str = "optional_number"
CHOICE: str = "choice"

MAX_NAME_LENGTH: int = 40


class MaterialKind(str, Enum):
    """Kinds of material data."""

    CONCRETE = "concrete"
    REBAR_GRADE = "rebar_grade"
    REBAR_SIZE = "rebar_size"

    @property
    def title(self) -> str:
        """Readable plural title."""
        return {
            MaterialKind.CONCRETE: "Concrete",
            MaterialKind.REBAR_GRADE: "Reinforcement Grades",
            MaterialKind.REBAR_SIZE: "Bar Sizes",
        }[self]

    @property
    def singular(self) -> str:
        """Readable singular name used in messages."""
        return {
            MaterialKind.CONCRETE: "Concrete grade",
            MaterialKind.REBAR_GRADE: "Reinforcement grade",
            MaterialKind.REBAR_SIZE: "Bar size",
        }[self]


@dataclass(frozen=True)
class MaterialField:
    """One editable property of a material kind."""

    key: str
    label: str
    kind: str = NUMBER
    unit: str = ""
    default: Any = None
    minimum: float | None = None
    maximum: float | None = None
    choices: tuple[str, ...] = ()
    tooltip: str = ""


@dataclass(frozen=True)
class DisplayColumn:
    """Column shown in material tables."""

    header: str
    getter: Callable[[Any], str]


def _fmt(value: float | None, digits: int = 0) -> str:
    if value is None:
        return "—"
    return f"{value:,.{digits}f}" if digits else f"{value:g}"


@dataclass(frozen=True)
class MaterialSchema:
    """Fields, columns and factory of one material kind."""

    kind: MaterialKind
    item_class: type
    id_key: str
    fields: tuple[MaterialField, ...]
    columns: tuple[DisplayColumn, ...]

    def defaults(self) -> dict[str, Any]:
        """Default raw values for a new item."""
        return {f.key: f.default for f in self.fields}

    def to_values(self, item: MaterialItem) -> dict[str, Any]:
        """Raw values of an existing *item*."""
        return item.to_dict()

    def row(self, item: MaterialItem) -> list[str]:
        """Table row texts of *item*."""
        return [column.getter(item) for column in self.columns]

    def validate(self, values: dict[str, Any]) -> tuple[ValidationResult, MaterialItem | None]:
        """Validate raw *values* and build the item when valid."""
        result = ValidationResult()
        parsed: dict[str, Any] = {}
        prefix = self.kind.singular
        for spec in self.fields:
            label = f"{prefix} {spec.label[0].lower()}{spec.label[1:]}"
            raw = values.get(spec.key)
            if spec.kind == TEXT:
                text = "" if raw is None else str(raw).strip()
                if spec.key == self.id_key:
                    validate_required_text(text, label, result, MAX_NAME_LENGTH)
                elif len(text) > 200:
                    result.add_error(f"{label} must not exceed 200 characters.")
                parsed[spec.key] = text
            elif spec.kind == CHOICE:
                parsed[spec.key] = validate_choice(raw, label, list(spec.choices), result)
            else:
                optional = spec.kind == OPTIONAL_NUMBER
                if optional and is_blank(raw):
                    parsed[spec.key] = None
                    continue
                parsed[spec.key] = validate_number(
                    raw, label, spec.unit, result, required=not optional,
                    minimum=spec.minimum, maximum=spec.maximum,
                )
        if result.is_valid:
            _CROSS_CHECKS.get(self.kind, lambda p, r: None)(parsed, result)
        if not result.is_valid:
            return result, None
        return result, self.item_class.from_dict(parsed)


def _check_rebar_grade(parsed: dict[str, Any], result: ValidationResult) -> None:
    fu = parsed.get("fu_ksc")
    if fu is not None and fu < parsed["fy_ksc"]:
        result.add_error("Reinforcement grade tensile strength fu must not be less than fy.")


_CROSS_CHECKS: dict[MaterialKind, Callable[[dict[str, Any], ValidationResult], None]] = {
    MaterialKind.REBAR_GRADE: _check_rebar_grade,
}

_STANDARD_HINT = "Leave blank to use the value of the selected design standard."

SCHEMAS: dict[MaterialKind, MaterialSchema] = {
    MaterialKind.CONCRETE: MaterialSchema(
        kind=MaterialKind.CONCRETE,
        item_class=Concrete,
        id_key="name",
        fields=(
            MaterialField("name", "Name", TEXT, default="", tooltip="Unique grade name"),
            MaterialField("fc_ksc", "Compressive strength f'c", NUMBER, "ksc", 240.0,
                          minimum=0.0, maximum=2000.0,
                          tooltip="Specified cylinder compressive strength"),
            MaterialField("unit_weight_kg_m3", "Unit weight", NUMBER, "kg/m³",
                          DEFAULT_UNIT_WEIGHT_KG_M3, minimum=0.0, maximum=5000.0),
            MaterialField("ec_ksc", "Modulus of elasticity Ec (override)", OPTIONAL_NUMBER,
                          "ksc", None, minimum=0.0, maximum=1.0e7, tooltip=_STANDARD_HINT),
            MaterialField("description", "Description", TEXT, default=""),
        ),
        columns=(
            DisplayColumn("Name", lambda c: c.name),
            DisplayColumn("f'c (ksc)", lambda c: _fmt(c.fc_ksc)),
            DisplayColumn("f'c (MPa)", lambda c: f"{c.fc_mpa:.2f}"),
            DisplayColumn("Unit wt (kg/m³)", lambda c: _fmt(c.unit_weight_kg_m3)),
            DisplayColumn("Ec (ksc)", lambda c: _fmt(c.ec_ksc) if c.ec_ksc else "by standard"),
            DisplayColumn("Description", lambda c: c.description),
        ),
    ),
    MaterialKind.REBAR_GRADE: MaterialSchema(
        kind=MaterialKind.REBAR_GRADE,
        item_class=RebarGrade,
        id_key="name",
        fields=(
            MaterialField("name", "Name", TEXT, default=""),
            MaterialField("bar_type", "Bar type", CHOICE, default=DEFORMED_BAR, choices=BAR_TYPES),
            MaterialField("fy_ksc", "Yield strength fy", NUMBER, "ksc", 4000.0,
                          minimum=0.0, maximum=20000.0),
            MaterialField("fu_ksc", "Tensile strength fu", OPTIONAL_NUMBER, "ksc", None,
                          minimum=0.0, maximum=30000.0),
            MaterialField("es_ksc", "Modulus of elasticity Es (override)", OPTIONAL_NUMBER,
                          "ksc", None, minimum=0.0, maximum=1.0e8, tooltip=_STANDARD_HINT),
            MaterialField("standard", "Product standard", TEXT, default=""),
        ),
        columns=(
            DisplayColumn("Name", lambda g: g.name),
            DisplayColumn("Bar type", lambda g: g.bar_type),
            DisplayColumn("fy (ksc)", lambda g: _fmt(g.fy_ksc)),
            DisplayColumn("fy (MPa)", lambda g: f"{g.fy_mpa:.1f}"),
            DisplayColumn("fu (ksc)", lambda g: _fmt(g.fu_ksc)),
            DisplayColumn("Es (ksc)", lambda g: _fmt(g.es_ksc) if g.es_ksc else "by standard"),
            DisplayColumn("Product standard", lambda g: g.standard),
        ),
    ),
    MaterialKind.REBAR_SIZE: MaterialSchema(
        kind=MaterialKind.REBAR_SIZE,
        item_class=RebarSize,
        id_key="designation",
        fields=(
            MaterialField("designation", "Designation", TEXT, default=""),
            MaterialField("bar_type", "Bar type", CHOICE, default=DEFORMED_BAR, choices=BAR_TYPES),
            MaterialField("diameter_mm", "Nominal diameter", NUMBER, "mm", 12.0,
                          minimum=0.0, maximum=100.0),
        ),
        columns=(
            DisplayColumn("Designation", lambda s: s.designation),
            DisplayColumn("Bar type", lambda s: s.bar_type),
            DisplayColumn("Diameter (mm)", lambda s: _fmt(s.diameter_mm)),
            DisplayColumn("Area (mm²)", lambda s: f"{s.area_mm2:.1f}"),
        ),
    ),
}


def schema_for(kind: MaterialKind) -> MaterialSchema:
    """Return the schema of *kind*."""
    return SCHEMAS[kind]


def item_from_dict(kind: MaterialKind, data: dict[str, Any]) -> MaterialItem:
    """Build an item of *kind* from serialized data."""
    return SCHEMAS[kind].item_class.from_dict(data)


def number_or_text(value: Any) -> Any:
    """Return a float if *value* parses as a number, else the stripped text."""
    number = parse_number(value)
    if number is not None:
        return number
    return "" if value is None else str(value).strip()
