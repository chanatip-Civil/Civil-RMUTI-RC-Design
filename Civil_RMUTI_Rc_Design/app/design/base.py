"""Abstract base class of all member design modules.

A design module combines:

* ``FIELD_SPECS`` - the input definition (used by validation and the GUI),
* ``validate()``  - generic + member-specific input checks,
* ``calculate()`` - runs the member's :class:`CalculationEngine`,
* ``generate_report()`` - plain text calculation report.

Concrete modules only declare their fields, engine and specific checks.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, ClassVar

from app.calculations.base_engine import CalculationContext, CalculationEngine
from app.core.constants import DesignType, unit_label
from app.core.exceptions import CalculationError, InputValidationError
from app.core.logger import get_logger
from app.core.project_model import DesignMember, DesignSettings, Project, ProjectInformation
from app.design.fields import CHOICE, INTEGER, FieldSpec
from app.design.results import DesignResult, DesignStatus
from app.utils.validators import (
    ValidationResult,
    parse_number,
    validate_choice,
    validate_number,
)

_log = get_logger("design")


class BaseDesign(ABC):
    """Common behaviour of Column, Beam, Slab, Stair and Footing designs."""

    design_type: ClassVar[DesignType]
    engine_class: ClassVar[type[CalculationEngine]]
    FIELD_SPECS: ClassVar[tuple[FieldSpec, ...]] = ()

    def __init__(self, member: DesignMember, project: Project) -> None:
        """Create a design wrapper around *member* of *project*."""
        if member.design_type != self.design_type:
            raise ValueError(
                f"{type(self).__name__} cannot handle a {member.design_type.title} member."
            )
        self.member: DesignMember = member
        self.project: Project = project
        self.engine: CalculationEngine = self.engine_class()

    # ----------------------------------------------------------------- inputs
    @property
    def settings(self) -> DesignSettings:
        """Project design settings."""
        return self.project.settings

    @classmethod
    def default_inputs(cls) -> dict[str, Any]:
        """Default input values for a new member."""
        return {spec.key: spec.default for spec in cls.FIELD_SPECS}

    @classmethod
    def field_spec(cls, key: str) -> FieldSpec:
        """Return the spec for *key* (KeyError if unknown)."""
        for spec in cls.FIELD_SPECS:
            if spec.key == key:
                return spec
        raise KeyError(key)

    @classmethod
    def create_member(cls, project: Project, name: str | None = None) -> DesignMember:
        """Create (but do not add) a new member with default inputs and materials."""
        return DesignMember(
            design_type=cls.design_type,
            name=name or project.next_member_name(cls.design_type),
            inputs=cls.default_inputs(),
            concrete=project.settings.default_concrete,
            main_rebar=project.settings.default_main_rebar,
            tie_rebar=project.settings.default_tie_rebar,
        )

    def unit_for(self, spec: FieldSpec) -> str:
        """Unit label of *spec* in the project unit system."""
        return unit_label(spec.quantity, self.settings.units)

    # ------------------------------------------------------------- validation
    def parse_inputs(self) -> tuple[dict[str, Any], ValidationResult]:
        """Parse and validate raw inputs field by field.

        Returns:
            ``(values, result)`` where *values* holds parsed numbers/strings
            of active fields that passed their individual checks.
        """
        raw = self.member.inputs
        values: dict[str, Any] = {}
        result = ValidationResult()
        for spec in self.FIELD_SPECS:
            if not spec.is_active(raw):
                continue
            value = raw.get(spec.key)
            errors = self.check_field(spec, value)
            if errors:
                for message in errors:
                    result.add_error(message)
                continue
            values[spec.key] = (
                str(value) if spec.kind == CHOICE else float(parse_number(value))  # type: ignore[arg-type]
            )
        return values, result

    def check_field(self, spec: FieldSpec, value: Any) -> list[str]:
        """Validate a single raw *value* against *spec* (used for highlighting)."""
        result = ValidationResult()
        label = f"{self.design_type.title} {spec.label[0].lower()}{spec.label[1:]}"
        if spec.kind == CHOICE:
            validate_choice(value, label, list(spec.choices), result)
        else:
            validate_number(
                value, label, self.unit_for(spec), result,
                required=spec.required, minimum=spec.minimum, maximum=spec.maximum,
                min_inclusive=spec.min_inclusive, integer=spec.kind == INTEGER,
            )
        return result.errors

    def validate(self) -> ValidationResult:
        """Validate name, materials, every field and member-specific rules."""
        values, result = self.parse_inputs()
        if not self.member.name.strip():
            result.add_error(f"{self.design_type.title} name is required.")
        if self.project.find_concrete(self.member.concrete) is None:
            result.add_error(f"Concrete grade '{self.member.concrete}' is not defined in the project.")
        if self.project.find_rebar_grade(self.member.main_rebar) is None:
            result.add_error(f"Main reinforcement grade '{self.member.main_rebar}' is not defined.")
        if self.project.find_rebar_grade(self.member.tie_rebar) is None:
            result.add_error(f"Tie/stirrup grade '{self.member.tie_rebar}' is not defined.")
        # Cross-field checks only make sense when all required values parsed.
        if result.is_valid:
            self._validate_specific(values, result)
        return result

    @abstractmethod
    def _validate_specific(self, values: dict[str, Any], result: ValidationResult) -> None:
        """Member-specific consistency checks on parsed *values*."""

    # ------------------------------------------------------------ calculation
    def build_context(self) -> CalculationContext:
        """Assemble the calculation context from project data."""
        return CalculationContext(
            standard=self.settings.standard,
            unit_system=self.settings.units,
            concrete=self.project.find_concrete(self.member.concrete),
            main_rebar=self.project.find_rebar_grade(self.member.main_rebar),
            tie_rebar=self.project.find_rebar_grade(self.member.tie_rebar),
        )

    def calculate(self) -> DesignResult:
        """Validate, run the engine and store the result on the member.

        Raises:
            InputValidationError: If the inputs are invalid.
            CalculationError: If the engine fails unexpectedly.
        """
        validation = self.validate()
        if not validation.is_valid:
            raise InputValidationError(validation.errors)
        values, _ = self.parse_inputs()
        try:
            result = self.engine.run(values, self.build_context())
        except (ArithmeticError, KeyError, TypeError, ValueError) as exc:
            _log.exception("Calculation failed for %s %s", self.design_type.title, self.member.name)
            raise CalculationError(f"Calculation failed: {exc}") from exc
        result.messages = [*validation.warnings, *result.messages]
        self.member.result = result.to_dict()
        self.member.touch()
        return result

    @property
    def last_result(self) -> DesignResult:
        """Result stored on the member (NOT_CALCULATED if none)."""
        return DesignResult.from_dict(self.member.result)

    # ----------------------------------------------------------------- report
    def generate_report(self, information: ProjectInformation | None = None) -> str:
        """Return a plain text calculation report of the last result."""
        from app.design.report import TextReportBuilder

        return TextReportBuilder(self, information or self.project.information).build()

    def is_result_current(self) -> bool:
        """True if a stored result exists and is not marked as an error."""
        return self.last_result.status not in (DesignStatus.NOT_CALCULATED, DesignStatus.ERROR)
