"""Reusable input validation helpers.

Validation functions never raise for bad user input; they collect readable
messages in a :class:`ValidationResult` so the GUI can show all problems at
once.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ValidationResult:
    """Collected errors (block calculation) and warnings (informational)."""

    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        """True when there are no errors."""
        return not self.errors

    def add_error(self, message: str) -> None:
        """Append an error message."""
        self.errors.append(message)

    def add_warning(self, message: str) -> None:
        """Append a warning message."""
        self.warnings.append(message)

    def merge(self, other: "ValidationResult") -> None:
        """Append all messages from *other*."""
        self.errors.extend(other.errors)
        self.warnings.extend(other.warnings)


def parse_number(value: Any) -> float | None:
    """Convert *value* to a finite float, or return None if impossible.

    Accepts numbers and strings (a comma is accepted as decimal separator
    only when no dot is present, e.g. ``"2,5"``; thousands separators such as
    ``"1,200.5"`` are also accepted).
    """
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        number = float(value)
    elif isinstance(value, str):
        text = value.strip().replace(" ", "")
        if not text:
            return None
        if "," in text and "." not in text and text.count(",") == 1:
            text = text.replace(",", ".")
        else:
            text = text.replace(",", "")
        try:
            number = float(text)
        except ValueError:
            return None
    else:
        return None
    return number if math.isfinite(number) else None


def is_blank(value: Any) -> bool:
    """True for None, empty or whitespace-only strings."""
    return value is None or (isinstance(value, str) and not value.strip())


def validate_required_text(value: Any, label: str, result: ValidationResult,
                           max_length: int = 200) -> None:
    """Check that a text field is filled in and not too long."""
    if is_blank(value):
        result.add_error(f"{label} is required.")
    elif len(str(value)) > max_length:
        result.add_error(f"{label} must not exceed {max_length} characters.")


def validate_number(
    value: Any,
    label: str,
    unit: str,
    result: ValidationResult,
    *,
    required: bool = True,
    minimum: float | None = None,
    maximum: float | None = None,
    min_inclusive: bool = False,
    integer: bool = False,
) -> float | None:
    """Validate a numeric input and return the parsed value.

    Args:
        value: Raw value (number or text).
        label: Field name used in messages, e.g. ``"Column width"``.
        unit: Unit label appended to limits in messages.
        result: Collector for messages.
        required: Blank values are errors when True.
        minimum: Lower limit (exclusive unless *min_inclusive*).
        maximum: Upper limit (inclusive).
        min_inclusive: Treat *minimum* as inclusive.
        integer: Require a whole number.

    Returns:
        The parsed number, or None if missing/invalid.
    """
    suffix = f" {unit}" if unit else ""
    if is_blank(value):
        if required:
            result.add_error(f"{label} is required.")
        return None
    number = parse_number(value)
    if number is None:
        result.add_error(f"{label} must be a number (got '{value}').")
        return None
    if integer and not float(number).is_integer():
        result.add_error(f"{label} must be a whole number.")
        return None
    if minimum is not None:
        if min_inclusive and number < minimum:
            result.add_error(f"{label} must be greater than or equal to {minimum:g}{suffix}.")
            return None
        if not min_inclusive and number <= minimum:
            result.add_error(f"{label} must be greater than {minimum:g}{suffix}.")
            return None
    if maximum is not None and number > maximum:
        result.add_error(f"{label} must not exceed {maximum:g}{suffix}.")
        return None
    return number


def validate_choice(value: Any, label: str, choices: list[str],
                    result: ValidationResult) -> str | None:
    """Check that *value* is one of *choices*."""
    if value not in choices:
        result.add_error(f"{label} must be one of: {', '.join(choices)}.")
        return None
    return str(value)
