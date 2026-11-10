"""Column calculation engine.

Implemented (Phase 3, step 1): axial strength of SHORT columns under
concentric load according to ACI 318-19 (SI units), together with the
reinforcement detailing checks that apply to an axially loaded column:

* longitudinal reinforcement ratio and minimum number of bars,
* maximum nominal axial strength phi*Pn,max,
* lateral reinforcement (ties or spiral),
* slenderness limit for neglecting slenderness effects.

Not implemented yet: combined axial + moment (interaction diagram),
slender column moment magnification, other design standards.
For those cases the engine reports ``NOT_IMPLEMENTED`` and never ``PASS``.

All clause numbers refer to ACI 318-19 "Building Code Requirements for
Structural Concrete" (SI edition, ACI 318M-19).
"""

from __future__ import annotations

import math
from typing import Any

from app.calculations.base_engine import CalculationContext, GeometryOnlyEngine
from app.core.constants import KGF_TO_N, DesignStandard, DesignType, Quantity, UnitSystem
from app.design.results import DesignResult, DesignStatus, ResultItem

SHAPE_RECTANGULAR: str = "Rectangular"
SHAPE_CIRCULAR: str = "Circular"

TIES_TIED: str = "Tied"
TIES_SPIRAL: str = "Spiral"

FRAME_NONSWAY: str = "Nonsway (braced)"
FRAME_SWAY: str = "Sway (unbraced)"

ACI = "ACI 318-19"

# ACI 318-19 Table 21.2.2: strength reduction factor, compression-controlled.
PHI_TIED: float = 0.65
PHI_SPIRAL: float = 0.75
# ACI 318-19 Table 22.4.2.1: Pn,max = 0.80 Po (ties) / 0.85 Po (spirals).
PN_MAX_TIED: float = 0.80
PN_MAX_SPIRAL: float = 0.85
# ACI 318-19 10.6.1.1: 0.01 Ag <= Ast <= 0.08 Ag.
RHO_MIN: float = 0.01
RHO_MAX: float = 0.08
# ACI 318-19 10.7.3.1: minimum number of longitudinal bars.
MIN_BARS_TIED: int = 4
MIN_BARS_SPIRAL: int = 6
# ACI 318-19 19.2.1.1 (Table 19.2.1.1): minimum f'c for general use [MPa].
FC_MIN_MPA: float = 17.0
# ACI 318-19 Table 20.2.2.4(a): maximum fy of deformed longitudinal bars
# (flexure, axial force; not special seismic systems) [MPa].
FY_MAX_LONGITUDINAL_MPA: float = 550.0
# ACI 318-19 Table 20.2.2.4(a): maximum fyt of spirals (lateral support of
# longitudinal bars / confinement) [MPa].
FYT_MAX_SPIRAL_MPA: float = 700.0
# ACI 318-19 25.7.2.2: minimum tie bar, No. 10 (9.5 mm) for longitudinal bars
# No. 32 (32.3 mm) or smaller, No. 13 (12.7 mm) for larger bars.
TIE_DB_SMALL_MM: float = 9.5
TIE_DB_LARGE_MM: float = 12.7
LONG_DB_LIMIT_MM: float = 32.3
# ACI 318-19 25.7.3.2: minimum spiral bar diameter (cast-in-place) [mm].
SPIRAL_DB_MIN_MM: float = 9.5
# ACI 318-19 25.7.3.1: clear spacing of spirals 25 mm .. 75 mm.
SPIRAL_CLEAR_MIN_MM: float = 25.0
SPIRAL_CLEAR_MAX_MM: float = 75.0


def force_to_newton(value: float, unit_system: UnitSystem) -> float:
    """Convert a force in the project unit system (kN or kgf) to N."""
    return value * (1000.0 if unit_system == UnitSystem.SI else KGF_TO_N)


def newton_to_force(value: float, unit_system: UnitSystem) -> float:
    """Convert a force in N to the project unit system (kN or kgf)."""
    return value / (1000.0 if unit_system == UnitSystem.SI else KGF_TO_N)


def _ok(flag: bool) -> str:
    return "OK" if flag else "NOT OK"


