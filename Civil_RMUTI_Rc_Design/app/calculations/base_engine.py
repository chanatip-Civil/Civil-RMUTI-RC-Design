"""Base class and context object for calculation engines."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

from app.core.constants import DesignStandard, DesignType, Quantity, UnitSystem, unit_label
from app.design.results import DesignResult, DesignStatus, ResultItem
from app.materials.concrete import Concrete
from app.materials.reinforcement import RebarGrade


@dataclass(frozen=True)
class CalculationContext:
    """Everything an engine needs besides the member inputs."""

    standard: DesignStandard
    unit_system: UnitSystem
    concrete: Concrete | None = None
    main_rebar: RebarGrade | None = None
    tie_rebar: RebarGrade | None = None

    def unit(self, quantity: Quantity) -> str:
        """Unit label of *quantity* in the project unit system."""
        return unit_label(quantity, self.unit_system)


class CalculationEngine(ABC):
    """Interface of all member calculation engines.

    Subclasses implement :meth:`run`. ``inputs`` are already validated and
    parsed (numbers as ``float``, choices as ``str``).
    """

    design_type: DesignType
    engine_name: str = "Base engine"

    #: Standards whose design checks are implemented by this engine.
    supported_standards: tuple[DesignStandard, ...] = ()

    def supports(self, standard: DesignStandard) -> bool:
        """True if the design check for *standard* is implemented."""
        return standard in self.supported_standards

    @abstractmethod
    def run(self, inputs: dict[str, Any], context: CalculationContext) -> DesignResult:
        """Execute the calculation and return a :class:`DesignResult`."""


class GeometryOnlyEngine(CalculationEngine):
    """Phase 1 engine: exact geometry, no code-based design check.

    Subclasses implement :meth:`geometry_items`. ``run`` wraps them into a
    ``NOT_IMPLEMENTED`` result that clearly states what is missing.
    """

    engine_name = "Phase 1 geometry engine"

    @abstractmethod
    def geometry_items(self, inputs: dict[str, Any],
                       context: CalculationContext) -> list[ResultItem]:
        """Return exact geometric properties of the member."""

    def run(self, inputs: dict[str, Any], context: CalculationContext) -> DesignResult:
        """Compute geometry and report that the design check is pending."""
        items = self.geometry_items(inputs, context)
        if context.concrete is not None:
            items.append(ResultItem("Concrete f'c", context.concrete.fc_ksc, "ksc",
                                    f"= {context.concrete.fc_mpa:.2f} MPa"))
        if context.main_rebar is not None:
            items.append(ResultItem(f"Main bar fy ({context.main_rebar.name})",
                                    context.main_rebar.fy_ksc, "ksc",
                                    f"= {context.main_rebar.fy_mpa:.1f} MPa"))
        messages = [
            "Geometric properties were computed.",
            f"Structural design check according to {context.standard.value} is NOT "
            f"implemented yet ({self.design_type.title} design is planned for a later phase).",
            "Results must not be used for construction.",
        ]
        return DesignResult(
            status=DesignStatus.NOT_IMPLEMENTED,
            summary=f"{self.design_type.title}: geometry computed, design check pending.",
            items=items,
            messages=messages,
            standard=context.standard.value,
            engine=self.engine_name,
        )
