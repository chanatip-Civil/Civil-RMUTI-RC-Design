"""Visual theme: colour palette and Qt style sheet."""

from __future__ import annotations

from app.core.constants import DesignType

PRIMARY: str = "#1F4E79"        # engineering blue
PRIMARY_DARK: str = "#163A5A"
PRIMARY_LIGHT: str = "#E8F0F8"
ACCENT: str = "#C8102E"         # RMUTI red accent
BACKGROUND: str = "#F3F5F8"
SURFACE: str = "#FFFFFF"
BORDER: str = "#D0D7E2"
TEXT: str = "#1E2A38"
TEXT_MUTED: str = "#5B6B7F"
SUCCESS: str = "#2E7D32"
WARNING: str = "#B26A00"
ERROR: str = "#C62828"
INVALID_BG: str = "#FDECEC"

DESIGN_COLORS: dict[DesignType, str] = {
    DesignType.COLUMN: "#1F4E79",
    DesignType.BEAM: "#2E7D32",
    DesignType.SLAB: "#6A1B9A",
    DesignType.STAIR: "#B26A00",
    DesignType.FOOTING: "#8D4E2A",
}

APP_STYLESHEET: str = f"""
QMainWindow, QDialog {{
    background: {BACKGROUND};
}}
QWidget {{
    color: {TEXT};
    font-size: 10pt;
}}
QMenuBar {{
    background: {SURFACE};
    border-bottom: 1px solid {BORDER};
}}
QMenuBar::item:selected {{
    background: {PRIMARY_LIGHT};
}}
QMenu::item:selected {{
    background: {PRIMARY};
    color: white;
}}
QToolBar {{
    background: {SURFACE};
    border-bottom: 1px solid {BORDER};
    spacing: 4px;
    padding: 3px;
}}
QToolButton {{
    padding: 4px 8px;
    border-radius: 4px;
}}
QToolButton:hover {{
    background: {PRIMARY_LIGHT};
}}
QStatusBar {{
    background: {PRIMARY};
    color: white;
}}
QStatusBar QLabel {{
    color: white;
    padding: 0 8px;
}}
#SidebarFrame {{
    background: {SURFACE};
    border-right: 1px solid {BORDER};
}}
#SidebarHeader {{
    background: {PRIMARY};
    color: white;
    font-weight: bold;
    padding: 8px 10px;
}}
QTreeWidget, QListWidget {{
    background: {SURFACE};
    border: none;
}}
QTreeWidget::item, QListWidget::item {{
    padding: 4px 2px;
}}
QTreeWidget::item:selected, QListWidget::item:selected {{
    background: {PRIMARY_LIGHT};
    color: {PRIMARY_DARK};
}}
#PageTitle {{
    font-size: 18pt;
    font-weight: bold;
    color: {PRIMARY_DARK};
}}
#PageSubtitle {{
    font-size: 10pt;
    color: {TEXT_MUTED};
}}
#DesignCard {{
    background: {SURFACE};
    border: 1px solid {BORDER};
    border-radius: 10px;
}}
#DesignCard:hover {{
    border: 2px solid {PRIMARY};
    background: {PRIMARY_LIGHT};
}}
#DesignCard:focus {{
    border: 2px solid {ACCENT};
}}
#CardTitle {{
    font-size: 14pt;
    font-weight: bold;
}}
#CardMuted {{
    color: {TEXT_MUTED};
}}
#Panel {{
    background: {SURFACE};
    border: 1px solid {BORDER};
    border-radius: 6px;
}}
QGroupBox {{
    background: {SURFACE};
    border: 1px solid {BORDER};
    border-radius: 6px;
    margin-top: 14px;
    padding: 10px 8px 8px 8px;
    font-weight: bold;
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 4px;
    color: {PRIMARY};
}}
QLineEdit, QComboBox, QDateEdit, QPlainTextEdit, QTextBrowser {{
    background: {SURFACE};
    border: 1px solid {BORDER};
    border-radius: 4px;
    padding: 3px 6px;
}}
QLineEdit:focus, QComboBox:focus, QDateEdit:focus, QPlainTextEdit:focus {{
    border: 1px solid {PRIMARY};
}}
QLineEdit[invalid="true"] {{
    border: 1px solid {ERROR};
    background: {INVALID_BG};
}}
QPushButton {{
    background: {SURFACE};
    border: 1px solid {BORDER};
    border-radius: 4px;
    padding: 5px 14px;
}}
QPushButton:hover {{
    background: {PRIMARY_LIGHT};
    border-color: {PRIMARY};
}}
QPushButton:disabled {{
    color: #9AA5B4;
}}
QPushButton#PrimaryButton {{
    background: {PRIMARY};
    color: white;
    border: 1px solid {PRIMARY_DARK};
    font-weight: bold;
}}
QPushButton#PrimaryButton:hover {{
    background: {PRIMARY_DARK};
}}
QHeaderView::section {{
    background: {PRIMARY_LIGHT};
    color: {PRIMARY_DARK};
    border: none;
    border-right: 1px solid {BORDER};
    padding: 4px;
    font-weight: bold;
}}
QTableWidget {{
    background: {SURFACE};
    gridline-color: {BORDER};
    border: 1px solid {BORDER};
}}
QTabWidget::pane {{
    border: 1px solid {BORDER};
    background: {SURFACE};
}}
QTabBar::tab {{
    padding: 6px 14px;
}}
QTabBar::tab:selected {{
    background: {SURFACE};
    border-bottom: 2px solid {PRIMARY};
}}
"""


def status_color(status_value: str) -> str:
    """Colour for a :class:`DesignStatus` value."""
    return {
        "pass": SUCCESS,
        "fail": ERROR,
        "error": ERROR,
        "not_implemented": WARNING,
    }.get(status_value, TEXT_MUTED)
