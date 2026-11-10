"""Plain text calculation report (Phase 1).

Phase 8 replaces this with a formatted report generator (HTML/PDF) that
reuses the same :class:`DesignResult` data.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.core.constants import APP_NAME, APP_VERSION
from app.core.project_model import ProjectInformation
from app.design.fields import CHOICE

if TYPE_CHECKING:
    from app.design.base import BaseDesign

_WIDTH: int = 78


class TextReportBuilder:
    """Builds a monospaced text report for one design member."""

    def __init__(self, design: "BaseDesign", information: ProjectInformation) -> None:
        self._design = design
        self._info = information
        self._lines: list[str] = []

    def _rule(self, char: str = "-") -> None:
        self._lines.append(char * _WIDTH)

    def _title(self, text: str) -> None:
        self._lines.append("")
        self._lines.append(text.upper())
        self._rule()

    def build(self) -> str:
        """Return the complete report text."""
        design = self._design
        member = design.member
        info = self._info
        self._lines = []
        self._rule("=")
        self._lines.append(f"{APP_NAME}  v{APP_VERSION}".center(_WIDTH))
        self._lines.append(f"{design.design_type.description} - Calculation Sheet".center(_WIDTH))
        self._rule("=")
        rows = [
            ("Project", info.project_name), ("Project No.", info.project_number),
            ("Organization", info.organization), ("Designer", info.designer),
            ("Checker", info.checker), ("Date", info.project_date),
            ("Design standard", design.settings.standard.label),
            ("Unit system", design.settings.units.label),
            ("Member", f"{design.design_type.title} {member.name}"),
        ]
        for label, value in rows:
            self._lines.append(f"{label:<18}: {value}")

        self._title("1. Materials")
        concrete = design.project.find_concrete(member.concrete)
        main = design.project.find_rebar_grade(member.main_rebar)
        tie = design.project.find_rebar_grade(member.tie_rebar)
        self._lines.append(f"{'Concrete':<18}: {member.concrete}"
                           + (f"  (f'c = {concrete.fc_ksc:g} ksc)" if concrete else ""))
        self._lines.append(f"{'Main bars':<18}: {member.main_rebar}"
                           + (f"  (fy = {main.fy_ksc:g} ksc)" if main else ""))
        self._lines.append(f"{'Ties / stirrups':<18}: {member.tie_rebar}"
                           + (f"  (fy = {tie.fy_ksc:g} ksc)" if tie else ""))

        self._title("2. Input data")
        for spec in design.FIELD_SPECS:
            if not spec.is_active(member.inputs):
                continue
            value = member.inputs.get(spec.key, "")
            if isinstance(value, float):
                value = f"{value:g}"
            unit = "" if spec.kind == CHOICE else design.unit_for(spec)
            self._lines.append(f"{spec.label:<40} = {value} {unit}".rstrip())

        self._title("3. Input validation")
        validation = design.validate()
        if validation.is_valid:
            self._lines.append("All inputs are valid.")
        for message in validation.errors:
            self._lines.append(f"[ERROR]   {message}")
        for message in validation.warnings:
            self._lines.append(f"[WARNING] {message}")

        self._title("4. Results")
        result = design.last_result
        self._lines.append(f"Status : {result.status.label}")
        if result.calculated_at and result.engine:
            self._lines.append(f"Engine : {result.engine}  ({result.calculated_at})")
        if result.summary:
            self._lines.append(f"Summary: {result.summary}")
        if result.items:
            self._lines.append("")
            for item in result.items:
                note = f"  [{item.note}]" if item.note else ""
                self._lines.append(
                    f"{item.label:<40} = {item.formatted_value():>14} {item.unit}{note}"
                )
        if result.messages:
            self._lines.append("")
            for message in result.messages:
                self._lines.append(f"- {message}")

        self._lines.append("")
        self._rule("=")
        self._lines.append("NOTE: structural design checks per the selected standard are not implemented yet.")
        self._rule("=")
        return "\n".join(self._lines)
