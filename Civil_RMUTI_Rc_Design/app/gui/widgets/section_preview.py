"""Geometry preview drawn with matplotlib (falls back to a label)."""

from __future__ import annotations

import math
from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

from app.core.constants import DesignType
from app.core.logger import get_logger
from app.gui.styles import DESIGN_COLORS
from app.utils.validators import parse_number

_log = get_logger("preview")

try:  # matplotlib is optional at runtime; the app must still start without it.
    from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
    from matplotlib.figure import Figure
    from matplotlib.patches import Circle, Polygon, Rectangle

    MATPLOTLIB_AVAILABLE = True
except ImportError:  # pragma: no cover - depends on installation
    MATPLOTLIB_AVAILABLE = False

_CONCRETE = "#DDE3EA"


class SectionPreview(QWidget):
    """Shows a schematic sketch of the member geometry."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setMinimumSize(260, 220)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self._canvas = None
        self._figure = None
        if MATPLOTLIB_AVAILABLE:
            self._figure = Figure(figsize=(3.2, 2.8), dpi=100, layout="tight")
            self._canvas = FigureCanvasQTAgg(self._figure)
            layout.addWidget(self._canvas)
        else:
            label = QLabel("Preview requires matplotlib\n(pip install matplotlib)")
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(label)

    def update_preview(self, design_type: DesignType, inputs: dict[str, Any]) -> None:
        """Redraw the sketch for *design_type* using raw *inputs*."""
        if self._figure is None or self._canvas is None:
            return
        self._figure.clear()
        axes = self._figure.add_subplot(111)
        axes.set_aspect("equal")
        axes.axis("off")
        values = {key: parse_number(value) for key, value in inputs.items()}
        color = DESIGN_COLORS[design_type]
        try:
            drawer = {
                DesignType.COLUMN: self._draw_column,
                DesignType.BEAM: self._draw_beam,
                DesignType.SLAB: self._draw_slab,
                DesignType.STAIR: self._draw_stair,
                DesignType.FOOTING: self._draw_footing,
            }[design_type]
            drawer(axes, inputs, values, color)
            axes.autoscale_view()
            axes.margins(0.15)
        except (TypeError, ValueError, ZeroDivisionError, KeyError, OverflowError):
            axes.clear()
            axes.axis("off")
            axes.text(0.5, 0.5, "Preview unavailable\n(invalid input)",
                      ha="center", va="center", transform=axes.transAxes, color="#5B6B7F")
        except Exception:  # Never let drawing problems crash the editor.
            _log.exception("Preview drawing failed")
        self._canvas.draw_idle()

    # ----------------------------------------------------------------- drawers
    @staticmethod
    def _need(values: dict[str, float | None], *keys: str) -> list[float]:
        result: list[float] = []
        for key in keys:
            value = values.get(key)
            if value is None or value <= 0:
                raise ValueError(key)
            result.append(value)
        return result

    def _draw_column(self, ax: Any, raw: dict[str, Any], values: dict, color: str) -> None:
        cover = values.get("cover") or 0.0
        if raw.get("shape") == "Circular":
            (diameter,) = self._need(values, "width")
            ax.add_patch(Circle((0, 0), diameter / 2, fc=_CONCRETE, ec=color, lw=2))
            if 0 < cover < diameter / 2:
                ax.add_patch(Circle((0, 0), diameter / 2 - cover, fill=False, ec=color, ls="--"))
            ax.set_title(f"Circular column D = {diameter:g} mm", fontsize=9)
            ax.set_xlim(-diameter / 2, diameter / 2)
            ax.set_ylim(-diameter / 2, diameter / 2)
            return
        width, depth = self._need(values, "width", "depth")
        ax.add_patch(Rectangle((0, 0), width, depth, fc=_CONCRETE, ec=color, lw=2))
        if 0 < 2 * cover < min(width, depth):
            ax.add_patch(Rectangle((cover, cover), width - 2 * cover, depth - 2 * cover,
                                   fill=False, ec=color, ls="--"))
        ax.set_title(f"Column section {width:g} x {depth:g} mm", fontsize=9)
        ax.set_xlim(0, width)
        ax.set_ylim(0, depth)

    def _draw_beam(self, ax: Any, raw: dict[str, Any], values: dict, color: str) -> None:
        width, depth = self._need(values, "width", "depth")
        cover = values.get("cover") or 0.0
        ax.add_patch(Rectangle((0, 0), width, depth, fc=_CONCRETE, ec=color, lw=2))
        if 0 < 2 * cover < min(width, depth):
            ax.add_patch(Rectangle((cover, cover), width - 2 * cover, depth - 2 * cover,
                                   fill=False, ec=color, ls="--"))
        ax.set_title(f"Beam section {width:g} x {depth:g} mm", fontsize=9)
        ax.set_xlim(0, width)
        ax.set_ylim(0, depth)

    def _draw_slab(self, ax: Any, raw: dict[str, Any], values: dict, color: str) -> None:
        lx, ly = self._need(values, "short_span", "long_span")
        ax.add_patch(Rectangle((0, 0), ly, lx, fc=_CONCRETE, ec=color, lw=2))
        ax.text(ly / 2, -0.08 * lx, f"Ly = {ly:g} m", ha="center", va="top", fontsize=8)
        ax.text(-0.04 * ly, lx / 2, f"Lx = {lx:g} m", ha="right", va="center",
                rotation=90, fontsize=8)
        ax.set_title(f"{raw.get('slab_type', '')} slab plan", fontsize=9)
        ax.set_xlim(0, ly)
        ax.set_ylim(0, lx)

    def _draw_stair(self, ax: Any, raw: dict[str, Any], values: dict, color: str) -> None:
        height, riser, tread = self._need(values, "floor_height", "riser", "tread")
        count = max(1, math.ceil(height / riser - 1e-9))
        if count > 200:
            raise ValueError("too many steps")
        actual = height / count
        xs, ys = [0.0], [0.0]
        x = y = 0.0
        for index in range(count):
            y += actual
            xs.append(x)
            ys.append(y)
            if index < count - 1:
                x += tread
                xs.append(x)
                ys.append(y)
        points = list(zip(xs, ys)) + [(x, y - actual * 0.6), (tread * 0.6, 0.0)]
        ax.add_patch(Polygon(points, closed=True, fc=_CONCRETE, ec=color, lw=1.5))
        ax.set_title(f"{count} risers x {actual:.0f} mm", fontsize=9)
        ax.set_xlim(0, max(x, tread))
        ax.set_ylim(0, height)

    def _draw_footing(self, ax: Any, raw: dict[str, Any], values: dict, color: str) -> None:
        width, length = self._need(values, "width", "length")
        cx = (values.get("column_width") or 0.0) / 1000.0
        cy = (values.get("column_depth") or 0.0) / 1000.0
        ax.add_patch(Rectangle((0, 0), width, length, fc=_CONCRETE, ec=color, lw=2))
        if 0 < cx < width and 0 < cy < length:
            ax.add_patch(Rectangle(((width - cx) / 2, (length - cy) / 2), cx, cy,
                                   fc="#9AA5B4", ec=color, lw=1.5))
        ax.set_title(f"Footing plan {width:g} x {length:g} m", fontsize=9)
        ax.set_xlim(0, width)
        ax.set_ylim(0, length)
