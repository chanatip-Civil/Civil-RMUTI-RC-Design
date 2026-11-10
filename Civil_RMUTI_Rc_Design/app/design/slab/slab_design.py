"""Reinforced concrete slab design module."""

from __future__ import annotations

from typing import Any

from app.calculations.slab_calculation import SlabCalculationEngine
from app.core.constants import DesignType, Quantity
from app.design.base import BaseDesign
from app.design.fields import CHOICE, FieldSpec
from app.utils.validators import ValidationResult

_GEOMETRY = "Geometry"
_LOADS = "Service Loads"


class SlabDesign(BaseDesign):
    """RC slab panel.

    Implemented: input definition, validation, geometry.
    Not implemented (Phase 5): moment coefficients / analysis, flexural
    reinforcement, minimum thickness and crack control checks.
    """

    design_type = DesignType.SLAB
    engine_class = SlabCalculationEngine
    FIELD_SPECS = (
        FieldSpec("slab_type", "Slab type", default="Two-way", kind=CHOICE, group=_GEOMETRY,
                  choices=("One-way", "Two-way", "Cantilever")),
        FieldSpec("thickness", "Thickness t", Quantity.LENGTH_MM, 120.0, group=_GEOMETRY,
                  minimum=0.0, maximum=1000.0),
        FieldSpec("short_span", "Short span Lx", Quantity.LENGTH_M, 4.0, group=_GEOMETRY,
                  minimum=0.0, maximum=30.0),
        FieldSpec("long_span", "Long span Ly", Quantity.LENGTH_M, 5.0, group=_GEOMETRY,
                  minimum=0.0, maximum=30.0),
        FieldSpec("cover", "Clear concrete cover", Quantity.LENGTH_MM, 20.0,
                  group=_GEOMETRY, minimum=0.0, maximum=100.0),
        FieldSpec("superimposed_dead_load", "Superimposed dead load", Quantity.AREA_LOAD,
                  0.0, group=_LOADS, minimum=0.0, min_inclusive=True),
        FieldSpec("live_load", "Live load", Quantity.AREA_LOAD, 0.0, group=_LOADS,
                  minimum=0.0, min_inclusive=True),
    )

    def _validate_specific(self, values: dict[str, Any], result: ValidationResult) -> None:
        """Lx must not exceed Ly; cover must fit in the thickness."""
        if values["short_span"] > values["long_span"]:
            result.add_error("Slab short span Lx must not be greater than long span Ly.")
        if 2.0 * values["cover"] >= values["thickness"]:
            result.add_error("Slab concrete cover is too large for the slab thickness.")
