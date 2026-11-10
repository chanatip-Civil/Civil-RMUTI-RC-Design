"""Application-wide constants and enumerations."""

from __future__ import annotations

from enum import Enum

APP_NAME: str = "Civil RMUTI Rc Design"
APP_SHORT_NAME: str = "CivilRMUTIRcDesign"
APP_VERSION: str = "0.2.3"
APP_PHASE: str = "Phase 2 - Material Database"
ORGANIZATION_NAME: str = "RMUTI Civil Engineering"
ORGANIZATION_DOMAIN: str = "rmuti.ac.th"

PROJECT_FILE_EXTENSION: str = ".rcproj"
PROJECT_FILE_FILTER: str = f"{APP_NAME} Project (*{PROJECT_FILE_EXTENSION} *{PROJECT_FILE_EXTENSION}.json)"
WEB_PROJECT_FILE_SUFFIX: str = f"{PROJECT_FILE_EXTENSION}.json"
FILE_FORMAT_ID: str = "CIVIL_RMUTI_RC_DESIGN_PROJECT"
FILE_FORMAT_VERSION: int = 1

MAX_RECENT_PROJECTS: int = 10

# Unit conversion between kilogram-force and SI (exact by definition of g_n).
KGF_TO_N: float = 9.80665
KSC_TO_MPA: float = KGF_TO_N / 100.0  # 1 kgf/cm^2 = 0.0980665 MPa


class DesignType(str, Enum):
    """Structural member types supported by the application."""

    COLUMN = "column"
    BEAM = "beam"
    SLAB = "slab"
    STAIR = "stair"
    FOOTING = "footing"

    @property
    def title(self) -> str:
        """Human readable title, e.g. ``Column``."""
        return self.value.capitalize()

    @property
    def description(self) -> str:
        """One line English description used on cards and reports."""
        return f"Reinforced Concrete {self.title} Design"

    @property
    def description_th(self) -> str:
        """One line Thai description."""
        return {
            DesignType.COLUMN: "ออกแบบเสาคอนกรีตเสริมเหล็ก",
            DesignType.BEAM: "ออกแบบคานคอนกรีตเสริมเหล็ก",
            DesignType.SLAB: "ออกแบบพื้นคอนกรีตเสริมเหล็ก",
            DesignType.STAIR: "ออกแบบบันไดคอนกรีตเสริมเหล็ก",
            DesignType.FOOTING: "ออกแบบฐานรากคอนกรีตเสริมเหล็ก",
        }[self]

    @property
    def project_key(self) -> str:
        """Key used inside the ``.rcproj`` file, e.g. ``columns``."""
        return f"{self.value}s"

    @property
    def name_prefix(self) -> str:
        """Default prefix for new member names (C1, B1, S1, ST1, F1)."""
        return {
            DesignType.COLUMN: "C",
            DesignType.BEAM: "B",
            DesignType.SLAB: "S",
            DesignType.STAIR: "ST",
            DesignType.FOOTING: "F",
        }[self]


class DesignStandard(str, Enum):
    """Design standards selectable for a project.

    Phase 1 only stores the selection. Calculation engines added in later
    phases must implement the clauses of the selected standard explicitly.
    """

    EIT_1007 = "EIT 1007-34"
    EIT_1008 = "EIT 1008-38"
    ACI_318_19 = "ACI 318-19"
    USER_DEFINED = "User Defined"

    @property
    def label(self) -> str:
        """Descriptive label shown in combo boxes."""
        return {
            DesignStandard.EIT_1007: "วสท. 1007-34 — Working Stress Design (WSD)",
            DesignStandard.EIT_1008: "วสท. 1008-38 — Strength Design Method (SDM)",
            DesignStandard.ACI_318_19: "ACI 318-19 — Building Code Requirements for Structural Concrete",
            DesignStandard.USER_DEFINED: "User Defined Standard",
        }[self]

    @classmethod
    def from_value(cls, value: str) -> "DesignStandard":
        """Return the enum member for *value*, falling back to USER_DEFINED."""
        for member in cls:
            if member.value == value:
                return member
        return cls.USER_DEFINED


class UnitSystem(str, Enum):
    """Unit systems for loads and stresses (geometry is always in mm / m)."""

    SI = "SI"
    MKS = "MKS"

    @property
    def label(self) -> str:
        """Descriptive label shown in combo boxes."""
        return {
            UnitSystem.SI: "SI (kN, kN·m, MPa)",
            UnitSystem.MKS: "MKS (kgf, kgf·m, ksc)",
        }[self]

    @classmethod
    def from_value(cls, value: str) -> "UnitSystem":
        """Return the enum member for *value*, falling back to SI."""
        for member in cls:
            if member.value == value:
                return member
        return cls.SI


class Quantity(str, Enum):
    """Physical quantity of an input field; determines its unit label."""

    LENGTH_MM = "length_mm"
    LENGTH_M = "length_m"
    FORCE = "force"
    MOMENT = "moment"
    AREA_LOAD = "area_load"
    STRESS = "stress"
    ANGLE = "angle"
    NONE = "none"


_UNIT_LABELS: dict[UnitSystem, dict[Quantity, str]] = {
    UnitSystem.SI: {
        Quantity.LENGTH_MM: "mm",
        Quantity.LENGTH_M: "m",
        Quantity.FORCE: "kN",
        Quantity.MOMENT: "kN·m",
        Quantity.AREA_LOAD: "kN/m²",
        Quantity.STRESS: "MPa",
        Quantity.ANGLE: "deg",
        Quantity.NONE: "",
    },
    UnitSystem.MKS: {
        Quantity.LENGTH_MM: "mm",
        Quantity.LENGTH_M: "m",
        Quantity.FORCE: "kgf",
        Quantity.MOMENT: "kgf·m",
        Quantity.AREA_LOAD: "kgf/m²",
        Quantity.STRESS: "ksc",
        Quantity.ANGLE: "deg",
        Quantity.NONE: "",
    },
}


def unit_label(quantity: Quantity, unit_system: UnitSystem) -> str:
    """Return the unit label of *quantity* in *unit_system*."""
    return _UNIT_LABELS[unit_system][quantity]
