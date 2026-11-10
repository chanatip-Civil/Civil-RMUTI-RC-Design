"""Footing calculation engine (Phase 1: geometry only).

Phase 7 will add bearing, punching shear, one-way shear and flexure checks
according to the selected standard with clause references.
"""

from __future__ import annotations

from typing import Any

from app.calculations.base_engine import CalculationContext, GeometryOnlyEngine
from app.core.constants import DesignType, Quantity
from app.design.results import ResultItem


class FootingCalculationEngine(GeometryOnlyEngine):
    """Geometry of an isolated rectangular spread footing."""

    design_type = DesignType.FOOTING
    engine_name = "Footing engine v0.1 (geometry)"

    def geometry_items(self, inputs: dict[str, Any],
                       context: CalculationContext) -> list[ResultItem]:
        """Plan area, volume and average service pressure P/A."""
        width = float(inputs["width"])
        length = float(inputs["length"])
        thickness = float(inputs["thickness"])
        area = width * length
        pressure_unit = context.unit(Quantity.AREA_LOAD)
        return [
            ResultItem("Footing plan area", area, "m²"),
            ResultItem("Concrete volume", area * thickness / 1000.0, "m³"),
            ResultItem("Average pressure P/A", float(inputs["service_load"]) / area,
                       pressure_unit, "Service load only; excludes self-weight, soil and moment"),
            ResultItem("Allowable soil bearing (input)", float(inputs["allowable_bearing"]),
                       pressure_unit, "Bearing check per standard pending"),
        ]
