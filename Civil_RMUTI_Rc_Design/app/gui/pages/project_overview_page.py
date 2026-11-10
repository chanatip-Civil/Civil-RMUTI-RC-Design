"""Project information / summary page."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from app.core.constants import APP_NAME, DesignType
from app.core.project_model import Project


class ProjectOverviewPage(QWidget):
    """Read-only summary of the open project with an Edit button."""

    edit_requested = Signal()
    design_selection_requested = Signal()

    _INFO_FIELDS: tuple[tuple[str, str], ...] = (
        ("project_name", "Project Name"),
        ("project_number", "Project Number"),
        ("designer", "Designer"),
        ("checker", "Checker"),
        ("organization", "Company / Organization"),
        ("project_date", "Date"),
        ("location", "Location"),
        ("description", "Description"),
    )

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        title = QLabel("Project Information")
        title.setObjectName("PageTitle")
        subtitle = QLabel(f"{APP_NAME} — project summary")
        subtitle.setObjectName("PageSubtitle")

        self._info_labels: dict[str, QLabel] = {}
        info_box = QGroupBox("General")
        info_form = QFormLayout(info_box)
        for key, label in self._INFO_FIELDS:
            value = QLabel("-")
            value.setWordWrap(True)
            value.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            self._info_labels[key] = value
            info_form.addRow(f"{label}:", value)

        settings_box = QGroupBox("Design Settings")
        settings_form = QFormLayout(settings_box)
        self._standard_label = QLabel("-")
        self._unit_label = QLabel("-")
        self._materials_label = QLabel("-")
        self._file_label = QLabel("-")
        self._file_label.setWordWrap(True)
        self._file_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        settings_form.addRow("Design Standard:", self._standard_label)
        settings_form.addRow("Unit System:", self._unit_label)
        settings_form.addRow("Default Materials:", self._materials_label)
        settings_form.addRow("Project File:", self._file_label)

        members_box = QGroupBox("Members")
        members_form = QFormLayout(members_box)
        self._count_labels: dict[DesignType, QLabel] = {}
        for design_type in DesignType:
            label = QLabel("0")
            self._count_labels[design_type] = label
            members_form.addRow(f"{design_type.title}s:", label)

        edit_button = QPushButton("Edit Project Information...")
        edit_button.clicked.connect(self.edit_requested)
        design_button = QPushButton("Go to Design Selection")
        design_button.setObjectName("PrimaryButton")
        design_button.clicked.connect(self.design_selection_requested)
        buttons = QHBoxLayout()
        buttons.addWidget(edit_button)
        buttons.addStretch()
        buttons.addWidget(design_button)

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(24, 24, 24, 24)
        content_layout.addWidget(title)
        content_layout.addWidget(subtitle)
        content_layout.addSpacing(8)
        content_layout.addWidget(info_box)
        row = QHBoxLayout()
        row.addWidget(settings_box, 2)
        row.addWidget(members_box, 1)
        content_layout.addLayout(row)
        content_layout.addLayout(buttons)
        content_layout.addStretch()

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll.setWidget(content)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(scroll)

    def update_project(self, project: Project | None, file_path: Path | None) -> None:
        """Show the data of *project*."""
        if project is None:
            return
        info = project.information.to_dict()
        for key, label in self._info_labels.items():
            label.setText(str(info.get(key) or "-"))
        settings = project.settings
        self._standard_label.setText(settings.standard.label)
        self._unit_label.setText(settings.units.label)
        self._materials_label.setText(
            f"Concrete {settings.default_concrete} · Main bars {settings.default_main_rebar}"
            f" · Ties {settings.default_tie_rebar}"
        )
        self._file_label.setText(str(file_path) if file_path else "Not saved yet")
        for design_type, label in self._count_labels.items():
            label.setText(str(project.member_count(design_type)))
