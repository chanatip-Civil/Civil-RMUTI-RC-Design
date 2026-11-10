"""Stair calculation engine (Phase 1: geometry only).

Phase 6 will add the structural design of the waist slab and landings
according to the selected standard with clause references.
"""

from __future__ import annotations

import math
from typing import Any

from app.calculations.base_engine import CalculationContext, GeometryOnlyEngine
from app.core.constants import DesignType
from app.design.results import ResultItem


class StairCalculationEngine(GeometryOnlyEngine):
    """Step geometry of a straight flight."""

    design_type = DesignType.STAIR
    engine_name = "Stair engine v0.1 (geometry)"

    def geometry_items(self, inputs: dict[str, Any],
                       context: CalculationContext) -> list[ResultItem]:
        """Number of risers, actual riser, going, slope and flight length."""
        floor_height = float(inputs["floor_height"])
        riser_target = float(inputs["riser"])
        tread = float(inputs["tread"])
        risers = max(1, math.ceil(floor_height / riser_target - 1e-9))
        actual_riser = floor_height / risers
        treads = risers - 1
        going = treads * tread
        slope_deg = math.degrees(math.atan2(actual_riser, tread))
        flight_length = math.hypot(going, floor_height - actual_riser) if treads else 0.0
        return [
            ResultItem("Number of risers", float(risers), "-"),
            ResultItem("Actual riser height", actual_riser, "mm"),
            ResultItem("Number of treads", float(treads), "-"),
            ResultItem("Total horizontal going", going, "mm"),
            ResultItem("Flight slope angle", slope_deg, "deg"),
            ResultItem("Inclined flight length (waist)", flight_length, "mm"),
        ]
