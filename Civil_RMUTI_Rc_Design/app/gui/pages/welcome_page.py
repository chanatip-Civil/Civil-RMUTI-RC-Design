"""Start page shown when no project is open."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.core.constants import APP_NAME, APP_PHASE, APP_VERSION
from app.gui.widgets.icons import app_pixmap


class WelcomePage(QWidget):
    """Home page with New / Open buttons and recent projects."""

    new_requested = Signal()
    open_requested = Signal()
    recent_requested = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        logo = QLabel()
        logo.setPixmap(app_pixmap(96))
        logo.setAlignment(Qt.AlignmentFlag.AlignCenter)

        title = QLabel(APP_NAME)
        title.setObjectName("PageTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle = QLabel(
            "Reinforced Concrete Structural Design Software\n"
            "โปรแกรมออกแบบโครงสร้างคอนกรีตเสริมเหล็ก"
        )
        subtitle.setObjectName("PageSubtitle")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        version = QLabel(f"Version {APP_VERSION} · {APP_PHASE}")
        version.setObjectName("PageSubtitle")
        version.setAlignment(Qt.AlignmentFlag.AlignCenter)

        new_button = QPushButton("New Project")
        new_button.setObjectName("PrimaryButton")
        new_button.setMinimumHeight(36)
        new_button.clicked.connect(self.new_requested)
        open_button = QPushButton("Open Project...")
        open_button.setMinimumHeight(36)
        open_button.clicked.connect(self.open_requested)
        buttons = QHBoxLayout()
        buttons.addStretch()
        buttons.addWidget(new_button)
        buttons.addWidget(open_button)
        buttons.addStretch()

        recent_panel = QFrame()
        recent_panel.setObjectName("Panel")
        recent_panel.setMaximumWidth(640)
        recent_layout = QVBoxLayout(recent_panel)
        recent_title = QLabel("Recent Projects")
        recent_title.setStyleSheet("font-weight: bold;")
        self._recent_list = QListWidget()
        self._recent_list.setMinimumHeight(140)
        self._recent_list.itemActivated.connect(self._on_recent_activated)
        self._recent_list.itemDoubleClicked.connect(self._on_recent_activated)
        recent_layout.addWidget(recent_title)
        recent_layout.addWidget(self._recent_list)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.addStretch(1)
        layout.addWidget(logo)
        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addWidget(version)
        layout.addSpacing(20)
        layout.addLayout(buttons)
        layout.addSpacing(20)
        layout.addWidget(recent_panel, alignment=Qt.AlignmentFlag.AlignHCenter)
        layout.addStretch(2)

    def set_recent_projects(self, paths: list[str]) -> None:
        """Fill the recent project list."""
        self._recent_list.clear()
        if not paths:
            item = QListWidgetItem("No recent projects")
            item.setFlags(Qt.ItemFlag.NoItemFlags)
            self._recent_list.addItem(item)
            return
        for path in paths:
            item = QListWidgetItem(f"{Path(path).name}    —    {path}")
            item.setData(Qt.ItemDataRole.UserRole, path)
            item.setToolTip(path)
            self._recent_list.addItem(item)

    def _on_recent_activated(self, item: QListWidgetItem) -> None:
        path = item.data(Qt.ItemDataRole.UserRole)
        if path:
            self.recent_requested.emit(str(path))
