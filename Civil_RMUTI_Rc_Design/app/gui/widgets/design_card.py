"""Clickable card representing one design type."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QKeyEvent, QMouseEvent
from PySide6.QtWidgets import QFrame, QLabel, QSizePolicy, QVBoxLayout

from app.core.constants import DesignType
from app.gui.widgets.icons import design_pixmap


class DesignCard(QFrame):
    """Card with icon, title and description. Emits :attr:`clicked`."""

    clicked = Signal(object)  # DesignType

    def __init__(self, design_type: DesignType, parent: QFrame | None = None) -> None:
        super().__init__(parent)
        self.design_type = design_type
        self.setObjectName("DesignCard")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setMinimumSize(230, 190)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setToolTip(f"Open {design_type.description}")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(4)

        icon = QLabel()
        icon.setPixmap(design_pixmap(design_type, 64))
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

        title = QLabel(design_type.title.upper())
        title.setObjectName("CardTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        subtitle = QLabel(design_type.description)
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setWordWrap(True)

        thai = QLabel(design_type.description_th)
        thai.setObjectName("CardMuted")
        thai.setAlignment(Qt.AlignmentFlag.AlignCenter)
        thai.setWordWrap(True)

        self._count_label = QLabel()
        self._count_label.setObjectName("CardMuted")
        self._count_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        for widget in (icon, title, subtitle, thai, self._count_label):
            widget.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
            layout.addWidget(widget)
        self.set_member_count(0)

    def set_member_count(self, count: int) -> None:
        """Show how many members of this type exist in the project."""
        noun = "member" if count == 1 else "members"
        self._count_label.setText(f"{count} {noun} in project")

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:  # noqa: N802 (Qt API)
        """Emit :attr:`clicked` on left click."""
        if event.button() == Qt.MouseButton.LeftButton and self.rect().contains(
            event.position().toPoint()
        ):
            self.clicked.emit(self.design_type)
        super().mouseReleaseEvent(event)

    def keyPressEvent(self, event: QKeyEvent) -> None:  # noqa: N802 (Qt API)
        """Activate with Enter / Space."""
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter, Qt.Key.Key_Space):
            self.clicked.emit(self.design_type)
            return
        super().keyPressEvent(event)
