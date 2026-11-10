"""New Project / Project Properties dialog."""

from __future__ import annotations

from PySide6.QtCore import QDate
from PySide6.QtWidgets import (
    QComboBox,
    QDateEdit,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGroupBox,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QVBoxLayout,
    QWidget,
)

from app.core.constants import APP_NAME, DesignStandard, UnitSystem
from app.core.project_model import DesignSettings, ProjectInformation
from app.core.settings import AppSettings
from app.gui.styles import ERROR
from app.materials.database import MaterialLibrary
from app.utils.validators import ValidationResult, validate_required_text

_DATE_FORMAT = "yyyy-MM-dd"


class NewProjectDialog(QDialog):
    """Collects project information and design settings.

    Used for *New Project* and, with ``edit_mode=True``, for editing the
    properties of the open project. Default material choices come from
    *concrete_names* / *grade_names* (project materials) or, when omitted,
    from the material *library*.
    """

    def __init__(
        self,
        app_settings: AppSettings,
        parent: QWidget | None = None,
        information: ProjectInformation | None = None,
        design_settings: DesignSettings | None = None,
        edit_mode: bool = False,
        library: MaterialLibrary | None = None,
        concrete_names: list[str] | None = None,
        grade_names: list[str] | None = None,
    ) -> None:
        super().__init__(parent)
        self._edit_mode = edit_mode
        self._original_units = design_settings.unit_system if design_settings else None
        self.setWindowTitle(f"{APP_NAME} — {'Project Properties' if edit_mode else 'New Project'}")
        self.setMinimumWidth(560)

        info = information or ProjectInformation(
            designer=app_settings.default_designer,
            organization=app_settings.default_organization,
        )
        settings = design_settings or DesignSettings(
            design_standard=app_settings.default_design_standard,
            unit_system=app_settings.default_unit_system,
        )

        header = QLabel("Project Properties" if edit_mode else "Create a New Project")
        header.setObjectName("PageTitle")

        info_box = QGroupBox("Project Information")
        info_form = QFormLayout(info_box)
        self._name = QLineEdit(info.project_name)
        self._name.setPlaceholderText("e.g. 3-Storey Office Building")
        self._number = QLineEdit(info.project_number)
        self._designer = QLineEdit(info.designer)
        self._checker = QLineEdit(info.checker)
        self._organization = QLineEdit(info.organization)
        self._location = QLineEdit(info.location)
        self._date = QDateEdit()
        self._date.setCalendarPopup(True)
        self._date.setDisplayFormat(_DATE_FORMAT)
        parsed = QDate.fromString(info.project_date, _DATE_FORMAT)
        self._date.setDate(parsed if parsed.isValid() else QDate.currentDate())
        self._description = QPlainTextEdit(info.description)
        self._description.setFixedHeight(60)
        for widget in (self._name, self._number, self._designer, self._checker,
                       self._organization, self._location):
            widget.setMaxLength(200)
        info_form.addRow("Project Name *", self._name)
        info_form.addRow("Project Number", self._number)
        info_form.addRow("Designer", self._designer)
        info_form.addRow("Checker", self._checker)
        info_form.addRow("Company / Organization", self._organization)
        info_form.addRow("Location", self._location)
        info_form.addRow("Date", self._date)
        info_form.addRow("Description", self._description)

        design_box = QGroupBox("Design Settings")
        design_form = QFormLayout(design_box)
        self._standard = QComboBox()
        for standard in DesignStandard:
            self._standard.addItem(standard.label, standard.value)
        self._standard.setCurrentIndex(max(0, self._standard.findData(settings.design_standard)))
        self._units = QComboBox()
        for unit in UnitSystem:
            self._units.addItem(unit.label, unit.value)
        self._units.setCurrentIndex(max(0, self._units.findData(settings.unit_system)))

        library = library or MaterialLibrary(None)
        if concrete_names is None:
            concrete_names = [c.name for c in library.concretes]
        if grade_names is None:
            grade_names = [g.name for g in library.rebar_grades]
        self._concrete = QComboBox()
        self._concrete.addItems(concrete_names)
        self._concrete.setCurrentText(settings.default_concrete)
        self._main_rebar = QComboBox()
        self._main_rebar.addItems(grade_names)
        self._main_rebar.setCurrentText(settings.default_main_rebar)
        self._tie_rebar = QComboBox()
        self._tie_rebar.addItems(grade_names)
        self._tie_rebar.setCurrentText(settings.default_tie_rebar)
        design_form.addRow("Design Standard", self._standard)
        design_form.addRow("Unit System", self._units)
        design_form.addRow("Default Concrete", self._concrete)
        design_form.addRow("Default Main Bars", self._main_rebar)
        design_form.addRow("Default Ties / Stirrups", self._tie_rebar)

        self._error_label = QLabel()
        self._error_label.setStyleSheet(f"color: {ERROR};")
        self._error_label.setWordWrap(True)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        ok_button = buttons.button(QDialogButtonBox.StandardButton.Ok)
        ok_button.setText("Save" if edit_mode else "Create")
        ok_button.setObjectName("PrimaryButton")
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addWidget(header)
        layout.addWidget(info_box)
        layout.addWidget(design_box)
        layout.addWidget(self._error_label)
        layout.addWidget(buttons)
        self._name.setFocus()

    # ---------------------------------------------------------------- results
    def information(self) -> ProjectInformation:
        """Project information entered by the user."""
        return ProjectInformation(
            project_name=self._name.text().strip(),
            project_number=self._number.text().strip(),
            designer=self._designer.text().strip(),
            checker=self._checker.text().strip(),
            organization=self._organization.text().strip(),
            project_date=self._date.date().toString(_DATE_FORMAT),
            location=self._location.text().strip(),
            description=self._description.toPlainText().strip(),
        )

    def design_settings(self) -> DesignSettings:
        """Design settings entered by the user."""
        return DesignSettings(
            design_standard=str(self._standard.currentData()),
            unit_system=str(self._units.currentData()),
            default_concrete=self._concrete.currentText(),
            default_main_rebar=self._main_rebar.currentText(),
            default_tie_rebar=self._tie_rebar.currentText(),
        )

    # ------------------------------------------------------------- validation
    def validate(self) -> ValidationResult:
        """Validate the entered data."""
        result = ValidationResult()
        validate_required_text(self._name.text(), "Project Name", result)
        if len(self._description.toPlainText()) > 2000:
            result.add_error("Description must not exceed 2000 characters.")
        return result

    def _on_accept(self) -> None:
        result = self.validate()
        if not result.is_valid:
            self._error_label.setText("\n".join(result.errors))
            QMessageBox.warning(self, "Invalid Input", "\n".join(result.errors))
            self._name.setFocus()
            return
        if (self._edit_mode and self._original_units
                and self._original_units != self._units.currentData()):
            answer = QMessageBox.question(
                self, "Change Unit System",
                "Changing the unit system does NOT convert values that were already "
                "entered for members.\n\nContinue?",
            )
            if answer != QMessageBox.StandardButton.Yes:
                return
        self.accept()
