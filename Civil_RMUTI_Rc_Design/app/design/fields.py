"""Declarative description of design input fields.

Each design class lists its inputs as :class:`FieldSpec` objects. The same
specification drives generic validation (core) and automatic form
generation (GUI), so a new member type needs no GUI code.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.core.constants import Quantity

NUMBER: str = "number"
INTEGER: str = "integer"
CHOICE: str = "choice"


@dataclass(frozen=True)
class FieldSpec:
    """Specification of one input field.

    Attributes:
        key: Storage key inside ``DesignMember.inputs``.
        label: Label used in the form and in error messages.
        quantity: Physical quantity (determines the unit label).
        default: Default value for new members.
        kind: ``"number"``, ``"integer"`` or ``"choice"``.
        group: Form group box title.
        minimum: Lower limit (exclusive unless *min_inclusive*); None = no limit.
        maximum: Upper limit (inclusive); None = no limit.
        min_inclusive: Treat *minimum* as inclusive.
        required: Blank values are not allowed.
        choices: Allowed values for ``"choice"`` fields.
        tooltip: Help text.
        visible_when: ``(other_key, allowed_values)``; the field is only
            shown and validated when the other field has one of the values.
    """

    key: str
    label: str
    quantity: Quantity = Quantity.NONE
    default: Any = None
    kind: str = NUMBER
    group: str = "General"
    minimum: float | None = None
    maximum: float | None = None
    min_inclusive: bool = False
    required: bool = True
    choices: tuple[str, ...] = field(default_factory=tuple)
    tooltip: str = ""
    visible_when: tuple[str, tuple[str, ...]] | None = None

    def is_active(self, inputs: dict[str, Any]) -> bool:
        """Return True if the field applies for the given *inputs*."""
        if self.visible_when is None:
            return True
        other_key, allowed = self.visible_when
        return str(inputs.get(other_key, "")) in allowed
