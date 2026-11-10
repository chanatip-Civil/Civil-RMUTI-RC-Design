"""Material Database manager (Phase 2).

Each material kind has a tab with two tables:

* **Material Library** - built-in (read-only) + user items, shared by all
  projects and saved in the user data folder;
* **Project Materials** - the copies stored in the open project file.

All rules (validation, protection of built-ins, usage checks, rename
propagation) live in the Qt-free classes :class:`MaterialLibrary` and
:class:`ProjectMaterials`; this module only presents them.
"""

from __future__ import annotations

from pathlib import Path
from typing import Callable

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from app.core.exceptions import MaterialError, ProjectFileError
from app.core.project_manager import ProjectManager
from app.gui.dialogs.material_edit_dialog import MaterialEditDialog
from app.gui.styles import TEXT_MUTED
from app.materials.database import MaterialLibrary
from app.materials.project_materials import (
    ROLE_CONCRETE,
    ROLE_MAIN_REBAR,
    ROLE_TIE_REBAR,
    ProjectMaterials,
)
from app.materials.schema import SCHEMAS, MaterialItem, MaterialKind
from app.utils.file_manager import ensure_extension

_ROLE = Qt.ItemDataRole.UserRole

TAB_CONCRETE: int = 0
TAB_REBAR_GRADES: int = 1
TAB_REBAR_SIZES: int = 2
_TAB_KINDS: tuple[MaterialKind, ...] = (
    MaterialKind.CONCRETE, MaterialKind.REBAR_GRADE, MaterialKind.REBAR_SIZE,
)


def _make_table(headers: list[str]) -> QTableWidget:
    table = QTableWidget(0, len(headers))
    table.setHorizontalHeaderLabels(headers)
    table.verticalHeader().setVisible(False)
    table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
    table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
    table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
    table.setAlternatingRowColors(True)
    header = table.horizontalHeader()
    header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
    header.setStretchLastSection(True)
    return table


def _fill_table(table: QTableWidget, rows: list[tuple[str, list[str], bool]]) -> None:
    """Fill *table*; each row is ``(name, cells, muted)``."""
    selected = {table.item(i.row(), 0).data(_ROLE) for i in table.selectedIndexes()
                if table.item(i.row(), 0) is not None}
    table.setRowCount(len(rows))
    muted = QColor(TEXT_MUTED)
    for row_index, (name, cells, is_muted) in enumerate(rows):
        for column, text in enumerate(cells):
            item = QTableWidgetItem(text)
            if column == 0:
                item.setData(_ROLE, name)
            if is_muted:
                item.setForeground(muted)
            table.setItem(row_index, column, item)
    table.clearSelection()
    for row_index, (name, _cells, _muted) in enumerate(rows):
        if name in selected:
            table.selectRow(row_index)


def _selected_names(table: QTableWidget) -> list[str]:
    names: list[str] = []
    for index in table.selectionModel().selectedRows():
        item = table.item(index.row(), 0)
        if item is not None and item.data(_ROLE) not in names:
            names.append(str(item.data(_ROLE)))
    return names


