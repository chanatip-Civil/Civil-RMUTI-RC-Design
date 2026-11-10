"""Application specific exception hierarchy."""

from __future__ import annotations


class RcDesignError(Exception):
    """Base class for all expected (handled) application errors."""


class ProjectFileError(RcDesignError):
    """Raised when a project file cannot be read, parsed or written."""


class ProjectStateError(RcDesignError):
    """Raised when an operation requires an open project but none exists."""


class InputValidationError(RcDesignError):
    """Raised when input data fails validation.

    Attributes:
        messages: Individual human readable error messages.
    """

    def __init__(self, messages: list[str]) -> None:
        self.messages: list[str] = list(messages)
        super().__init__("\n".join(self.messages) or "Invalid input")


class MaterialError(RcDesignError):
    """Raised for invalid material operations (duplicates, protected or used items)."""


class CalculationError(RcDesignError):
    """Raised when a calculation engine fails."""
