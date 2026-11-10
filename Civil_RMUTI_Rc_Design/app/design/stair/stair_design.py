"""Reinforced concrete stair design module."""

from __future__ import annotations

from typing import Any

from app.calculations.stair_calculation import StairCalculationEngine
from app.core.constants import DesignType, Quantity
from app.design.base import BaseDesign
from app.design.fields import CHOICE, FieldSpec
from app.utils.validators import ValidationResult

_GEOMETRY = "Geometry"
_LOADS = "Service Loads"


class StairDesign(BaseDesign):
    """RC stair flight.

    Implemented: input definition, validation, step geometry.
    Not implemented (Phase 6): load analysis and waist slab / landing design.
    """

    design_type = DesignType.STAIR
    engine_class = StairCalculationEngine
    FIELD_SPECS = (
        FieldSpec("stair_type", "Stair type", default="Straight flight", kind=CHOICE,
                  group=_GEOMETRY, choices=("Straight flight", "Dog-legged", "Cantilever steps")),
        FieldSpec("floor_height", "Floor-to-floor height (flight rise)", Quantity.LENGTH_MM,
                  1500.0, group=_GEOMETRY, minimum=0.0, maximum=10000.0),
        FieldSpec("riser", "Target riser height", Quantity.LENGTH_MM, 170.0, group=_GEOMETRY,
                  minimum=0.0, maximum=500.0),
        FieldSpec("tread", "Tread (going)", Quantity.LENGTH_MM, 250.0, group=_GEOMETRY,
                  minimum=0.0, maximum=1000.0),
        FieldSpec("waist", "Waist slab thickness", Quantity.LENGTH_MM, 150.0, group=_GEOMETRY,
                  minimum=0.0, maximum=1000.0),
        FieldSpec("stair_width", "Stair width", Quantity.LENGTH_MM, 1200.0, group=_GEOMETRY,
                  minimum=0.0, maximum=10000.0),
        FieldSpec("cover", "Clear concrete cover", Quantity.LENGTH_MM, 20.0, group=_GEOMETRY,
                  minimum=0.0, maximum=100.0),
        FieldSpec("finish_load", "Finishing load", Quantity.AREA_LOAD, 0.0, group=_LOADS,
                  minimum=0.0, min_inclusive=True),
        FieldSpec("live_load", "Live load", Quantity.AREA_LOAD, 0.0, group=_LOADS,
                  minimum=0.0, min_inclusive=True),
    )

    def _validate_specific(self, values: dict[str, Any], result: ValidationResult) -> None:
        """Riser must be lower than the flight rise; cover must fit the waist."""
        if values["riser"] >= values["floor_height"]:
            result.add_error("Stair riser height must be smaller than the flight rise.")
        if 2.0 * values["cover"] >= values["waist"]:
            result.add_error("Stair concrete cover is too large for the waist thickness.")