class MaterialKindPanel(QWidget):
    """Library table + project table for one material kind."""

    def __init__(self, kind: MaterialKind, library: MaterialLibrary,
                 project_manager: ProjectManager | None,
                 on_library_changed: Callable[[], None],
                 on_project_changed: Callable[[], None],
                 parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.kind = kind
        self._schema = SCHEMAS[kind]
        self._library = library
        self._pm = project_manager
        self._on_library_changed = on_library_changed
        self._on_project_changed = on_project_changed

        headers = [c.header for c in self._schema.columns]

        # ---- library side
        self._library_table = _make_table(headers + ["Source"])
        self._library_table.doubleClicked.connect(lambda *_: self._library_edit())
        self._lib_new = QPushButton("New...")
        self._lib_new.clicked.connect(self._library_new)
        self._lib_edit = QPushButton("Edit...")
        self._lib_edit.clicked.connect(self._library_edit)
        self._lib_duplicate = QPushButton("Duplicate")
        self._lib_duplicate.clicked.connect(self._library_duplicate)
        self._lib_delete = QPushButton("Delete")
        self._lib_delete.clicked.connect(self._library_delete)
        self._to_project = QPushButton("Add to Project  →")
        self._to_project.setObjectName("PrimaryButton")
        self._to_project.setToolTip("Copy the selected library items into the open project")
        self._to_project.clicked.connect(self._add_to_project)
        library_buttons = QHBoxLayout()
        for button in (self._lib_new, self._lib_edit, self._lib_duplicate, self._lib_delete):
            library_buttons.addWidget(button)
        library_buttons.addStretch()
        library_buttons.addWidget(self._to_project)
        library_box = QGroupBox("Material Library (all projects)")
        library_layout = QVBoxLayout(library_box)
        library_layout.addWidget(self._library_table)
        library_layout.addLayout(library_buttons)

        # ---- project side
        self._project_table = _make_table(headers + ["Used by"])
        self._project_table.doubleClicked.connect(lambda *_: self._project_edit())
        self._prj_new = QPushButton("New...")
        self._prj_new.clicked.connect(self._project_new)
        self._prj_edit = QPushButton("Edit...")
        self._prj_edit.clicked.connect(self._project_edit)
        self._prj_remove = QPushButton("Remove")
        self._prj_remove.clicked.connect(self._project_remove)
        self._to_library = QPushButton("Save to Library")
        self._to_library.clicked.connect(self._save_to_library)
        project_buttons = QHBoxLayout()
        for button in (self._prj_new, self._prj_edit, self._prj_remove, self._to_library):
            project_buttons.addWidget(button)
        project_buttons.addStretch()
        self._default_buttons: list[QPushButton] = []
        roles: list[tuple[str, str]] = []
        if kind == MaterialKind.CONCRETE:
            roles = [("Set as Default", ROLE_CONCRETE)]
        elif kind == MaterialKind.REBAR_GRADE:
            roles = [("Default Main Bars", ROLE_MAIN_REBAR), ("Default Ties", ROLE_TIE_REBAR)]
        for text, role in roles:
            button = QPushButton(text)
            button.clicked.connect(lambda _=False, r=role: self._set_default(r))
            project_buttons.addWidget(button)
            self._default_buttons.append(button)
        self._project_note = QLabel()
        self._project_note.setWordWrap(True)
        self._project_note.setObjectName("PageSubtitle")
        project_box = QGroupBox("Project Materials (saved in the .rcproj file)")
        project_layout = QVBoxLayout(project_box)
        project_layout.addWidget(self._project_table)
        project_layout.addLayout(project_buttons)
        project_layout.addWidget(self._project_note)

        splitter = QSplitter(Qt.Orientation.Vertical)
        splitter.addWidget(library_box)
        splitter.addWidget(project_box)
        splitter.setChildrenCollapsible(False)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.addWidget(splitter)

        self._library_table.itemSelectionChanged.connect(self._update_buttons)
        self._project_table.itemSelectionChanged.connect(self._update_buttons)
        self.refresh()

    # ------------------------------------------------------------- helpers
    @property
    def _materials(self) -> ProjectMaterials | None:
        if self._pm is None or self._pm.project is None:
            return None
        return ProjectMaterials(self._pm.project)

    def _error(self, title: str, message: str) -> None:
        QMessageBox.warning(self, title, message)

    def _save_library(self) -> bool:
        try:
            self._library.save()
        except ProjectFileError as exc:
            QMessageBox.critical(self, "Material Library", f"The library could not be saved.\n\n{exc}")
            return False
        self._on_library_changed()
        return True

    def _project_changed(self) -> None:
        if self._pm is not None:
            self._pm.mark_modified()
        self._on_project_changed()

    def _defaults_label(self, name: str) -> str:
        if self._pm is None or self._pm.project is None:
            return ""
        settings = self._pm.project.settings
        tags = []
        if self.kind == MaterialKind.CONCRETE and settings.default_concrete == name:
            tags.append("default")
        if self.kind == MaterialKind.REBAR_GRADE:
            if settings.default_main_rebar == name:
                tags.append("default main")
            if settings.default_tie_rebar == name:
                tags.append("default ties")
        return ", ".join(tags)

    # ------------------------------------------------------------- refresh
    def refresh(self) -> None:
        """Reload both tables."""
        library_rows = []
        for item in self._library.items(self.kind):
            builtin = self._library.is_builtin(self.kind, item.name)
            library_rows.append((item.name, self._schema.row(item) + [
                "Built-in" if builtin else "User"], builtin))
        _fill_table(self._library_table, library_rows)

        materials = self._materials
        project_rows = []
        if materials is not None:
            for item in materials.items(self.kind):
                usage = materials.usage(self.kind, item.name)
                parts = []
                if usage.members:
                    parts.append(f"{len(usage.members)} member(s)")
                defaults = self._defaults_label(item.name)
                if defaults:
                    parts.append(defaults)
                project_rows.append((item.name, self._schema.row(item) + [", ".join(parts) or "—"],
                                     False))
            self._project_note.setText(
                "Editing a project material updates all members that use it and clears "
                "their old results. Used materials cannot be removed.")
        else:
            self._project_note.setText("No project is open — only the library can be edited.")
        _fill_table(self._project_table, project_rows)
        self._update_buttons()

    def _update_buttons(self) -> None:
        library_selection = _selected_names(self._library_table)
        single_lib = len(library_selection) == 1
        user_selected = single_lib and not self._library.is_builtin(self.kind, library_selection[0])
        self._lib_edit.setEnabled(user_selected)
        self._lib_delete.setEnabled(user_selected)
        self._lib_duplicate.setEnabled(single_lib)
        has_project = self._materials is not None
        self._to_project.setEnabled(has_project and bool(library_selection))

        project_selection = _selected_names(self._project_table)
        single_prj = has_project and len(project_selection) == 1
        self._prj_new.setEnabled(has_project)
        for button in (self._prj_edit, self._prj_remove, self._to_library, *self._default_buttons):
            button.setEnabled(single_prj)

    # ------------------------------------------------------------- library
    def _library_name_check(self, old_name: str | None) -> Callable[[str], str | None]:
        def check(name: str) -> str | None:
            if old_name is not None and name.strip().lower() == old_name.strip().lower():
                return None
            if self._library.find(self.kind, name) is not None:
                return f"{self.kind.singular} '{name}' already exists in the library."
            return None
        return check

    def _library_new(self) -> None:
        dialog = MaterialEditDialog(self._schema, self._schema.defaults(),
                                    f"New {self.kind.singular} (Library)",
                                    self._library_name_check(None), self)
        if dialog.exec() and dialog.item() is not None:
            try:
                self._library.add(self.kind, dialog.item())
            except MaterialError as exc:
                self._error("Material Library", str(exc))
                return
            self._save_library()
            self.refresh()

    def _library_edit(self) -> None:
        names = _selected_names(self._library_table)
        if len(names) != 1:
            return
        name = names[0]
        if self._library.is_builtin(self.kind, name):
            self._error("Material Library", f"Built-in {self.kind.singular.lower()} '{name}' "
                        "is read-only. Use Duplicate to create an editable copy.")
            return
        item = self._library.find(self.kind, name)
        if item is None:
            return
        dialog = MaterialEditDialog(self._schema, self._schema.to_values(item),
                                    f"Edit {self.kind.singular} '{name}' (Library)",
                                    self._library_name_check(name), self)
        if dialog.exec() and dialog.item() is not None:
            try:
                self._library.update(self.kind, name, dialog.item())
            except MaterialError as exc:
                self._error("Material Library", str(exc))
                return
            self._save_library()
            self.refresh()

    def _library_duplicate(self) -> None:
        names = _selected_names(self._library_table)
        item = self._library.find(self.kind, names[0]) if len(names) == 1 else None
        if item is None:
            return
        values = self._schema.to_values(item)
        values[self._schema.id_key] = self._library.unique_name(self.kind, f"{item.name} copy")
        dialog = MaterialEditDialog(self._schema, values, f"Duplicate {self.kind.singular}",
                                    self._library_name_check(None), self)
        if dialog.exec() and dialog.item() is not None:
            try:
                self._library.add(self.kind, dialog.item())
            except MaterialError as exc:
                self._error("Material Library", str(exc))
                return
            self._save_library()
            self.refresh()

    def _library_delete(self) -> None:
        names = _selected_names(self._library_table)
        if len(names) != 1:
            return
        answer = QMessageBox.question(
            self, "Delete Library Item",
            f"Delete {self.kind.singular.lower()} '{names[0]}' from the library?\n"
            "Projects that already contain a copy are not affected.")
        if answer != QMessageBox.StandardButton.Yes:
            return
        try:
            self._library.remove(self.kind, names[0])
        except MaterialError as exc:
            self._error("Material Library", str(exc))
            return
        self._save_library()
        self.refresh()

    def _add_to_project(self) -> None:
        materials = self._materials
        names = _selected_names(self._library_table)
        if materials is None or not names:
            return
        added, skipped = materials.import_from_library(self._library, self.kind, names)
        if added:
            self._project_changed()
        self.refresh()
        message = f"{added} item(s) added to the project."
        if skipped:
            message += f"\n{skipped} item(s) skipped because the name already exists in the project."
        QMessageBox.information(self, "Add to Project", message)

    # ------------------------------------------------------------- project
    def _project_name_check(self, old_name: str | None) -> Callable[[str], str | None]:
        def check(name: str) -> str | None:
            materials = self._materials
            if materials is None:
                return "No project is open."
            if old_name is not None and name.strip().lower() == old_name.strip().lower():
                return None
            if materials.find(self.kind, name) is not None:
                return f"{self.kind.singular} '{name}' already exists in the project."
            return None
        return check

    def _project_new(self) -> None:
        materials = self._materials
        if materials is None:
            return
        dialog = MaterialEditDialog(self._schema, self._schema.defaults(),
                                    f"New {self.kind.singular} (Project)",
                                    self._project_name_check(None), self)
        if dialog.exec() and dialog.item() is not None:
            try:
                materials.add(self.kind, dialog.item())
            except MaterialError as exc:
                self._error("Project Materials", str(exc))
                return
            self._project_changed()
            self.refresh()

    def _project_edit(self) -> None:
        materials = self._materials
        names = _selected_names(self._project_table)
        if materials is None or len(names) != 1:
            return
        item = materials.find(self.kind, names[0])
        if item is None:
            return
        usage = materials.usage(self.kind, item.name)
        dialog = MaterialEditDialog(self._schema, self._schema.to_values(item),
                                    f"Edit {self.kind.singular} '{item.name}' (Project)",
                                    self._project_name_check(item.name), self)
        if not dialog.exec() or dialog.item() is None:
            return
        new_item: MaterialItem = dialog.item()
        if usage.members and new_item != item:
            answer = QMessageBox.question(
                self, "Update Project Material",
                f"'{item.name}' is used by {len(usage.members)} member(s).\n"
                "Their previous calculation results will be cleared.\n\nContinue?")
            if answer != QMessageBox.StandardButton.Yes:
                return
        try:
            cleared = materials.update(self.kind, item.name, new_item)
        except MaterialError as exc:
            self._error("Project Materials", str(exc))
            return
        self._project_changed()
        self.refresh()
        if cleared:
            QMessageBox.information(self, "Project Materials",
                                    f"Results of {cleared} member(s) were cleared. "
                                    "Please recalculate them.")

    def _project_remove(self) -> None:
        materials = self._materials
        names = _selected_names(self._project_table)
        if materials is None or len(names) != 1:
            return
        answer = QMessageBox.question(
            self, "Remove Project Material",
            f"Remove {self.kind.singular.lower()} '{names[0]}' from the project?")
        if answer != QMessageBox.StandardButton.Yes:
            return
        try:
            materials.remove(self.kind, names[0])
        except MaterialError as exc:
            self._error("Project Materials", str(exc))
            return
        self._project_changed()
        self.refresh()

    def _save_to_library(self) -> None:
        materials = self._materials
        names = _selected_names(self._project_table)
        if materials is None or len(names) != 1:
            return
        item = materials.find(self.kind, names[0])
        if item is None:
            return
        try:
            self._library.add(self.kind, item)
        except MaterialError as exc:
            self._error("Material Library", str(exc))
            return
        if self._save_library():
            self.refresh()
            QMessageBox.information(self, "Material Library",
                                    f"'{item.name}' was saved to the material library.")

    def _set_default(self, role: str) -> None:
        materials = self._materials
        names = _selected_names(self._project_table)
        if materials is None or len(names) != 1:
            return
        try:
            materials.set_default(role, names[0])
        except MaterialError as exc:
            self._error("Project Materials", str(exc))
            return
        self._project_changed()
        self.refresh()


class MaterialDatabaseDialog(QDialog):
    """Tools → Material Database / Reinforcement Database."""

    def __init__(self, library: MaterialLibrary, project_manager: ProjectManager | None = None,
                 initial_tab: int = TAB_CONCRETE, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Material Database")
        self.resize(980, 720)
        self._library = library
        self.library_changed: bool = False
        self.project_changed: bool = False

        title = QLabel("Material Database")
        title.setObjectName("PageTitle")
        project_name = (project_manager.display_name
                        if project_manager is not None and project_manager.has_project
                        else "no project open")
        subtitle = QLabel(f"Library file: {library.path or 'in memory'}    ·    Project: {project_name}")
        subtitle.setObjectName("PageSubtitle")
        subtitle.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)

        self._tabs = QTabWidget()
        self._panels: list[MaterialKindPanel] = []
        for kind in _TAB_KINDS:
            panel = MaterialKindPanel(kind, library, project_manager,
                                      self._mark_library_changed, self._mark_project_changed)
            self._panels.append(panel)
            self._tabs.addTab(panel, kind.title)
        self._tabs.setCurrentIndex(initial_tab)

        note = QLabel(
            "Built-in grades are read-only (TIS 20 / TIS 24 steel, common f'c grades). "
            "Ec / Es left blank are taken from the selected design standard in later phases. "
            "1 ksc = 0.0980665 MPa; bar area = π·d²/4."
        )
        note.setWordWrap(True)
        note.setObjectName("PageSubtitle")

        import_button = QPushButton("Import Library...")
        import_button.clicked.connect(self._import_library)
        export_button = QPushButton("Export Library...")
        export_button.clicked.connect(self._export_library)
        close_button = QPushButton("Close")
        close_button.setObjectName("PrimaryButton")
        close_button.clicked.connect(self.accept)
        buttons = QHBoxLayout()
        buttons.addWidget(import_button)
        buttons.addWidget(export_button)
        buttons.addStretch()
        buttons.addWidget(close_button)

        layout = QVBoxLayout(self)
        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addWidget(self._tabs, 1)
        layout.addWidget(note)
        layout.addLayout(buttons)

    def _mark_library_changed(self) -> None:
        self.library_changed = True

    def _mark_project_changed(self) -> None:
        self.project_changed = True

    def _refresh_all(self) -> None:
        for panel in self._panels:
            panel.refresh()

    def _import_library(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Import Material Library", "",
                                              "Material library (*.json);;All files (*)")
        if not path:
            return
        try:
            added, skipped = self._library.import_from(Path(path))
            self._library.save()
        except ProjectFileError as exc:
            QMessageBox.critical(self, "Import Library", str(exc))
            return
        self.library_changed = True
        self._refresh_all()
        QMessageBox.information(self, "Import Library",
                                f"{added} item(s) imported, {skipped} skipped (name already exists).")

    def _export_library(self) -> None:
        path, _ = QFileDialog.getSaveFileName(self, "Export Material Library",
                                              "material_library.json",
                                              "Material library (*.json)")
        if not path:
            return
        try:
            target = self._library.export_to(ensure_extension(Path(path), ".json"))
        except ProjectFileError as exc:
            QMessageBox.critical(self, "Export Library", str(exc))
            return
        QMessageBox.information(self, "Export Library", f"User materials exported to:\n{target}")
