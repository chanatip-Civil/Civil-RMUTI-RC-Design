"""Generic member editor page.

The form is generated from the design class ``FIELD_SPECS``, so the same page
serves Column, Beam, Slab, Stair and Footing. Edits are kept in the form until
*Apply* (or Calculate / switching member / saving) validates and writes them
to the project model.
"""

from __future__ import annotations

import copy
from dataclasses import replace
from typing import Any, Union

from PySide6.QtCore import Qt
from PySide6.QtGui import QKeySequence
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QFormLayout,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QSplitter,
    QStyle,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.core.constants import DesignType
from app.core.exceptions import CalculationError, InputValidationError
from app.core.logger import get_logger
from app.core.project_manager import ProjectManager
from app.core.project_model import DesignMember, Project
from app.design.base import BaseDesign
from app.design.fields import CHOICE, FieldSpec
from app.design.registry import create_design, get_design_class
from app.design.results import DesignResult, DesignStatus
from app.gui.dialogs.report_dialog import ReportDialog
from app.gui.styles import ERROR, TEXT_MUTED, WARNING, status_color
from app.gui.widgets.icons import design_pixmap
from app.gui.widgets.section_preview import SectionPreview
from app.utils.validators import parse_number

_log = get_logger("editor")
_ROLE = Qt.ItemDataRole.UserRole

FieldEditor = Union[QLineEdit, QComboBox]


