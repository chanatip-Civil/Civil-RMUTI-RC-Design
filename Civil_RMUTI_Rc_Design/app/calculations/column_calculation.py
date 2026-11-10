"""Column calculation engine (Phase 1: geometry only).

Phase 3 will add the axial-flexural design check (interaction diagram,
slenderness, ties) according to the selected standard with clause references.
"""

from __future__ import annotations

import math
from typing import Any

from app.calculations.base_engine import CalculationContext, GeometryOnlyEngine
from app.core.constants import DesignType
from app.design.results import ResultItem

SHAPE_RECTANGULAR: str = "Rectangular"
SHAPE_CIRCULAR: str = "Circular"


class ColumnCalculationEngine(GeometryOnlyEngine):
    """Geometric properties of rectangular and circular columns."""

    design_type = DesignType.COLUMN
    engine_name = "Column engine v0.1 (geometry)"

    def geometry_items(self, inputs: dict[str, Any],
                       context: CalculationContext) -> list[ResultItem]:
        """Gross area, perimeter, volume and Lu/least-dimension ratio."""
        width = float(inputs["width"])
        height_mm = float(inputs["clear_height"])
        if inputs["shape"] == SHAPE_CIRCULAR:
            area = math.pi * width ** 2 / 4.0
            perimeter = math.pi * width
            least_dim = width
        else:
            depth = float(inputs["depth"])
            area = width * depth
            perimeter = 2.0 * (width + depth)
            least_dim = min(width, depth)
        return [
            ResultItem("Gross section area Ag", area, "mm²", f"= {area / 100.0:,.1f} cm²"),
            ResultItem("Section perimeter", perimeter, "mm"),
            ResultItem("Concrete volume (clear height)", area * height_mm / 1e9, "m³"),
            ResultItem("Clear height / least dimension", height_mm / least_dim, "-",
                       "Geometric ratio only; slenderness check per standard pending"),
        ]
