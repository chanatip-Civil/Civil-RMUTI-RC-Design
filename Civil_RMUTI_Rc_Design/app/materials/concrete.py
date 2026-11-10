"""Concrete material definition.

Stored properties are user data. Properties that depend on the design
standard (e.g. the modulus of elasticity Ec) are **not** derived here: the
user may enter an override value, otherwise the standard-specific calculation
engines (Phase 3+) compute them with clause references.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from app.core.constants import KSC_TO_MPA

#: Editable default unit weight of reinforced concrete [kg/m³] for new grades.
#: It is a user default, not a design-code value; change it per grade if needed.
DEFAULT_UNIT_WEIGHT_KG_M3: float = 2400.0


def _optional_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    return float(value)


@dataclass(frozen=True)
class Concrete:
    """Concrete grade.

    Attributes:
        name: Grade name, e.g. ``"fc' 240 ksc"`` (unique identifier).
        fc_ksc: Specified cylinder compressive strength f'c [kgf/cm²].
        description: Free text.
        unit_weight_kg_m3: Unit weight used for self-weight [kg/m³].
        ec_ksc: Optional user override of the modulus of elasticity [ksc];
            None means "use the selected design standard".
    """

    name: str
    fc_ksc: float
    description: str = ""
    unit_weight_kg_m3: float = DEFAULT_UNIT_WEIGHT_KG_M3
    ec_ksc: float | None = None

    @property
    def fc_mpa(self) -> float:
        """f'c converted to MPa (exact unit conversion)."""
        return self.fc_ksc * KSC_TO_MPA

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a JSON compatible dict."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Concrete":
        """Create an instance from a dict produced by :meth:`to_dict`."""
        return cls(
            name=str(data["name"]),
            fc_ksc=float(data["fc_ksc"]),
            description=str(data.get("description", "") or ""),
            unit_weight_kg_m3=float(data.get("unit_weight_kg_m3", DEFAULT_UNIT_WEIGHT_KG_M3)),
            ec_ksc=_optional_float(data.get("ec_ksc")),
        )


# Commonly specified cylinder strengths in Thai practice. These are just
# selectable grades (user data), not design-code values.
DEFAULT_CONCRETE_GRADES: tuple[Concrete, ...] = (
    Concrete("fc' 180 ksc", 180.0, "Cylinder strength 180 ksc"),
    Concrete("fc' 210 ksc", 210.0, "Cylinder strength 210 ksc"),
    Concrete("fc' 240 ksc", 240.0, "Cylinder strength 240 ksc"),
    Concrete("fc' 280 ksc", 280.0, "Cylinder strength 280 ksc"),
    Concrete("fc' 320 ksc", 320.0, "Cylinder strength 320 ksc"),
)