class DesignEditorPage(QWidget):
    """Member list + input form + preview + results for one design type."""

    def __init__(self, design_type: DesignType, project_manager: ProjectManager,
                 parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.design_type = design_type
        self._pm = project_manager
        self._design_class: type[BaseDesign] = get_design_class(design_type)
        self._editors: dict[str, FieldEditor] = {}
        self._rows: dict[str, QWidget] = {}
        self._forms: dict[str, QFormLayout] = {}
        self._unit_labels: dict[str, QLabel] = {}
        self._loading: bool = False
        self._dirty: bool = False
        self._current_id: str | None = None

        self._build_ui()
        self.load_project()

    # =================================================================== UI
    def _build_ui(self) -> None:
        icon = QLabel()
        icon.setPixmap(design_pixmap(self.design_type, 40))
        title = QLabel(f"{self.design_type.title} Design")
        title.setObjectName("PageTitle")
        self._subtitle = QLabel(self.design_type.description)
        self._subtitle.setObjectName("PageSubtitle")
        title_box = QVBoxLayout()
        title_box.setSpacing(0)
        title_box.addWidget(title)
        title_box.addWidget(self._subtitle)
        header = QHBoxLayout()
        header.addWidget(icon)
        header.addLayout(title_box)
        header.addStretch()

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(self._build_member_panel())
        splitter.addWidget(self._build_form_panel())
        splitter.addWidget(self._build_output_panel())
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 3)
        splitter.setStretchFactor(2, 3)
        splitter.setSizes([200, 420, 420])
        splitter.setChildrenCollapsible(False)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.addLayout(header)
        layout.addWidget(splitter, 1)

    def _build_member_panel(self) -> QWidget:
        panel = QFrame()
        panel.setObjectName("Panel")
        panel.setMinimumWidth(170)
        layout = QVBoxLayout(panel)
        label = QLabel(f"{self.design_type.title}s")
        label.setStyleSheet("font-weight: bold;")
        self._member_list = QListWidget()
        self._member_list.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self._member_list.currentItemChanged.connect(self._on_current_item_changed)

        self._add_button = QPushButton("Add")
        self._add_button.setToolTip(f"Add a new {self.design_type.value}")
        self._add_button.clicked.connect(self._on_add)
        self._duplicate_button = QPushButton("Duplicate")
        self._duplicate_button.clicked.connect(self._on_duplicate)
        self._rename_button = QPushButton("Rename")
        self._rename_button.clicked.connect(self._on_rename)
        self._delete_button = QPushButton("Delete")
        self._delete_button.clicked.connect(self._on_delete)

        layout.addWidget(label)
        layout.addWidget(self._member_list, 1)
        for button in (self._add_button, self._duplicate_button,
                       self._rename_button, self._delete_button):
            layout.addWidget(button)
        return panel

    def _build_form_panel(self) -> QWidget:
        content = QWidget()
        form_layout = QVBoxLayout(content)
        form_layout.setContentsMargins(4, 4, 4, 4)

        general = QGroupBox("Member")
        general_form = QFormLayout(general)
        self._name_edit = QLineEdit()
        self._name_edit.setMaxLength(40)
        self._name_edit.textEdited.connect(self._on_form_edited)
        self._notes_edit = QPlainTextEdit()
        self._notes_edit.setFixedHeight(54)
        self._notes_edit.textChanged.connect(self._on_form_edited)
        general_form.addRow("Name / Mark *", self._name_edit)
        general_form.addRow("Notes", self._notes_edit)
        form_layout.addWidget(general)

        materials = QGroupBox("Materials")
        materials_form = QFormLayout(materials)
        self._concrete_combo = QComboBox()
        self._main_rebar_combo = QComboBox()
        self._tie_rebar_combo = QComboBox()
        for combo in (self._concrete_combo, self._main_rebar_combo, self._tie_rebar_combo):
            combo.currentIndexChanged.connect(self._on_form_edited)
        materials_form.addRow("Concrete", self._concrete_combo)
        materials_form.addRow("Main reinforcement", self._main_rebar_combo)
        materials_form.addRow("Ties / stirrups", self._tie_rebar_combo)
        form_layout.addWidget(materials)

        groups: dict[str, QFormLayout] = {}
        for spec in self._design_class.FIELD_SPECS:
            if spec.group not in groups:
                box = QGroupBox(spec.group)
                groups[spec.group] = QFormLayout(box)
                form_layout.addWidget(box)
            self._add_field_row(groups[spec.group], spec)
        form_layout.addStretch()

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll.setWidget(content)

        self._message_label = QLabel()
        self._message_label.setWordWrap(True)
        self._dirty_label = QLabel()
        self._dirty_label.setStyleSheet(f"color: {WARNING};")

        self._apply_button = QPushButton("Apply")
        self._apply_button.setToolTip("Validate and store the inputs (Ctrl+Return)")
        self._apply_button.setShortcut(QKeySequence("Ctrl+Return"))
        self._apply_button.clicked.connect(lambda: self._apply(show_success=True))
        self._validate_button = QPushButton("Validate")
        self._validate_button.clicked.connect(self._on_validate)
        self._calculate_button = QPushButton("Calculate")
        self._calculate_button.setObjectName("PrimaryButton")
        self._calculate_button.setShortcut(QKeySequence("F5"))
        self._calculate_button.setToolTip("Validate, store and calculate (F5)")
        self._calculate_button.clicked.connect(self._on_calculate)
        self._report_button = QPushButton("Report...")
        self._report_button.clicked.connect(self._on_report)
        buttons = QHBoxLayout()
        buttons.addWidget(self._apply_button)
        buttons.addWidget(self._validate_button)
        buttons.addStretch()
        buttons.addWidget(self._report_button)
        buttons.addWidget(self._calculate_button)

        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(scroll, 1)
        layout.addWidget(self._dirty_label)
        layout.addWidget(self._message_label)
        layout.addLayout(buttons)
        return panel

    def _add_field_row(self, form: QFormLayout, spec: FieldSpec) -> None:
        editor: FieldEditor
        if spec.kind == CHOICE:
            combo = QComboBox()
            combo.addItems(list(spec.choices))
            combo.currentIndexChanged.connect(self._on_form_edited)
            combo.currentIndexChanged.connect(self._update_visibility)
            editor = combo
        else:
            line = QLineEdit()
            line.setAlignment(Qt.AlignmentFlag.AlignRight)
            line.textEdited.connect(self._on_form_edited)
            editor = line
        if spec.tooltip:
            editor.setToolTip(spec.tooltip)
        unit = QLabel()
        unit.setMinimumWidth(52)
        unit.setStyleSheet(f"color: {TEXT_MUTED};")
        row = QWidget()
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.addWidget(editor, 1)
        row_layout.addWidget(unit)
        label = spec.label + (" *" if spec.required and spec.kind != CHOICE else "")
        form.addRow(label, row)
        self._editors[spec.key] = editor
        self._unit_labels[spec.key] = unit
        self._rows[spec.key] = row
        self._forms[spec.key] = form

    def _build_output_panel(self) -> QWidget:
        preview_box = QGroupBox("Geometry Preview")
        preview_layout = QVBoxLayout(preview_box)
        self._preview = SectionPreview()
        preview_layout.addWidget(self._preview)

        results_box = QGroupBox("Results")
        results_layout = QVBoxLayout(results_box)
        self._status_label = QLabel()
        self._status_label.setWordWrap(True)
        self._results_table = QTableWidget(0, 3)
        self._results_table.setHorizontalHeaderLabels(["Item", "Value", "Unit"])
        self._results_table.verticalHeader().setVisible(False)
        self._results_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        header = self._results_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self._result_messages = QLabel()
        self._result_messages.setWordWrap(True)
        self._result_messages.setStyleSheet(f"color: {TEXT_MUTED};")
        results_layout.addWidget(self._status_label)
        results_layout.addWidget(self._results_table, 1)
        results_layout.addWidget(self._result_messages)

        splitter = QSplitter(Qt.Orientation.Vertical)
        splitter.addWidget(preview_box)
        splitter.addWidget(results_box)
        splitter.setSizes([300, 300])
        splitter.setChildrenCollapsible(False)
        return splitter

    # ========================================================== project data
    @property
    def project(self) -> Project | None:
        """The open project."""
        return self._pm.project

    @property
    def has_pending_changes(self) -> bool:
        """True if the form holds edits not yet applied."""
        return self._dirty

    def load_project(self) -> None:
        """Reload combos, units and members from the current project."""
        project = self.project
        self._loading = True
        try:
            for combo in (self._concrete_combo, self._main_rebar_combo, self._tie_rebar_combo):
                combo.clear()
            if project is not None:
                self._concrete_combo.addItems([c.name for c in project.concretes])
                names = [g.name for g in project.rebar_grades]
                self._main_rebar_combo.addItems(names)
                self._tie_rebar_combo.addItems(names)
                self._subtitle.setText(
                    f"{self.design_type.description}  ·  {project.settings.standard.value}"
                    f"  ·  {project.settings.units.label}"
                )
                design = self._design_class(self._design_class.create_member(project), project)
                for spec in self._design_class.FIELD_SPECS:
                    self._unit_labels[spec.key].setText(
                        "" if spec.kind == CHOICE else design.unit_for(spec)
                    )
        finally:
            self._loading = False
        previous_id = self._current_id
        self._dirty = False
        self._current_id = None
        self._refresh_member_list(select_id=previous_id)

    def _refresh_member_list(self, select_id: str | None = None) -> None:
        project = self.project
        target = select_id or self._current_id
        self._member_list.blockSignals(True)
        self._member_list.clear()
        selected_item: QListWidgetItem | None = None
        if project is not None:
            for member in project.members_of(self.design_type):
                item = QListWidgetItem(member.name)
                item.setData(_ROLE, member.member_id)
                item.setIcon(self._member_list.style().standardIcon(
                    QStyle.StandardPixmap.SP_FileIcon))
                self._member_list.addItem(item)
                if member.member_id == target:
                    selected_item = item
        if selected_item is None and self._member_list.count() > 0:
            selected_item = self._member_list.item(0)
        if selected_item is not None:
            self._member_list.setCurrentItem(selected_item)
        self._member_list.blockSignals(False)
        member_id = selected_item.data(_ROLE) if selected_item is not None else None
        self._show_member(member_id)

    def _member(self, member_id: str | None) -> DesignMember | None:
        if self.project is None or member_id is None:
            return None
        return self.project.find_member(self.design_type, member_id)

    def current_member(self) -> DesignMember | None:
        """Member currently shown in the form."""
        return self._member(self._current_id)

    def select_member(self, member_id: str) -> None:
        """Select a member by id (used by the sidebar)."""
        if member_id == self._current_id:
            return
        if not self.commit_pending():
            return
        self._refresh_member_list(select_id=member_id)

    # ================================================================== form
    def _show_member(self, member_id: str | None) -> None:
        self._current_id = member_id
        member = self._member(member_id)
        has_member = member is not None
        for widget in (self._name_edit, self._notes_edit, self._concrete_combo,
                       self._main_rebar_combo, self._tie_rebar_combo, self._apply_button,
                       self._validate_button, self._calculate_button, self._report_button,
                       self._duplicate_button, self._rename_button, self._delete_button):
            widget.setEnabled(has_member)
        for editor in self._editors.values():
            editor.setEnabled(has_member)
        self._add_button.setEnabled(self.project is not None)

        self._loading = True
        try:
            if member is None:
                self._name_edit.clear()
                self._notes_edit.clear()
                for editor in self._editors.values():
                    if isinstance(editor, QLineEdit):
                        editor.clear()
                self._show_message(
                    f"No {self.design_type.value} yet. Click 'Add' to create one."
                    if self.project else "Open or create a project first.", TEXT_MUTED)
                self._show_result(DesignResult())
            else:
                self._name_edit.setText(member.name)
                self._notes_edit.setPlainText(member.notes)
                self._set_combo(self._concrete_combo, member.concrete)
                self._set_combo(self._main_rebar_combo, member.main_rebar)
                self._set_combo(self._tie_rebar_combo, member.tie_rebar)
                defaults = self._design_class.default_inputs()
                for spec in self._design_class.FIELD_SPECS:
                    value = member.inputs.get(spec.key, defaults.get(spec.key))
                    editor = self._editors[spec.key]
                    if isinstance(editor, QComboBox):
                        self._set_combo(editor, str(value))
                    else:
                        editor.setText(self._format_value(value))
                self._show_message("", TEXT_MUTED)
                self._show_result(DesignResult.from_dict(member.result))
        finally:
            self._loading = False
        self._set_dirty(False)
        self._update_visibility()
        self._clear_highlight()
        self._update_preview()

    @staticmethod
    def _format_value(value: Any) -> str:
        if value is None:
            return ""
        if isinstance(value, float):
            return f"{value:g}"
        return str(value)

    @staticmethod
    def _set_combo(combo: QComboBox, text: str) -> None:
        index = combo.findText(text)
        if index < 0 and text:
            combo.addItem(text)  # Keep unknown values visible; validation reports them.
            index = combo.findText(text)
        combo.setCurrentIndex(max(index, 0))

    def _collect_inputs(self) -> dict[str, Any]:
        inputs: dict[str, Any] = {}
        for spec in self._design_class.FIELD_SPECS:
            editor = self._editors[spec.key]
            if isinstance(editor, QComboBox):
                inputs[spec.key] = editor.currentText()
            else:
                text = editor.text().strip()
                number = parse_number(text)
                inputs[spec.key] = number if number is not None else text
        return inputs

    def _candidate_member(self) -> DesignMember | None:
        member = self.current_member()
        if member is None:
            return None
        return replace(
            member,
            name=self._name_edit.text().strip(),
            notes=self._notes_edit.toPlainText(),
            inputs=self._collect_inputs(),
            concrete=self._concrete_combo.currentText(),
            main_rebar=self._main_rebar_combo.currentText(),
            tie_rebar=self._tie_rebar_combo.currentText(),
        )

    def _on_form_edited(self, *_args: Any) -> None:
        if self._loading or self.current_member() is None:
            return
        self._set_dirty(True)
        self._update_preview()

    def _set_dirty(self, dirty: bool) -> None:
        self._dirty = dirty
        self._dirty_label.setText("● Unapplied changes — press Apply or Calculate." if dirty else "")

    def _update_visibility(self, *_args: Any) -> None:
        inputs = self._collect_inputs()
        for spec in self._design_class.FIELD_SPECS:
            self._forms[spec.key].setRowVisible(self._rows[spec.key], spec.is_active(inputs))

    def _update_preview(self) -> None:
        if self.current_member() is None:
            self._preview.update_preview(self.design_type, {})
            return
        self._preview.update_preview(self.design_type, self._collect_inputs())

    def _clear_highlight(self) -> None:
        for editor in self._editors.values():
            if isinstance(editor, QLineEdit):
                self._set_invalid(editor, False)

    @staticmethod
    def _set_invalid(editor: QLineEdit, invalid: bool) -> None:
        editor.setProperty("invalid", "true" if invalid else "false")
        editor.style().unpolish(editor)
        editor.style().polish(editor)

    def _highlight(self, design: BaseDesign) -> None:
        inputs = design.member.inputs
        for spec in self._design_class.FIELD_SPECS:
            editor = self._editors[spec.key]
            if isinstance(editor, QLineEdit):
                errors = design.check_field(spec, inputs.get(spec.key)) if spec.is_active(inputs) else []
                self._set_invalid(editor, bool(errors))
                editor.setToolTip("\n".join(errors) or spec.tooltip)

    def _show_message(self, text: str, color: str) -> None:
        self._message_label.setText(text)
        self._message_label.setStyleSheet(f"color: {color};")

    # ============================================================ validation
    def _validate_candidate(self) -> tuple[DesignMember | None, list[str], list[str]]:
        """Return ``(candidate, errors, warnings)`` for the current form."""
        project = self.project
        candidate = self._candidate_member()
        if project is None or candidate is None:
            return None, [], []
        design = create_design(candidate, project)
        result = design.validate()
        errors = list(result.errors)
        if candidate.name and project.is_name_taken(
                self.design_type, candidate.name, exclude_id=candidate.member_id):
            errors.append(f"{self.design_type.title} name '{candidate.name}' is already used.")
        self._highlight(design)
        return candidate, errors, list(result.warnings)

    def _apply(self, show_success: bool = False, show_dialog: bool = True) -> bool:
        """Validate the form and write it to the model. Returns success."""
        member = self.current_member()
        if member is None:
            return True
        candidate, errors, warnings = self._validate_candidate()
        if candidate is None:
            return False
        if errors:
            self._show_message("Invalid input:\n• " + "\n• ".join(errors), ERROR)
            if show_dialog:
                QMessageBox.warning(self, "Invalid Input", "\n".join(errors))
            return False

        inputs_changed = (
            candidate.inputs != member.inputs or candidate.concrete != member.concrete
            or candidate.main_rebar != member.main_rebar or candidate.tie_rebar != member.tie_rebar
        )
        if self._dirty:
            member.name = candidate.name
            member.notes = candidate.notes
            member.inputs = copy.deepcopy(candidate.inputs)
            member.concrete = candidate.concrete
            member.main_rebar = candidate.main_rebar
            member.tie_rebar = candidate.tie_rebar
            if inputs_changed:
                member.result = None  # Old results no longer match the inputs.
                self._show_result(DesignResult())
            member.touch()
            self._set_dirty(False)
            item = self._member_list.currentItem()
            if item is not None:
                item.setText(member.name)
            self._pm.mark_modified()
        if warnings:
            self._show_message("Applied with warnings:\n• " + "\n• ".join(warnings), WARNING)
        elif show_success:
            self._show_message("Inputs are valid and have been applied.", status_color("pass"))
        return True

    def commit_pending(self) -> bool:
        """Apply pending edits before navigation/saving.

        Returns:
            True if it is safe to continue (applied or discarded), False to cancel.
        """
        if not self._dirty or self.current_member() is None:
            return True
        if self._apply(show_dialog=False):
            return True
        answer = QMessageBox.question(
            self, "Invalid Input",
            f"The {self.design_type.value} form contains invalid input:\n\n"
            f"{self._message_label.text()}\n\nDiscard these changes?",
            QMessageBox.StandardButton.Discard | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Cancel,
        )
        if answer == QMessageBox.StandardButton.Discard:
            self._show_member(self._current_id)
            return True
        return False

    # =============================================================== actions
    def _on_current_item_changed(self, current: QListWidgetItem | None,
                                 previous: QListWidgetItem | None) -> None:
        new_id = current.data(_ROLE) if current is not None else None
        if new_id == self._current_id:
            return
        if not self.commit_pending():
            self._member_list.blockSignals(True)
            self._member_list.setCurrentItem(previous)
            self._member_list.blockSignals(False)
            return
        self._show_member(new_id)

    def _on_add(self) -> None:
        project = self.project
        if project is None or not self.commit_pending():
            return
        member = project.add_member(self._design_class.create_member(project))
        self._pm.mark_modified()
        self._refresh_member_list(select_id=member.member_id)
        self._name_edit.setFocus()
        self._name_edit.selectAll()

    def _on_duplicate(self) -> None:
        project = self.project
        member = self.current_member()
        if project is None or member is None or not self.commit_pending():
            return
        data = copy.deepcopy(member.to_dict())
        data.update(member_id="", created_at="", modified_at="",
                    name=project.next_member_name(self.design_type))
        clone = DesignMember.from_dict(self.design_type, data)  # new id and timestamps
        project.add_member(clone)
        self._pm.mark_modified()
        self._refresh_member_list(select_id=clone.member_id)

    def _on_rename(self) -> None:
        project = self.project
        member = self.current_member()
        if project is None or member is None or not self.commit_pending():
            return
        name, ok = QInputDialog.getText(self, f"Rename {self.design_type.title}",
                                        "New name / mark:", text=member.name)
        if not ok:
            return
        name = name.strip()
        if not name:
            QMessageBox.warning(self, "Invalid Input",
                                f"{self.design_type.title} name is required.")
            return
        if project.is_name_taken(self.design_type, name, exclude_id=member.member_id):
            QMessageBox.warning(self, "Invalid Input",
                                f"{self.design_type.title} name '{name}' is already used.")
            return
        member.name = name
        member.touch()
        self._pm.mark_modified()
        self._refresh_member_list(select_id=member.member_id)

    def _on_delete(self) -> None:
        project = self.project
        member = self.current_member()
        if project is None or member is None:
            return
        answer = QMessageBox.question(
            self, f"Delete {self.design_type.title}",
            f"Delete {self.design_type.value} '{member.name}'?\nThis cannot be undone.",
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        project.remove_member(self.design_type, member.member_id)
        self._current_id = None
        self._dirty = False
        self._pm.mark_modified()
        self._refresh_member_list()

    def _on_validate(self) -> None:
        candidate, errors, warnings = self._validate_candidate()
        if candidate is None:
            return
        if errors:
            self._show_message("Invalid input:\n• " + "\n• ".join(errors), ERROR)
        elif warnings:
            self._show_message("Valid with warnings:\n• " + "\n• ".join(warnings), WARNING)
        else:
            self._show_message("All inputs are valid.", status_color("pass"))

    def _on_calculate(self) -> None:
        member = self.current_member()
        project = self.project
        if member is None or project is None or not self._apply():
            return
        design = create_design(member, project)
        try:
            result = design.calculate()
        except InputValidationError as exc:
            QMessageBox.warning(self, "Invalid Input", "\n".join(exc.messages))
            return
        except CalculationError as exc:
            QMessageBox.critical(self, "Calculation Error", str(exc))
            return
        self._show_result(result)
        self._pm.mark_modified()

    def _on_report(self) -> None:
        member = self.current_member()
        project = self.project
        if member is None or project is None or not self._apply():
            return
        report = create_design(member, project).generate_report()
        dialog = ReportDialog(f"{self.design_type.title} {member.name} — Calculation Report",
                              report, f"{self.design_type.value}_{member.name}", self)
        dialog.exec()

    # =============================================================== results
    def _show_result(self, result: DesignResult) -> None:
        color = status_color(result.status.value)
        text = f"Status: {result.status.label}"
        if result.status != DesignStatus.NOT_CALCULATED and result.calculated_at:
            text += f"   ({result.calculated_at})"
        self._status_label.setText(text)
        self._status_label.setStyleSheet(f"color: {color}; font-weight: bold;")
        self._results_table.setRowCount(len(result.items))
        for row, item in enumerate(result.items):
            label_item = QTableWidgetItem(item.label)
            if item.note:
                label_item.setToolTip(item.note)
            value_item = QTableWidgetItem(item.formatted_value())
            value_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self._results_table.setItem(row, 0, label_item)
            self._results_table.setItem(row, 1, value_item)
            self._results_table.setItem(row, 2, QTableWidgetItem(item.unit))
        self._result_messages.setText("\n".join(f"• {m}" for m in result.messages))
