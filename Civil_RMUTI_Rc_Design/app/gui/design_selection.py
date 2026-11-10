"""Design Selection page: one card per design type."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QGridLayout, QHBoxLayout, QLabel, QScrollArea, QVBoxLayout, QWidget

from app.core.constants import DesignType
from app.core.project_model import Project
from app.gui.widgets.design_card import DesignCard


class DesignSelectionPage(QWidget):
    """Grid of :class:`DesignCard` (2 columns, footing centred on the last row)."""

    design_selected = Signal(object)  # DesignType

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        title = QLabel("SELECT DESIGN TYPE")
        title.setObjectName("PageTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle = QLabel("เลือกประเภทโครงสร้างที่ต้องการออกแบบ — choose a member type to design")
        subtitle.setObjectName("PageSubtitle")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._cards: dict[DesignType, DesignCard] = {}
        grid = QGridLayout()
        grid.setSpacing(18)
        types = list(DesignType)
        for index, design_type in enumerate(types[:-1]):
            card = self._make_card(design_type)
            grid.addWidget(card, index // 2, index % 2)

        last_row = QHBoxLayout()
        last_row.addStretch(1)
        last_card = self._make_card(types[-1])
        last_row.addWidget(last_card, 2)
        last_row.addStretch(1)
        grid.addLayout(last_row, (len(types) - 1) // 2, 0, 1, 2)

        content = QWidget()
        content.setMaximumWidth(820)
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(24, 24, 24, 24)
        content_layout.addWidget(title)
        content_layout.addWidget(subtitle)
        content_layout.addSpacing(16)
        content_layout.addLayout(grid)
        content_layout.addStretch()

        wrapper = QWidget()
        wrapper_layout = QHBoxLayout(wrapper)
        wrapper_layout.addStretch()
        wrapper_layout.addWidget(content, 10)
        wrapper_layout.addStretch()

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll.setWidget(wrapper)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(scroll)

    def _make_card(self, design_type: DesignType) -> DesignCard:
        card = DesignCard(design_type)
        card.clicked.connect(self.design_selected.emit)
        self._cards[design_type] = card
        return card

    def update_counts(self, project: Project | None) -> None:
        """Refresh member counts on the cards."""
        for design_type, card in self._cards.items():
            card.set_member_count(project.member_count(design_type) if project else 0)
