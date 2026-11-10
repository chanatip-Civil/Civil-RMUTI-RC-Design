"""Short column under concentric axial load - ACI 318-19 (SI).

Expected values are hand calculations shown step by step in each docstring
(no textbook example yet; replace/add one when the team chooses a textbook,
see docs/DECISIONS.md). Unit conversion: 1 ksc = 0.0980665 MPa,
1 kgf = 9.80665 N (app/core/constants.py).
"""

from __future__ import annotations

import math
import unittest

from app.core.constants import DesignStandard, DesignType, UnitSystem
from app.core.project_model import Project
from app.design.registry import DESIGN_REGISTRY, create_design
from app.design.results import DesignStatus

KSC = 0.0980665
FC = 240.0 * KSC      # fc' 240 ksc = 23.53596 MPa (project default concrete)
FY = 4000.0 * KSC     # SD40 = 392.266 MPa (project default main bars)
FYT = 2400.0 * KSC    # SR24 = 235.3596 MPa (project default ties)


class ColumnAxialAciTests(unittest.TestCase):
    def _design(self, standard: DesignStandard = DesignStandard.ACI_318_19,
                units: UnitSystem = UnitSystem.SI, **inputs):
        project = Project()
        project.settings.design_standard = standard.value
        project.settings.unit_system = units.value
        cls = DESIGN_REGISTRY[DesignType.COLUMN]
        member = project.add_member(cls.create_member(project))
        member.inputs.update(inputs)
        return create_design(member, project)

    @staticmethod
    def _items(result) -> dict[str, float]:
        return {i.label: i.value for i in result.items}

    # ------------------------------------------------------------- tied
    def test_tied_400x400_8db20_pass(self) -> None:
        """Hand calculation, ACI 318-19 22.4.2 / Table 21.2.2.

        Ag = 400·400 = 160 000 mm²; Ast = 8·π·20²/4 = 2 513.27 mm² (ρg = 1.571 %)
        Po = 0.85·23.536·(160 000 − 2 513.27) + 392.266·2 513.27 = 4 136.48 kN
        Pn,max = 0.80·Po = 3 309.19 kN;  φPn,max = 0.65·3 309.19 = 2 150.97 kN
        Ties DB10 @ 200: s,max = min(16·20, 48·10, 400) = 320 mm
        Slenderness (ACI 6.2.5): r = 0.3·400 = 120 mm, kLu/r = 1.0·3000/120 = 25.0;
        nonsway with M1/M2 = 0 → limit min(34 + 12·0, 40) = 34 → short column.
        """
        d = self._design(width=400.0, depth=400.0, clear_height=3000.0, bar_count=8,
                         bar_diameter=20.0, tie_diameter=10.0, tie_spacing=200.0,
                         axial_load=2000.0, m1_m2=0.0)
        result = d.calculate()
        it = self._items(result)
        self.assertEqual(result.status, DesignStatus.PASS, result.messages)
        self.assertAlmostEqual(it["Longitudinal steel Ast"], 2513.274, places=2)
        self.assertAlmostEqual(it["Reinforcement ratio ρg = Ast/Ag"], 1.5708, places=3)
        self.assertAlmostEqual(it["Po = 0.85f'c(Ag-Ast) + fy·Ast"], 4136.483, places=2)
        self.assertAlmostEqual(it["Pn,max = 0.80·Po"], 3309.186, places=2)
        self.assertAlmostEqual(it["Design strength φPn,max"], 2150.971, places=2)
        self.assertAlmostEqual(it["Maximum tie spacing"], 320.0)
        self.assertAlmostEqual(it["Slenderness k·Lu/r"], 25.0)
        self.assertAlmostEqual(it["Demand / capacity Pu/φPn,max"], 2000.0 / 2150.971, places=4)

    def test_tied_overloaded_fails(self) -> None:
        """Same section, Pu = 2 200 kN > φPn,max = 2 150.97 kN → FAIL."""
        d = self._design(width=400.0, depth=400.0, bar_count=8, bar_diameter=20.0,
                         axial_load=2200.0, m1_m2=0.0)
        result = d.calculate()
        self.assertEqual(result.status, DesignStatus.FAIL)
        self.assertIn("Pu exceeds φPn,max (ACI 318-19 22.4.2.1).", result.messages)

    def test_capacity_in_mks_units(self) -> None:
        """φPn,max = 2 150 971.2 N / 9.80665 = 219 338 kgf."""
        d = self._design(units=UnitSystem.MKS, width=400.0, depth=400.0, bar_count=8,
                         bar_diameter=20.0, axial_load=200000.0, m1_m2=0.0)
        it = self._items(d.calculate())
        self.assertAlmostEqual(it["Design strength φPn,max"], 2150971.2 / 9.80665, delta=1.0)

    def test_reinforcement_ratio_limits(self) -> None:
        """ACI 10.6.1.1: 4-DB12 in 400x400 → ρg = 452.4/160 000 = 0.283 % < 1 % → FAIL;
        boundary: 4 bars with Ast = 0.01·Ag exactly (db = √(1600/π)·2) → OK."""
        low = self._design(width=400.0, depth=400.0, bar_count=4, bar_diameter=12.0,
                           axial_load=100.0, m1_m2=0.0).calculate()
        self.assertEqual(low.status, DesignStatus.FAIL)
        self.assertTrue(any("10.6.1.1" in m for m in low.messages))
        db_edge = math.sqrt(0.01 * 160000.0 / 4.0 * 4.0 / math.pi) * 1.0000001
        edge = self._design(width=400.0, depth=400.0, bar_count=4, bar_diameter=db_edge,
                            axial_load=100.0, m1_m2=0.0, tie_diameter=12.7).calculate()
        self.assertFalse(any("10.6.1.1" in m for m in edge.messages), edge.messages)

    def test_tie_size_and_spacing(self) -> None:
        """ACI 25.7.2.2: RB9 (9 mm) < 9.5 mm → FAIL; 25.7.2.1: s = 350 > 320 mm → FAIL."""
        result = self._design(width=400.0, depth=400.0, bar_count=8, bar_diameter=20.0,
                              tie_diameter=9.0, tie_spacing=350.0, axial_load=100.0,
                              m1_m2=0.0).calculate()
        self.assertEqual(result.status, DesignStatus.FAIL)
        self.assertIn("Tie diameter 9 mm < 9.5 mm (ACI 318-19 25.7.2.2).", result.messages)
        # 48·9 = 432, 16·20 = 320, b = 400 → 320
        self.assertIn("Tie spacing 350 mm > 320 mm (ACI 318-19 25.7.2.1).", result.messages)

    def test_minimum_bar_count(self) -> None:
        """ACI 10.7.3.1: 3 bars with rectangular ties < 4 → FAIL."""
        result = self._design(width=300.0, depth=300.0, bar_count=3, bar_diameter=25.0,
                              axial_load=100.0, m1_m2=0.0).calculate()
        self.assertTrue(any("10.7.3.1" in m for m in result.messages))
        self.assertEqual(result.status, DesignStatus.FAIL)

    # ------------------------------------------------------- slenderness
    def test_slenderness_limits(self) -> None:
        """ACI 6.2.5.1: kLu/r = 3000/(0.3·400) = 25.
        nonsway M1/M2 = −1 → limit 22 → slender → NOT_IMPLEMENTED (never PASS);
        nonsway M1/M2 = +0.5 → limit min(40, 40) = 40 → short;
        sway → limit 22 → slender."""
        base = dict(width=400.0, depth=400.0, bar_count=8, bar_diameter=20.0, axial_load=100.0)
        r1 = self._design(m1_m2=-1.0, **base).calculate()
        self.assertEqual(r1.status, DesignStatus.NOT_IMPLEMENTED)
        r2 = self._design(m1_m2=0.5, **base).calculate()
        self.assertEqual(r2.status, DesignStatus.PASS)
        self.assertIn("limit 40.0", next(i.note for i in r2.items if i.label == "Slenderness k·Lu/r"))
        r3 = self._design(frame_type="Sway (unbraced)", **base).calculate()
        self.assertEqual(r3.status, DesignStatus.NOT_IMPLEMENTED)

    def test_moment_input_is_not_checked(self) -> None:
        """Nonzero Mu must never give PASS (interaction diagram not implemented)."""
        result = self._design(width=400.0, depth=400.0, bar_count=8, bar_diameter=20.0,
                              axial_load=100.0, moment_x=10.0, m1_m2=0.0).calculate()
        self.assertEqual(result.status, DesignStatus.NOT_IMPLEMENTED)

    # ------------------------------------------------------------ spiral
    def test_spiral_circular(self) -> None:
        """D = 400, cover 40, 6-DB20, spiral fyt = SR24.
        Ag = 125 663.7 mm², Ast = 1 885.0 mm² (1.5 %)
        Po = 0.85·23.536·(125 663.7 − 1 885.0) + 392.266·1 885.0 = 3 215.67 kN
        φPn,max = 0.75·0.85·Po = 2 049.99 kN
        Dc = 320 mm, Ach = 80 424.8 mm²
        ρs,min = 0.45·(125 663.7/80 424.8 − 1)·23.536/235.36 = 0.025313 (Eq. 25.7.3.3)
        RB10 @ 50: ρs = 4·78.54/(320·50) = 0.019635 → FAIL
        DB12 @ 50: ρs = 4·113.10/(320·50) = 0.028274 → OK, clear = 38 mm (25-75) → PASS
        """
        base = dict(shape="Circular", width=400.0, cover=40.0, tie_type="Spiral",
                    bar_count=6, bar_diameter=20.0, tie_spacing=50.0, axial_load=2000.0,
                    m1_m2=0.0)
        fail = self._design(tie_diameter=10.0, **base).calculate()
        it = self._items(fail)
        self.assertAlmostEqual(it["Design strength φPn,max"], 2049.988, places=2)
        self.assertAlmostEqual(it["Spiral ratio ρs = 4Asp/(Dc·s)"], 0.019635, places=6)
        self.assertAlmostEqual(it["Minimum ρs = 0.45(Ag/Ach-1)f'c/fyt"], 0.0253125, places=6)
        self.assertEqual(fail.status, DesignStatus.FAIL)
        ok = self._design(tie_diameter=12.0, **base).calculate()
        self.assertEqual(ok.status, DesignStatus.PASS, ok.messages)

    def test_spiral_requires_circular_section(self) -> None:
        d = self._design(tie_type="Spiral")
        self.assertIn("Column spiral reinforcement is only supported for circular sections.",
                      d.validate().errors)

    # --------------------------------------------------- other standards
    def test_unsupported_standard_returns_geometry_only(self) -> None:
        for standard in (DesignStandard.EIT_1008, DesignStandard.EIT_1007,
                         DesignStandard.USER_DEFINED):
            with self.subTest(standard=standard):
                result = self._design(standard=standard).calculate()
                self.assertEqual(result.status, DesignStatus.NOT_IMPLEMENTED)
                self.assertIn("Gross section area Ag", self._items(result))


if __name__ == "__main__":
    unittest.main()