class ColumnCalculationEngine(GeometryOnlyEngine):
    """Short RC column under concentric axial load (ACI 318-19).

    For standards other than ACI 318-19 the geometry-only result of
    :class:`GeometryOnlyEngine` is returned (``NOT_IMPLEMENTED``).
    """

    design_type = DesignType.COLUMN
    engine_name = "Column engine v1.0 (ACI 318-19 short column, axial)"
    supported_standards = (DesignStandard.ACI_318_19,)

    # ------------------------------------------------------------ geometry
    def geometry_items(self, inputs: dict[str, Any],
                       context: CalculationContext) -> list[ResultItem]:
        """Gross area, perimeter, volume and Lu/least-dimension ratio."""
        width = float(inputs["width"])
        height_mm = float(inputs["clear_height"])
        if inputs["shape"] == SHAPE_CIRCULAR:
            area = math.pi * width ** 2 / 4.0
            perimeter = math.pi * width
            least_dim = width
        else:
            depth = float(inputs["depth"])
            area = width * depth
            perimeter = 2.0 * (width + depth)
            least_dim = min(width, depth)
        return [
            ResultItem("Gross section area Ag", area, "mm²", f"= {area / 100.0:,.1f} cm²"),
            ResultItem("Section perimeter", perimeter, "mm"),
            ResultItem("Concrete volume (clear height)", area * height_mm / 1e9, "m³"),
            ResultItem("Clear height / least dimension", height_mm / least_dim, "-",
                       "Geometric ratio only; slenderness check per standard pending"),
        ]

    # ---------------------------------------------------------------- run
    def run(self, inputs: dict[str, Any], context: CalculationContext) -> DesignResult:
        """Axial design check (ACI 318-19) or geometry only for other standards."""
        if not self.supports(context.standard) or context.concrete is None \
                or context.main_rebar is None or context.tie_rebar is None:
            return super().run(inputs, context)
        return self._run_aci(inputs, context)

    def _run_aci(self, v: dict[str, Any], context: CalculationContext) -> DesignResult:
        units = context.unit_system
        force_unit = context.unit(Quantity.FORCE)
        circular = v["shape"] == SHAPE_CIRCULAR
        spiral = v["tie_type"] == TIES_SPIRAL
        b = float(v["width"])
        lu = float(v["clear_height"])
        cover = float(v["cover"])
        n_bars = int(v["bar_count"])
        db = float(v["bar_diameter"])
        dt = float(v["tie_diameter"])
        s = float(v["tie_spacing"])
        k = float(v["k_factor"])

        fc = context.concrete.fc_mpa
        fy = context.main_rebar.fy_mpa
        fyt = context.tie_rebar.fy_mpa

        items: list[ResultItem] = []
        failures: list[str] = []
        out_of_scope: list[str] = []

        # ---- section
        if circular:
            ag = math.pi * b ** 2 / 4.0
            least = b
        else:
            h = float(v["depth"])
            ag = b * h
            least = min(b, h)
        items.append(ResultItem("Gross section area Ag", ag, "mm²", f"= {ag / 100.0:,.1f} cm²"))

        # ---- materials (ACI 318-19 19.2.1.1, Table 20.2.2.4(a))
        fc_ok = fc >= FC_MIN_MPA
        items.append(ResultItem("Concrete f'c", fc, "MPa",
                                f"min {FC_MIN_MPA:g} MPa, ACI 19.2.1.1 - {_ok(fc_ok)}"))
        fy_ok = fy <= FY_MAX_LONGITUDINAL_MPA
        items.append(ResultItem(f"Main bar fy ({context.main_rebar.name})", fy, "MPa",
                                f"max {FY_MAX_LONGITUDINAL_MPA:g} MPa, ACI Table 20.2.2.4(a) - {_ok(fy_ok)}"))
        if not fc_ok:
            failures.append(f"f'c = {fc:.2f} MPa is below the minimum {FC_MIN_MPA:g} MPa (ACI 318-19 19.2.1.1).")
        if not fy_ok:
            failures.append(f"fy = {fy:.1f} MPa exceeds {FY_MAX_LONGITUDINAL_MPA:g} MPa "
                            "(ACI 318-19 Table 20.2.2.4(a)).")

        # ---- longitudinal reinforcement (ACI 318-19 10.6.1.1, 10.7.3.1)
        ast = n_bars * math.pi * db ** 2 / 4.0
        rho = ast / ag
        items.append(ResultItem("Longitudinal steel Ast", ast, "mm²",
                                f"{n_bars} bars x {db:g} mm"))
        rho_ok = RHO_MIN <= rho <= RHO_MAX
        items.append(ResultItem("Reinforcement ratio ρg = Ast/Ag", rho * 100.0, "%",
                                f"{RHO_MIN * 100:g}-{RHO_MAX * 100:g} %, ACI 10.6.1.1 - {_ok(rho_ok)}"))
        if not rho_ok:
            failures.append(f"ρg = {rho * 100:.2f} % is outside {RHO_MIN * 100:g}-{RHO_MAX * 100:g} % "
                            "(ACI 318-19 10.6.1.1).")
        min_bars = MIN_BARS_SPIRAL if spiral else MIN_BARS_TIED
        bars_ok = n_bars >= min_bars
        items.append(ResultItem("Number of longitudinal bars", float(n_bars), "-",
                                f"min {min_bars}, ACI 10.7.3.1 - {_ok(bars_ok)}"))
        if not bars_ok:
            failures.append(f"{n_bars} longitudinal bars < minimum {min_bars} for "
                            f"{'spirals' if spiral else 'ties'} (ACI 318-19 10.7.3.1).")

        # ---- axial strength (ACI 318-19 22.4.2)
        po = 0.85 * fc * (ag - ast) + fy * ast              # ACI 318-19 Eq. 22.4.2.2
        pn_factor = PN_MAX_SPIRAL if spiral else PN_MAX_TIED  # ACI 318-19 Table 22.4.2.1
        phi = PHI_SPIRAL if spiral else PHI_TIED           # ACI 318-19 Table 21.2.2
        pn_max = pn_factor * po
        phi_pn = phi * pn_max
        pu_n = force_to_newton(float(v["axial_load"]), units)
        items.append(ResultItem("Po = 0.85f'c(Ag-Ast) + fy·Ast",
                                newton_to_force(po, units), force_unit, "ACI Eq. 22.4.2.2"))
        items.append(ResultItem(f"Pn,max = {pn_factor:.2f}·Po",
                                newton_to_force(pn_max, units), force_unit, "ACI Table 22.4.2.1"))
        items.append(ResultItem("Strength reduction factor φ", phi, "-",
                                f"{'spiral' if spiral else 'tied'}, ACI Table 21.2.2"))
        items.append(ResultItem("Design strength φPn,max",
                                newton_to_force(phi_pn, units), force_unit, "ACI 22.4.2.1"))
        items.append(ResultItem("Factored axial load Pu", newton_to_force(pu_n, units), force_unit))
        ratio = pu_n / phi_pn
        axial_ok = pu_n <= phi_pn
        items.append(ResultItem("Demand / capacity Pu/φPn,max", ratio, "-", _ok(axial_ok)))
        if not axial_ok:
            failures.append("Pu exceeds φPn,max (ACI 318-19 22.4.2.1).")

        # ---- lateral reinforcement
        if spiral:
            self._check_spiral(b, cover, dt, s, fc, fyt, ag, context, items, failures)
        else:
            self._check_ties(db, dt, s, least, items, failures)

        # ---- slenderness (ACI 318-19 6.2.5.1, r per 6.2.5.2)
        r = 0.25 * b if circular else 0.30 * least
        slenderness = k * lu / r
        if v["frame_type"] == FRAME_SWAY:
            limit = 22.0                                     # ACI 318-19 Eq. 6.2.5.1a
            limit_note = "sway: 22, ACI 6.2.5.1(a)"
        else:
            m_ratio = float(v["m1_m2"])
            limit = min(34.0 + 12.0 * m_ratio, 40.0)         # ACI 318-19 Eq. 6.2.5.1b/c
            limit_note = f"nonsway: min(34+12·M1/M2, 40), ACI 6.2.5.1(b),(c)"
        items.append(ResultItem("Radius of gyration r", r, "mm",
                                "0.25D (circular) / 0.30h (rectangular), ACI 6.2.5.2"))
        short_ok = slenderness <= limit
        items.append(ResultItem("Slenderness k·Lu/r", slenderness, "-",
                                f"limit {limit:.1f} ({limit_note}) - "
                                f"{'short column' if short_ok else 'SLENDER'}"))
        if not short_ok:
            out_of_scope.append(
                f"k·Lu/r = {slenderness:.1f} > {limit:.1f}: slenderness effects must be considered "
                "(ACI 318-19 6.6/6.7). Slender column design is not implemented yet."
            )

        # ---- moments are outside the scope of this engine version
        if float(v["moment_x"]) != 0.0 or float(v["moment_y"]) != 0.0:
            out_of_scope.append(
                "Mux/Muy are not zero: combined axial force and moment (interaction diagram, "
                "ACI 318-19 22.4) is not implemented yet. Only the axial capacity was checked."
            )

        if failures:
            status = DesignStatus.FAIL
            summary = f"Column: FAIL - {len(failures)} check(s) not satisfied (ACI 318-19)."
        elif out_of_scope:
            status = DesignStatus.NOT_IMPLEMENTED
            summary = "Column: axial checks OK, but the member is outside the implemented scope."
        else:
            status = DesignStatus.PASS
            summary = f"Column: PASS - Pu/φPn,max = {ratio:.3f} (ACI 318-19, short column)."
        messages = [*failures, *out_of_scope,
                    "Scope: short column, concentric axial load, ACI 318-19 (SI)."]
        return DesignResult(status=status, summary=summary, items=items, messages=messages,
                            standard=context.standard.value, engine=self.engine_name)

    # ------------------------------------------------------- lateral steel
    @staticmethod
    def _check_ties(db: float, dt: float, s: float, least: float,
                    items: list[ResultItem], failures: list[str]) -> None:
        """Tie size (ACI 318-19 25.7.2.2) and spacing (25.7.2.1)."""
        dt_min = TIE_DB_SMALL_MM if db <= LONG_DB_LIMIT_MM else TIE_DB_LARGE_MM
        size_ok = dt >= dt_min
        items.append(ResultItem("Tie bar diameter", dt, "mm",
                                f"min {dt_min:g} mm, ACI 25.7.2.2 - {_ok(size_ok)}"))
        if not size_ok:
            failures.append(f"Tie diameter {dt:g} mm < {dt_min:g} mm (ACI 318-19 25.7.2.2).")
        s_max = min(16.0 * db, 48.0 * dt, least)  # ACI 318-19 25.7.2.1(b)
        s_ok = s <= s_max
        items.append(ResultItem("Maximum tie spacing", s_max, "mm",
                                f"min(16db, 48dt, least dim.), ACI 25.7.2.1(b)"))
        items.append(ResultItem("Tie spacing s", s, "mm", _ok(s_ok)))
        if not s_ok:
            failures.append(f"Tie spacing {s:g} mm > {s_max:g} mm (ACI 318-19 25.7.2.1).")

    @staticmethod
    def _check_spiral(diameter: float, cover: float, dt: float, s: float, fc: float,
                      fyt: float, ag: float, context: CalculationContext,
                      items: list[ResultItem], failures: list[str]) -> None:
        """Spiral size, pitch and volumetric ratio (ACI 318-19 25.7.3)."""
        size_ok = dt >= SPIRAL_DB_MIN_MM
        items.append(ResultItem("Spiral bar diameter", dt, "mm",
                                f"min {SPIRAL_DB_MIN_MM:g} mm, ACI 25.7.3.2 - {_ok(size_ok)}"))
        if not size_ok:
            failures.append(f"Spiral diameter {dt:g} mm < {SPIRAL_DB_MIN_MM:g} mm (ACI 318-19 25.7.3.2).")
        clear = s - dt
        clear_ok = SPIRAL_CLEAR_MIN_MM <= clear <= SPIRAL_CLEAR_MAX_MM
        items.append(ResultItem("Spiral clear spacing", clear, "mm",
                                f"{SPIRAL_CLEAR_MIN_MM:g}-{SPIRAL_CLEAR_MAX_MM:g} mm, ACI 25.7.3.1 - "
                                f"{_ok(clear_ok)}"))
        if not clear_ok:
            failures.append(f"Spiral clear spacing {clear:g} mm is outside "
                            f"{SPIRAL_CLEAR_MIN_MM:g}-{SPIRAL_CLEAR_MAX_MM:g} mm (ACI 318-19 25.7.3.1).")
        fyt_ok = fyt <= FYT_MAX_SPIRAL_MPA
        if not fyt_ok:
            failures.append(f"Spiral fyt = {fyt:.1f} MPa exceeds {FYT_MAX_SPIRAL_MPA:g} MPa "
                            "(ACI 318-19 Table 20.2.2.4(a)).")
        dc = diameter - 2.0 * cover                     # core to outside of spiral
        ach = math.pi * dc ** 2 / 4.0
        asp = math.pi * dt ** 2 / 4.0
        rho_s = 4.0 * asp / (dc * s)                     # spiral volume / core volume
        rho_s_min = 0.45 * (ag / ach - 1.0) * fc / fyt   # ACI 318-19 Eq. 25.7.3.3
        rho_ok = rho_s >= rho_s_min
        items.append(ResultItem("Spiral ratio ρs = 4Asp/(Dc·s)", rho_s, "-",
                                f"fyt ({context.tie_rebar.name}) = {fyt:.1f} MPa"))  # type: ignore[union-attr]
        items.append(ResultItem("Minimum ρs = 0.45(Ag/Ach-1)f'c/fyt", rho_s_min, "-",
                                f"ACI Eq. 25.7.3.3 - {_ok(rho_ok)}"))
        if not rho_ok:
            failures.append(f"Spiral ratio {rho_s:.4f} < required {rho_s_min:.4f} (ACI 318-19 25.7.3.3).")
