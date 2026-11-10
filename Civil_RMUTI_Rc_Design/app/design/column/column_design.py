"""Reinforced concrete column design module."""

from __future__ import annotations

from typing import Any

from app.calculations.column_calculation import (
    SHAPE_CIRCULAR,
    SHAPE_RECTANGULAR,
    ColumnCalculationEngine,
)
from app.core.constants import DesignType, Quantity
from app.design.base import BaseDesign
from app.design.fields import CHOICE, FieldSpec
from app.utils.validators import ValidationResult

_GEOMETRY = "Geometry"
_LOADS = "Factored Loads"


class ColumnDesign(BaseDesign):
    """RC column (rectangular or circular).

    Implemented: input definition, validation, geometry.
    Not implemented (Phase 3): axial-flexural strength check, slenderness,
    longitudinal and tie reinforcement design.
    """

    design_type = DesignType.COLUMN
    engine_class = ColumnCalculationEngine
    FIELD_SPECS = (
        FieldSpec("shape", "Section shape", default=SHAPE_RECTANGULAR, kind=CHOICE,
                  group=_GEOMETRY, choices=(SHAPE_RECTANGULAR, SHAPE_CIRCULAR)),
        FieldSpec("width", "Width b / diameter D", Quantity.LENGTH_MM, 300.0,
                  group=_GEOMETRY, minimum=0.0, maximum=5000.0,
                  tooltip="Section width (rectangular) or diameter (circular)."),
        FieldSpec("depth", "Depth h", Quantity.LENGTH_MM, 300.0, group=_GEOMETRY,
                  minimum=0.0, maximum=5000.0,
                  visible_when=("shape", (SHAPE_RECTANGULAR,))),
        FieldSpec("clear_height", "Clear height Lu", Quantity.LENGTH_MM, 3000.0,
                  group=_GEOMETRY, minimum=0.0, maximum=30000.0),
        FieldSpec("cover", "Clear concrete cover", Quantity.LENGTH_MM, 35.0,
                  group=_GEOMETRY, minimum=0.0, maximum=200.0),
        FieldSpec("axial_load", "Axial load Pu (compression +)", Quantity.FORCE, 0.0,
                  group=_LOADS, minimum=0.0, min_inclusive=True),
        FieldSpec("moment_x", "Moment Mux", Quantity.MOMENT, 0.0, group=_LOADS),
        FieldSpec("moment_y", "Moment Muy", Quantity.MOMENT, 0.0, group=_LOADS),
    )

    def _validate_specific(self, values: dict[str, Any], result: ValidationResult) -> None:
        """Cover must fit in the section; warn on unusually small sections."""
        least = values["width"] if values["shape"] == SHAPE_CIRCULAR else min(
            values["width"], values["depth"])
        if 2.0 * values["cover"] >= least:
            result.add_error(
                f"Column concrete cover ({values['cover']:g} mm) is too large for the "
                f"least section dimension ({least:g} mm)."
            )
        if least < 150.0:
            result.add_warning(f"Least column dimension {least:g} mm is unusually small.")
