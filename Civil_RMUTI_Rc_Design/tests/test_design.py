"""Tests for design modules and placeholder calculation engines."""

from __future__ import annotations

import unittest

from app.core.constants import DesignType
from app.core.exceptions import InputValidationError
from app.core.project_model import Project
from app.design.registry import DESIGN_REGISTRY, create_design
from app.design.results import DesignResult, DesignStatus


class DesignModuleTests(unittest.TestCase):
    def setUp(self) -> None:
        self.project = Project()

    def _new(self, design_type: DesignType):
        cls = DESIGN_REGISTRY[design_type]
        member = self.project.add_member(cls.create_member(self.project))
        return create_design(member, self.project)

    def test_all_types_registered(self) -> None:
        self.assertEqual(set(DESIGN_REGISTRY), set(DesignType))

    def test_defaults_are_valid_and_calculate(self) -> None:
        for design_type in DesignType:
            with self.subTest(design_type=design_type):
                design = self._new(design_type)
                self.assertEqual(design.validate().errors, [])
                result = design.calculate()
                self.assertEqual(result.status, DesignStatus.NOT_IMPLEMENTED)
                self.assertTrue(result.items)
                stored = DesignResult.from_dict(design.member.result)
                self.assertEqual(stored.to_dict(), result.to_dict())
                self.assertIn(design.member.name, design.generate_report())

    def test_negative_dimension_message(self) -> None:
        design = self._new(DesignType.COLUMN)
        design.member.inputs["width"] = -300
        errors = design.validate().errors
        self.assertIn("Column width b / diameter D must be greater than 0 mm.", errors)
        with self.assertRaises(InputValidationError):
            design.calculate()

    def test_cross_field_checks(self) -> None:
        slab = self._new(DesignType.SLAB)
        slab.member.inputs.update(short_span=6.0, long_span=4.0)
        self.assertTrue(any("short span" in e for e in slab.validate().errors))

        footing = self._new(DesignType.FOOTING)
        footing.member.inputs["column_width"] = 2000.0
        self.assertTrue(any("Column width" in e for e in footing.validate().errors))

    def test_inactive_field_is_ignored(self) -> None:
        design = self._new(DesignType.COLUMN)
        design.member.inputs.update(shape="Circular", depth="")
        self.assertEqual(design.validate().errors, [])

    def test_geometry_values(self) -> None:
        beam = self._new(DesignType.BEAM)
        beam.member.inputs.update(width=250.0, depth=500.0, span=5.0)
        items = {i.label: i.value for i in beam.calculate().items}
        self.assertAlmostEqual(items["Gross section area Ag"], 125000.0)
        self.assertAlmostEqual(items["Concrete volume"], 0.625)

        stair = self._new(DesignType.STAIR)
        stair.member.inputs.update(floor_height=1500.0, riser=170.0, tread=250.0)
        items = {i.label: i.value for i in stair.calculate().items}
        self.assertEqual(items["Number of risers"], 9.0)

    def test_unknown_material_rejected(self) -> None:
        design = self._new(DesignType.BEAM)
        design.member.concrete = "Unknown"
        self.assertTrue(any("Concrete grade" in e for e in design.validate().errors))


if __name__ == "__main__":
    unittest.main()
