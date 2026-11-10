"""Reinforced concrete footing design module."""

from __future__ import annotations

from typing import Any

from app.calculations.footing_calculation import FootingCalculationEngine
from app.core.constants import DesignType, Quantity
from app.design.base import BaseDesign
from app.design.fields import CHOICE, FieldSpec
from app.utils.validators import ValidationResult

_GEOMETRY = "Geometry"
_COLUMN = "Supported Column"
_LOADS = "Loads and Soil"


class FootingDesign(BaseDesign):
    """RC isolated spread footing.

    Implemented: input definition, validation, geometry, average pressure.
    Not implemented (Phase 7): bearing, punching / one-way shear and flexure
    checks, pile caps.
    """

    design_type = DesignType.FOOTING
    engine_class = FootingCalculationEngine
    FIELD_SPECS = (
        FieldSpec("footing_type", "Footing type", default="Isolated spread footing",
                  kind=CHOICE, group=_GEOMETRY, choices=("Isolated spread footing",)),
        FieldSpec("width", "Footing width B", Quantity.LENGTH_M, 1.5, group=_GEOMETRY,
                  minimum=0.0, maximum=20.0),
        FieldSpec("length", "Footing length L", Quantity.LENGTH_M, 1.5, group=_GEOMETRY,
                  minimum=0.0, maximum=20.0),
        FieldSpec("thickness", "Footing thickness t", Quantity.LENGTH_MM, 500.0,
                  group=_GEOMETRY, minimum=0.0, maximum=5000.0),
        FieldSpec("embedment", "Depth of footing base Df", Quantity.LENGTH_M, 1.5,
                  group=_GEOMETRY, minimum=0.0, maximum=20.0),
        FieldSpec("cover", "Clear concrete cover", Quantity.LENGTH_MM, 75.0, group=_GEOMETRY,
                  minimum=0.0, maximum=200.0),
        FieldSpec("column_width", "Column width cx", Quantity.LENGTH_MM, 300.0, group=_COLUMN,
                  minimum=0.0, maximum=5000.0),
        FieldSpec("column_depth", "Column depth cy", Quantity.LENGTH_MM, 300.0, group=_COLUMN,
                  minimum=0.0, maximum=5000.0),
        FieldSpec("service_load", "Service axial load P", Quantity.FORCE, 0.0, group=_LOADS,
                  minimum=0.0, min_inclusive=True),
        FieldSpec("service_moment", "Service moment M", Quantity.MOMENT, 0.0, group=_LOADS),
        FieldSpec("allowable_bearing", "Allowable soil bearing qa", Quantity.AREA_LOAD,
                  100.0, group=_LOADS, minimum=0.0),
    )

    def _validate_specific(self, values: dict[str, Any], result: ValidationResult) -> None:
        """Column must fit on the footing; cover must fit in the thickness."""
        if values["column_width"] >= values["width"] * 1000.0:
            result.add_error("Column width must be smaller than footing width B.")
        if values["column_depth"] >= values["length"] * 1000.0:
            result.add_error("Column depth must be smaller than footing length L.")
        if 2.0 * values["cover"] >= values["thickness"]:
            result.add_error("Footing concrete cover is too large for the footing thickness.")
        if values["embedment"] * 1000.0 < values["thickness"]:
            result.add_warning("Footing base depth Df is less than the footing thickness.")
