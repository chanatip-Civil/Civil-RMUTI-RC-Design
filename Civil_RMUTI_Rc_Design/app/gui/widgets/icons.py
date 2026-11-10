"""Vector icons drawn with QPainter.

Icons are generated at runtime, so the application needs no image assets and
stays sharp on High-DPI screens. All drawing uses a 64 x 64 logical canvas.
"""

from __future__ import annotations

from pathlib import Path
from typing import Callable

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import (
    QBrush,
    QColor,
    QFont,
    QGuiApplication,
    QIcon,
    QPainter,
    QPen,
    QPixmap,
    QPolygonF,
)

from app.core.constants import DesignType
from app.core.paths import resource_path
from app.gui.styles import ACCENT, DESIGN_COLORS, PRIMARY

_CANVAS: float = 64.0
#: Application logo (transparent PNG). Replace this file to change the logo.
LOGO_PATH: Path = resource_path("app", "gui", "resources", "rmuti_logo.png")
_CONCRETE_FILL: str = "#DDE3EA"
_ICON_SIZES: tuple[int, ...] = (16, 24, 32, 48, 64, 128)

Painter = Callable[[QPainter, QColor], None]


def _device_ratio() -> float:
    screen = QGuiApplication.primaryScreen()
    return float(screen.devicePixelRatio()) if screen is not None else 1.0


def _render(size: int, draw: Painter, color: QColor) -> QPixmap:
    ratio = max(1.0, _device_ratio())
    pixmap = QPixmap(int(size * ratio), int(size * ratio))
    pixmap.setDevicePixelRatio(ratio)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    painter.scale(size / _CANVAS, size / _CANVAS)
    draw(painter, color)
    painter.end()
    return pixmap


def _pen(color: QColor, width: float = 2.5) -> QPen:
    pen = QPen(color, width)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    return pen


def _draw_column(p: QPainter, color: QColor) -> None:
    p.setPen(_pen(color))
    p.setBrush(QBrush(QColor(_CONCRETE_FILL)))
    p.drawRect(QRectF(22, 6, 20, 52))
    p.setBrush(QBrush(color))
    p.setPen(Qt.PenStyle.NoPen)
    for x in (27.0, 37.0):
        p.drawRect(QRectF(x - 1.2, 9, 2.4, 46))
    p.setPen(_pen(color, 1.5))
    for y in range(14, 56, 8):
        p.drawLine(QPointF(24, y), QPointF(40, y))


def _draw_beam(p: QPainter, color: QColor) -> None:
    p.setPen(_pen(color))
    p.setBrush(QBrush(QColor(_CONCRETE_FILL)))
    p.drawRect(QRectF(4, 20, 56, 20))
    p.setBrush(QBrush(color))
    p.drawPolygon(QPolygonF([QPointF(10, 40), QPointF(5, 50), QPointF(15, 50)]))
    p.drawPolygon(QPolygonF([QPointF(54, 40), QPointF(49, 50), QPointF(59, 50)]))
    p.setPen(_pen(color, 2.0))
    p.drawLine(QPointF(8, 35), QPointF(56, 35))
    p.drawLine(QPointF(8, 25), QPointF(56, 25))


def _draw_slab(p: QPainter, color: QColor) -> None:
    p.setPen(_pen(color))
    p.setBrush(QBrush(QColor(_CONCRETE_FILL)))
    top = QPolygonF([QPointF(4, 30), QPointF(22, 16), QPointF(60, 16), QPointF(42, 30)])
    p.drawPolygon(top)
    p.drawPolygon(QPolygonF([QPointF(4, 30), QPointF(42, 30), QPointF(42, 38), QPointF(4, 38)]))
    p.drawPolygon(QPolygonF([QPointF(42, 30), QPointF(60, 16), QPointF(60, 24), QPointF(42, 38)]))
    p.setPen(_pen(color, 1.2))
    for i in range(1, 4):
        t = i / 4.0
        p.drawLine(QPointF(4 + 18 * t, 30 - 14 * t), QPointF(42 + 18 * t, 30 - 14 * t))
    p.setPen(_pen(color, 2.5))
    p.drawLine(QPointF(10, 38), QPointF(10, 56))
    p.drawLine(QPointF(38, 38), QPointF(38, 56))


def _draw_stair(p: QPainter, color: QColor) -> None:
    p.setPen(_pen(color))
    p.setBrush(QBrush(QColor(_CONCRETE_FILL)))
    points = [QPointF(6, 58)]
    x, y = 6.0, 58.0
    for _ in range(5):
        y -= 10
        points.append(QPointF(x, y))
        x += 10
        points.append(QPointF(x, y))
    points.extend([QPointF(58, 8), QPointF(58, 18), QPointF(20, 58)])
    p.drawPolygon(QPolygonF(points))


def _draw_footing(p: QPainter, color: QColor) -> None:
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QBrush(QColor("#C9B79C")))
    p.drawRect(QRectF(2, 50, 60, 10))
    p.setPen(_pen(color))
    p.setBrush(QBrush(QColor(_CONCRETE_FILL)))
    p.drawRect(QRectF(26, 6, 12, 34))
    p.drawRect(QRectF(8, 38, 48, 14))
    p.setPen(_pen(color, 1.8))
    p.drawLine(QPointF(12, 48), QPointF(52, 48))


def _draw_app(p: QPainter, color: QColor) -> None:
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QBrush(QColor(PRIMARY)))
    p.drawRoundedRect(QRectF(2, 2, 60, 60), 12, 12)
    p.setBrush(QBrush(QColor(ACCENT)))
    p.drawRect(QRectF(2, 48, 60, 6))
    p.setPen(QPen(QColor("white")))
    font = QFont()
    font.setBold(True)
    font.setPixelSize(26)
    p.setFont(font)
    p.drawText(QRectF(2, 6, 60, 40), Qt.AlignmentFlag.AlignCenter, "RC")


_DRAWERS: dict[DesignType, Painter] = {
    DesignType.COLUMN: _draw_column,
    DesignType.BEAM: _draw_beam,
    DesignType.SLAB: _draw_slab,
    DesignType.STAIR: _draw_stair,
    DesignType.FOOTING: _draw_footing,
}


def design_pixmap(design_type: DesignType, size: int = 64) -> QPixmap:
    """Pixmap of the icon of *design_type*."""
    return _render(size, _DRAWERS[design_type], QColor(DESIGN_COLORS[design_type]))


def design_icon(design_type: DesignType) -> QIcon:
    """Multi-resolution icon of *design_type*."""
    icon = QIcon()
    for size in _ICON_SIZES:
        icon.addPixmap(design_pixmap(design_type, size))
    return icon


def app_pixmap(size: int = 64) -> QPixmap:
    """Pixmap of the application logo (RMUTI emblem; drawn fallback if missing)."""
    if LOGO_PATH.is_file():
        source = QPixmap(str(LOGO_PATH))
        if not source.isNull():
            ratio = max(1.0, _device_ratio())
            pixmap = source.scaled(
                int(size * ratio), int(size * ratio),
                Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation,
            )
            pixmap.setDevicePixelRatio(ratio)
            return pixmap
    return _render(size, _draw_app, QColor(PRIMARY))


def app_icon() -> QIcon:
    """Multi-resolution application icon."""
    icon = QIcon()
    for size in _ICON_SIZES:
        icon.addPixmap(app_pixmap(size))
    return icon
