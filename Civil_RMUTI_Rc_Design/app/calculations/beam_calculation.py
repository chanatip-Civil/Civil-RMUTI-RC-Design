"""Beam calculation engine (Phase 1: geometry only).

Phase 4 will add flexure, shear and serviceability checks according to the
selected standard with clause references.
"""

from __future__ import annotations

from typing import Any

from app.calculations.base_engine import CalculationContext, GeometryOnlyEngine
from app.core.constants import DesignType
from app.design.results import ResultItem


class BeamCalculationEngine(GeometryOnlyEngine):
    """Geometric properties of rectangular beams."""

    design_type = DesignType.BEAM
    engine_name = "Beam engine v0.1 (geometry)"

    def geometry_items(self, inputs: dict[str, Any],
                       context: CalculationContext) -> list[ResultItem]:
        """Gross area, volume, span/depth ratio."""
        width = float(inputs["width"])
        depth = float(inputs["depth"])
        span_m = float(inputs["span"])
        area = width * depth
        return [
            ResultItem("Gross section area Ag", area, "mm²", f"= {area / 100.0:,.1f} cm²"),
            ResultItem("Concrete volume", area * span_m / 1e6, "m³"),
            ResultItem("Span / total depth", span_m * 1000.0 / depth, "-",
                       "Geometric ratio only; deflection check per standard pending"),
            ResultItem("Clear cover to depth ratio", float(inputs["cover"]) / depth, "-"),
        ]
