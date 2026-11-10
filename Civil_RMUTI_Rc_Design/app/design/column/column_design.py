"""Reinforced concrete column design module."""

from __future__ import annotations

from typing import Any

from app.calculations.column_calculation import (
    FRAME_NONSWAY,
    FRAME_SWAY,
    SHAPE_CIRCULAR,
    SHAPE_RECTANGULAR,
    TIES_SPIRAL,
    TIES_TIED,
    ColumnCalculationEngine,
)
from app.core.constants import DesignType, Quantity
from app.design.base import BaseDesign
from app.design.fields import CHOICE, INTEGER, FieldSpec
from app.utils.validators import ValidationResult

_GEOMETRY = "Geometry"
_LOADS = "Factored Loads"
_REINF = "Reinforcement"
_SLENDER = "Slenderness"


class ColumnDesign(BaseDesign):
    """RC column (rectangular or circular).

    Implemented: input definition, validation, geometry and (ACI 318-19)
    the axial strength and detailing check of short columns.
    Not implemented: combined axial + moment, slender column design.
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
        FieldSpec("tie_type", "Lateral reinforcement", default=TIES_TIED, kind=CHOICE,
                  group=_REINF, choices=(TIES_TIED, TIES_SPIRAL),
                  tooltip="Spirals are only available for circular columns."),
        FieldSpec("bar_count", "Number of main bars", Quantity.NONE, 8.0, kind=INTEGER,
                  group=_REINF, minimum=1.0, min_inclusive=True, maximum=200.0),
        FieldSpec("bar_diameter", "Main bar diameter db", Quantity.LENGTH_MM, 16.0,
                  group=_REINF, minimum=0.0, maximum=60.0),
        FieldSpec("tie_diameter", "Tie / spiral bar diameter", Quantity.LENGTH_MM, 10.0,
                  group=_REINF, minimum=0.0, maximum=40.0),
        FieldSpec("tie_spacing", "Tie spacing / spiral pitch s", Quantity.LENGTH_MM, 200.0,
                  group=_REINF, minimum=0.0, maximum=1000.0),
        FieldSpec("frame_type", "Frame type", default=FRAME_NONSWAY, kind=CHOICE,
                  group=_SLENDER, choices=(FRAME_NONSWAY, FRAME_SWAY)),
        FieldSpec("k_factor", "Effective length factor k", Quantity.NONE, 1.0,
                  group=_SLENDER, minimum=0.0, maximum=10.0,
                  tooltip="ACI 318-19 6.2.5.1: k may be taken as 1.0 for nonsway members."),
        FieldSpec("m1_m2", "End moment ratio M1/M2", Quantity.NONE, -1.0,
                  group=_SLENDER, minimum=-1.0, min_inclusive=True, maximum=1.0,
                  visible_when=("frame_type", (FRAME_NONSWAY,)),
                  tooltip="Negative for single curvature (ACI 318-19 6.2.5.1). "
                          "-1.0 is the most conservative value."),
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
        if values["tie_type"] == TIES_SPIRAL and values["shape"] != SHAPE_CIRCULAR:
            result.add_error("Column spiral reinforcement is only supported for circular sections.")
        if values["tie_diameter"] + values["bar_diameter"] + values["cover"] >= least / 2.0:
            result.add_error("Column bars and cover do not fit in the section.")
        if least < 150.0:
            result.add_warning(f"Least column dimension {least:g} mm is unusually small.")
