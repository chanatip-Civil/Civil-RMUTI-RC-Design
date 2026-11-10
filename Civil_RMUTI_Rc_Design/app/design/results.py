"""Result model shared by all calculation engines."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class DesignStatus(str, Enum):
    """Outcome of a design calculation."""

    NOT_CALCULATED = "not_calculated"
    NOT_IMPLEMENTED = "not_implemented"
    PASS = "pass"
    FAIL = "fail"
    ERROR = "error"

    @property
    def label(self) -> str:
        """Readable label."""
        return {
            DesignStatus.NOT_CALCULATED: "Not calculated",
            DesignStatus.NOT_IMPLEMENTED: "Design check not implemented (Phase 1)",
            DesignStatus.PASS: "PASS",
            DesignStatus.FAIL: "FAIL",
            DesignStatus.ERROR: "ERROR",
        }[self]


@dataclass
class ResultItem:
    """One reported quantity."""

    label: str
    value: float | str
    unit: str = ""
    note: str = ""

    def formatted_value(self) -> str:
        """Value formatted for display."""
        if isinstance(self.value, float):
            return f"{self.value:,.3f}".rstrip("0").rstrip(".")
        return str(self.value)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a JSON compatible dict."""
        return {"label": self.label, "value": self.value, "unit": self.unit, "note": self.note}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ResultItem":
        """Create from :meth:`to_dict` output."""
        value = data.get("value", "")
        if not isinstance(value, (int, float, str)) or isinstance(value, bool):
            value = str(value)
        return cls(
            label=str(data.get("label", "")),
            value=float(value) if isinstance(value, int) else value,
            unit=str(data.get("unit", "")),
            note=str(data.get("note", "")),
        )


@dataclass
class DesignResult:
    """Result of a calculation engine run."""

    status: DesignStatus = DesignStatus.NOT_CALCULATED
    summary: str = ""
    items: list[ResultItem] = field(default_factory=list)
    messages: list[str] = field(default_factory=list)
    standard: str = ""
    engine: str = ""
    calculated_at: str = field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a JSON compatible dict."""
        return {
            "status": self.status.value,
            "summary": self.summary,
            "items": [item.to_dict() for item in self.items],
            "messages": list(self.messages),
            "standard": self.standard,
            "engine": self.engine,
            "calculated_at": self.calculated_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "DesignResult":
        """Create from :meth:`to_dict` output (None gives NOT_CALCULATED)."""
        if not data:
            return cls()
        try:
            status = DesignStatus(data.get("status", DesignStatus.NOT_CALCULATED.value))
        except ValueError:
            status = DesignStatus.ERROR
        return cls(
            status=status,
            summary=str(data.get("summary", "")),
            items=[ResultItem.from_dict(i) for i in data.get("items", []) if isinstance(i, dict)],
            messages=[str(m) for m in data.get("messages", [])],
            standard=str(data.get("standard", "")),
            engine=str(data.get("engine", "")),
            calculated_at=str(data.get("calculated_at", "")),
        )
