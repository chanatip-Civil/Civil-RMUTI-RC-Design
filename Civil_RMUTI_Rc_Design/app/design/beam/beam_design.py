"""Reinforced concrete beam design module."""

from __future__ import annotations

from typing import Any

from app.calculations.beam_calculation import BeamCalculationEngine
from app.core.constants import DesignType, Quantity
from app.design.base import BaseDesign
from app.design.fields import CHOICE, FieldSpec
from app.utils.validators import ValidationResult

_GEOMETRY = "Geometry"
_LOADS = "Factored Actions"


class BeamDesign(BaseDesign):
    """RC rectangular beam.

    Implemented: input definition, validation, geometry.
    Not implemented (Phase 4): flexure, shear, torsion, deflection and
    detailing checks.
    """

    design_type = DesignType.BEAM
    engine_class = BeamCalculationEngine
    FIELD_SPECS = (
        FieldSpec("support", "Support condition", default="Continuous", kind=CHOICE,
                  group=_GEOMETRY, choices=("Simply supported", "Continuous", "Cantilever")),
        FieldSpec("width", "Width b", Quantity.LENGTH_MM, 250.0, group=_GEOMETRY,
                  minimum=0.0, maximum=3000.0),
        FieldSpec("depth", "Total depth h", Quantity.LENGTH_MM, 500.0, group=_GEOMETRY,
                  minimum=0.0, maximum=5000.0),
        FieldSpec("span", "Span length L", Quantity.LENGTH_M, 5.0, group=_GEOMETRY,
                  minimum=0.0, maximum=50.0),
        FieldSpec("cover", "Clear concrete cover", Quantity.LENGTH_MM, 30.0,
                  group=_GEOMETRY, minimum=0.0, maximum=200.0),
        FieldSpec("moment_positive", "Positive moment Mu+", Quantity.MOMENT, 0.0,
                  group=_LOADS, minimum=0.0, min_inclusive=True),
        FieldSpec("moment_negative", "Negative moment Mu- (magnitude)", Quantity.MOMENT, 0.0,
                  group=_LOADS, minimum=0.0, min_inclusive=True),
        FieldSpec("shear", "Shear force Vu", Quantity.FORCE, 0.0, group=_LOADS,
                  minimum=0.0, min_inclusive=True),
    )

    def _validate_specific(self, values: dict[str, Any], result: ValidationResult) -> None:
        """Cover must fit in the section."""
        if 2.0 * values["cover"] >= min(values["width"], values["depth"]):
            result.add_error("Beam concrete cover is too large for the section dimensions.")
        if values["depth"] < values["width"]:
            result.add_warning("Beam depth is smaller than its width (check input order).")
