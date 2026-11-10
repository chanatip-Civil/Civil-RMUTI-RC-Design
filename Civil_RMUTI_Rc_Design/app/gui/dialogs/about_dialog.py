"""About Civil RMUTI Rc Design."""

from __future__ import annotations

import platform

from PySide6 import __version__ as pyside_version
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QDialogButtonBox, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from app.core.constants import APP_NAME, APP_PHASE, APP_VERSION, ORGANIZATION_NAME
from app.gui.widgets.icons import app_pixmap


class AboutDialog(QDialog):
    """Program name, version and technology information."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(f"About {APP_NAME}")
        self.setMinimumWidth(480)

        logo = QLabel()
        logo.setPixmap(app_pixmap(80))
        logo.setAlignment(Qt.AlignmentFlag.AlignTop)

        text = QLabel(
            f"<h2>{APP_NAME}</h2>"
            f"<p><b>Version {APP_VERSION}</b><br>{APP_PHASE}</p>"
            "<p>Desktop application for the design of reinforced concrete "
            "structures: columns, beams, slabs, stairs and footings.<br>"
            "โปรแกรมออกแบบโครงสร้างคอนกรีตเสริมเหล็ก</p>"
            f"<p>{ORGANIZATION_NAME}</p>"
            f"<p style='color:#5B6B7F'>Python {platform.python_version()} · "
            f"PySide6 {pyside_version}</p>"
            "<p style='color:#C62828'><b>Notice:</b> structural design checks are not "
            "implemented in this build. Do not use results for construction.</p>"
        )
        text.setWordWrap(True)
        text.setTextFormat(Qt.TextFormat.RichText)

        row = QHBoxLayout()
        row.addWidget(logo)
        row.addWidget(text, 1)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
        buttons.accepted.connect(self.accept)

        layout = QVBoxLayout(self)
        layout.addLayout(row)
        layout.addWidget(buttons)
