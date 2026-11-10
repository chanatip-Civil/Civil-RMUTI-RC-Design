"""Slab calculation engine (Phase 1: geometry only).

Phase 5 will add one-way / two-way slab analysis and design according to the
selected standard with clause references.
"""

from __future__ import annotations

from typing import Any

from app.calculations.base_engine import CalculationContext, GeometryOnlyEngine
from app.core.constants import DesignType
from app.design.results import ResultItem


class SlabCalculationEngine(GeometryOnlyEngine):
    """Geometric properties of rectangular slab panels."""

    design_type = DesignType.SLAB
    engine_name = "Slab engine v0.1 (geometry)"

    def geometry_items(self, inputs: dict[str, Any],
                       context: CalculationContext) -> list[ResultItem]:
        """Panel area, volume and long/short span ratio."""
        lx = float(inputs["short_span"])
        ly = float(inputs["long_span"])
        thickness = float(inputs["thickness"])
        area = lx * ly
        return [
            ResultItem("Panel area", area, "m²"),
            ResultItem("Concrete volume", area * thickness / 1000.0, "m³"),
            ResultItem("Long / short span ratio Ly/Lx", ly / lx, "-"),
            ResultItem("Short span / thickness", lx * 1000.0 / thickness, "-",
                       "Geometric ratio only; minimum thickness check per standard pending"),
        ]
