"""Reinforcing steel grades and bar sizes.

Built-in grades follow the Thai Industrial Standards for reinforcing bars:
TIS 20 (มอก. 20) round bars SR24 and TIS 24 (มอก. 24) deformed bars
SD30 / SD40 / SD50, whose names give the minimum yield strength in
units of 100 kgf/cm². Users can add further grades in the material library.
"""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from typing import Any

from app.core.constants import KSC_TO_MPA

ROUND_BAR: str = "Round"
DEFORMED_BAR: str = "Deformed"
BAR_TYPES: tuple[str, ...] = (ROUND_BAR, DEFORMED_BAR)


def _optional_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    return float(value)


@dataclass(frozen=True)
class RebarGrade:
    """Reinforcing steel grade.

    Attributes:
        name: Grade name, e.g. ``"SD40"`` (unique identifier).
        fy_ksc: Minimum yield strength fy [kgf/cm²].
        bar_type: ``"Round"`` or ``"Deformed"``.
        standard: Product standard reference.
        fu_ksc: Optional minimum tensile strength fu [ksc].
        es_ksc: Optional user override of the modulus of elasticity [ksc];
            None means "use the selected design standard".
    """

    name: str
    fy_ksc: float
    bar_type: str
    standard: str = ""
    fu_ksc: float | None = None
    es_ksc: float | None = None

    @property
    def fy_mpa(self) -> float:
        """fy converted to MPa (exact unit conversion)."""
        return self.fy_ksc * KSC_TO_MPA

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a JSON compatible dict."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "RebarGrade":
        """Create an instance from a dict produced by :meth:`to_dict`."""
        return cls(
            name=str(data["name"]),
            fy_ksc=float(data["fy_ksc"]),
            bar_type=str(data.get("bar_type", DEFORMED_BAR)),
            standard=str(data.get("standard", "") or ""),
            fu_ksc=_optional_float(data.get("fu_ksc")),
            es_ksc=_optional_float(data.get("es_ksc")),
        )


@dataclass(frozen=True)
class RebarSize:
    """Nominal bar size.

    Attributes:
        designation: e.g. ``"DB16"`` (unique identifier).
        diameter_mm: Nominal diameter [mm].
        bar_type: ``"Round"`` or ``"Deformed"``.
    """

    designation: str
    diameter_mm: float
    bar_type: str

    @property
    def name(self) -> str:
        """Identifier (alias of :attr:`designation` for generic code)."""
        return self.designation

    @property
    def area_mm2(self) -> float:
        """Nominal cross-sectional area π·d²/4 [mm²]."""
        return math.pi * self.diameter_mm ** 2 / 4.0

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a JSON compatible dict."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "RebarSize":
        """Create an instance from a dict produced by :meth:`to_dict`."""
        return cls(
            designation=str(data["designation"]),
            diameter_mm=float(data["diameter_mm"]),
            bar_type=str(data.get("bar_type", DEFORMED_BAR)),
        )


DEFAULT_REBAR_GRADES: tuple[RebarGrade, ...] = (
    RebarGrade("SR24", 2400.0, ROUND_BAR, "TIS 20 (มอก. 20)"),
    RebarGrade("SD30", 3000.0, DEFORMED_BAR, "TIS 24 (มอก. 24)"),
    RebarGrade("SD40", 4000.0, DEFORMED_BAR, "TIS 24 (มอก. 24)"),
    RebarGrade("SD50", 5000.0, DEFORMED_BAR, "TIS 24 (มอก. 24)"),
)

DEFAULT_REBAR_SIZES: tuple[RebarSize, ...] = (
    RebarSize("RB6", 6.0, ROUND_BAR),
    RebarSize("RB9", 9.0, ROUND_BAR),
    RebarSize("RB12", 12.0, ROUND_BAR),
    RebarSize("DB10", 10.0, DEFORMED_BAR),
    RebarSize("DB12", 12.0, DEFORMED_BAR),
    RebarSize("DB16", 16.0, DEFORMED_BAR),
    RebarSize("DB20", 20.0, DEFORMED_BAR),
    RebarSize("DB25", 25.0, DEFORMED_BAR),
    RebarSize("DB28", 28.0, DEFORMED_BAR),
    RebarSize("DB32", 32.0, DEFORMED_BAR),
)
