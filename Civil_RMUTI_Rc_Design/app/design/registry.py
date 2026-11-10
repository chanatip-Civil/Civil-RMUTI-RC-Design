"""Registry mapping each :class:`DesignType` to its design class.

Adding a new member type = create the design package, then register it here.
"""

from __future__ import annotations

from app.core.constants import DesignType
from app.core.project_model import DesignMember, Project
from app.design.base import BaseDesign
from app.design.beam import BeamDesign
from app.design.column import ColumnDesign
from app.design.footing import FootingDesign
from app.design.slab import SlabDesign
from app.design.stair import StairDesign

DESIGN_REGISTRY: dict[DesignType, type[BaseDesign]] = {
    DesignType.COLUMN: ColumnDesign,
    DesignType.BEAM: BeamDesign,
    DesignType.SLAB: SlabDesign,
    DesignType.STAIR: StairDesign,
    DesignType.FOOTING: FootingDesign,
}


def get_design_class(design_type: DesignType) -> type[BaseDesign]:
    """Return the design class registered for *design_type*."""
    return DESIGN_REGISTRY[design_type]


def create_design(member: DesignMember, project: Project) -> BaseDesign:
    """Instantiate the design object handling *member*."""
    return get_design_class(member.design_type)(member, project)
