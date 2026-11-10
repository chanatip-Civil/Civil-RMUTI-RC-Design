"""Application settings dialog."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGroupBox,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.core.constants import DesignStandard, UnitSystem
from app.core.logger import LOG_FILE_NAME
from app.core.settings import SettingsManager, app_data_dir, logs_dir
from app.materials.database import LIBRARY_FILE_NAME


class SettingsDialog(QDialog):
    """Edit defaults used for new projects."""

    def __init__(self, settings_manager: SettingsManager, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setMinimumWidth(520)
        self._manager = settings_manager
        settings = settings_manager.settings

        defaults = QGroupBox("Defaults for New Projects")
        form = QFormLayout(defaults)
        self._designer = QLineEdit(settings.default_designer)
        self._organization = QLineEdit(settings.default_organization)
        self._standard = QComboBox()
        for standard in DesignStandard:
            self._standard.addItem(standard.label, standard.value)
        self._standard.setCurrentIndex(max(0, self._standard.findData(settings.default_design_standard)))
        self._units = QComboBox()
        for unit in UnitSystem:
            self._units.addItem(unit.label, unit.value)
        self._units.setCurrentIndex(max(0, self._units.findData(settings.default_unit_system)))
        form.addRow("Designer", self._designer)
        form.addRow("Company / Organization", self._organization)
        form.addRow("Design Standard", self._standard)
        form.addRow("Unit System", self._units)

        files = QGroupBox("Files")
        files_form = QFormLayout(files)
        files_form.addRow("Data folder", QLabel(str(app_data_dir())))
        files_form.addRow("Error log", QLabel(str(logs_dir() / LOG_FILE_NAME)))
        files_form.addRow("Material library", QLabel(str(app_data_dir() / LIBRARY_FILE_NAME)))
        self._clear_recent = QPushButton(f"Clear Recent Projects ({len(settings.recent_projects)})")
        self._clear_recent.clicked.connect(self._on_clear_recent)
        files_form.addRow("", self._clear_recent)
        self._reset = QPushButton("Reset All Settings")
        self._reset.setToolTip("Restore default settings and clear recent projects "
                               "(project files and the material library are kept)")
        self._reset.clicked.connect(self._on_reset)
        files_form.addRow("", self._reset)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addWidget(defaults)
        layout.addWidget(files)
        layout.addWidget(buttons)

    def _on_clear_recent(self) -> None:
        self._manager.clear_recent_projects()
        self._clear_recent.setText("Clear Recent Projects (0)")

    def _on_reset(self) -> None:
        answer = QMessageBox.question(
            self, "Reset All Settings",
            "Restore default settings and clear the recent project list?\n"
            "Project files and the material library are not affected.",
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        self._manager.reset()
        defaults = self._manager.settings
        self._designer.setText(defaults.default_designer)
        self._organization.setText(defaults.default_organization)
        self._standard.setCurrentIndex(max(0, self._standard.findData(defaults.default_design_standard)))
        self._units.setCurrentIndex(max(0, self._units.findData(defaults.default_unit_system)))
        self._clear_recent.setText("Clear Recent Projects (0)")

    def _on_accept(self) -> None:
        settings = self._manager.settings
        settings.default_designer = self._designer.text().strip()
        settings.default_organization = self._organization.text().strip()
        settings.default_design_standard = str(self._standard.currentData())
        settings.default_unit_system = str(self._units.currentData())
        self._manager.save()
        self.accept()
