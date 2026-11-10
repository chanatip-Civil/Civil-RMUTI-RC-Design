"""Main application window of Civil RMUTI Rc Design."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QByteArray, Qt
from PySide6.QtGui import QAction, QCloseEvent, QKeySequence
from PySide6.QtWidgets import (
    QLabel,
    QMainWindow,
    QMenu,
    QMessageBox,
    QSplitter,
    QStackedWidget,
    QStyle,
    QToolBar,
    QWidget,
)

from app.core.constants import APP_NAME, APP_VERSION, DesignType
from app.core.exceptions import ProjectFileError, ProjectStateError
from app.core.logger import get_logger
from app.core.project_manager import ProjectEvent, ProjectManager
from app.core.settings import SettingsManager
from app.gui.design_selection import DesignSelectionPage
from app.gui.dialogs.about_dialog import AboutDialog
from app.gui.dialogs.material_database_dialog import (
    TAB_CONCRETE,
    TAB_REBAR_GRADES,
    MaterialDatabaseDialog,
)
from app.gui.dialogs.settings_dialog import SettingsDialog
from app.gui.dialogs.user_manual_dialog import UserManualDialog
from app.gui.new_project_dialog import NewProjectDialog
from app.gui.open_project_dialog import ProjectFileDialog
from app.gui.pages.design_editor_page import DesignEditorPage
from app.gui.pages.project_overview_page import ProjectOverviewPage
from app.gui.pages.welcome_page import WelcomePage
from app.gui.widgets.icons import app_icon, design_icon
from app.gui.widgets.sidebar import PAGE_OVERVIEW, PAGE_SELECTION, ProjectSidebar
from app.materials.database import MaterialLibrary

_log = get_logger("main_window")

PAGE_WELCOME: str = "welcome"


class MainWindow(QMainWindow):
    """Menu bar, toolbar, sidebar, workspace stack and status bar."""

    def __init__(self, settings_manager: SettingsManager,
                 project_manager: ProjectManager | None = None) -> None:
        super().__init__()
        self._settings = settings_manager
        self._pm = project_manager or ProjectManager()
        self._material_db = MaterialLibrary.default()
        self._current_page: str = PAGE_WELCOME

        self.setWindowIcon(app_icon())
        self.setMinimumSize(960, 640)
        self.resize(1360, 860)

        self._create_actions()
        self._create_menus()
        self._create_toolbar()
        self._create_workspace()
        self._create_status_bar()

        self._pm.add_listener(self._on_project_event)
        self._restore_geometry()
        self._refresh_all()
        self._show_page(PAGE_WELCOME, check_pending=False)

    @property
    def project_manager(self) -> ProjectManager:
        """The project manager used by this window."""
        return self._pm

    # ============================================================== actions
    def _action(self, text: str, slot, shortcut: QKeySequence | str | None = None,
                icon: QStyle.StandardPixmap | None = None, tip: str = "") -> QAction:
        action = QAction(text, self)
        if icon is not None:
            action.setIcon(self.style().standardIcon(icon))
        if shortcut is not None:
            action.setShortcut(QKeySequence(shortcut))
        if tip:
            action.setStatusTip(tip)
            action.setToolTip(tip)
        action.triggered.connect(slot)
        return action

    def _create_actions(self) -> None:
        sp = QStyle.StandardPixmap
        keys = QKeySequence.StandardKey
        self.act_new = self._action("&New Project...", self.new_project, keys.New,
                                    sp.SP_FileIcon, "Create a new project")
        self.act_open = self._action("&Open Project...", lambda: self.open_project(), keys.Open,
                                     sp.SP_DialogOpenButton, "Open a .rcproj project file")
        self.act_save = self._action("&Save Project", self.save_project, keys.Save,
                                     sp.SP_DialogSaveButton, "Save the project")
        self.act_save_as = self._action("Save Project &As...", self.save_project_as,
                                        keys.SaveAs, None, "Save the project under a new name")
        self.act_properties = self._action("Project &Properties...", self.edit_project_properties,
                                           None, sp.SP_FileDialogInfoView,
                                           "Edit project information and design settings")
        self.act_close = self._action("&Close Project", self.close_project, keys.Close,
                                      sp.SP_DialogCloseButton, "Close the current project")
        self.act_exit = self._action("E&xit", self.close, keys.Quit, None, "Exit the program")

        self.design_actions: dict[DesignType, QAction] = {}
        for index, design_type in enumerate(DesignType, start=1):
            action = QAction(design_icon(design_type), design_type.title, self)
            action.setShortcut(QKeySequence(f"Ctrl+{index}"))
            action.setStatusTip(design_type.description)
            action.setToolTip(design_type.description)
            action.triggered.connect(lambda _=False, dt=design_type: self.open_design(dt))
            self.design_actions[design_type] = action
        self.act_selection = self._action("Design &Selection", lambda: self._show_page(PAGE_SELECTION),
                                          "Ctrl+0", sp.SP_FileDialogContentsView,
                                          "Show the design type selection page")

        self.act_settings = self._action("&Settings...", self.show_settings, None,
                                         sp.SP_FileDialogDetailedView, "Application settings")
        self.act_material_db = self._action("&Material Database...",
                                            lambda: self.show_material_database(TAB_CONCRETE),
                                            None, None, "Concrete grades")
        self.act_rebar_db = self._action("&Reinforcement Database...",
                                         lambda: self.show_material_database(TAB_REBAR_GRADES),
                                         None, None, "Reinforcing steel grades and bar sizes")
        self.act_manual = self._action("&User Manual", self.show_manual, keys.HelpContents,
                                       sp.SP_DialogHelpButton, "Open the user manual")
        self.act_about = self._action(f"&About {APP_NAME}", self.show_about, None,
                                      sp.SP_MessageBoxInformation, "Program information")

    def _create_menus(self) -> None:
        bar = self.menuBar()
        file_menu = bar.addMenu("&File")
        file_menu.addActions([self.act_new, self.act_open])
        self._recent_menu = QMenu("Open &Recent", self)
        file_menu.addMenu(self._recent_menu)
        file_menu.addSeparator()
        file_menu.addActions([self.act_save, self.act_save_as])
        file_menu.addSeparator()
        file_menu.addActions([self.act_properties, self.act_close])
        file_menu.addSeparator()
        file_menu.addAction(self.act_exit)

        design_menu = bar.addMenu("&Design")
        design_menu.addAction(self.act_selection)
        design_menu.addSeparator()
        design_menu.addActions(list(self.design_actions.values()))

        tools_menu = bar.addMenu("&Tools")
        tools_menu.addAction(self.act_settings)
        tools_menu.addSeparator()
        tools_menu.addActions([self.act_material_db, self.act_rebar_db])

        help_menu = bar.addMenu("&Help")
        help_menu.addAction(self.act_manual)
        help_menu.addSeparator()
        help_menu.addAction(self.act_about)

    def _create_toolbar(self) -> None:
        toolbar = QToolBar("Main Toolbar", self)
        toolbar.setObjectName("MainToolbar")
        toolbar.setMovable(False)
        toolbar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        toolbar.addActions([self.act_new, self.act_open, self.act_save])
        toolbar.addSeparator()
        toolbar.addAction(self.act_selection)
        toolbar.addActions(list(self.design_actions.values()))
        toolbar.addSeparator()
        toolbar.addAction(self.act_manual)
        self.addToolBar(Qt.ToolBarArea.TopToolBarArea, toolbar)

    # ============================================================ workspace
    def _create_workspace(self) -> None:
        self._sidebar = ProjectSidebar()
        self._sidebar.page_requested.connect(self._on_sidebar_page)
        self._sidebar.member_requested.connect(self._on_sidebar_member)

        self._stack = QStackedWidget()
        self._pages: dict[str, QWidget] = {}

        welcome = WelcomePage()
        welcome.new_requested.connect(self.new_project)
        welcome.open_requested.connect(lambda: self.open_project())
        welcome.recent_requested.connect(lambda path: self.open_project(Path(path)))
        self._welcome = welcome

        overview = ProjectOverviewPage()
        overview.edit_requested.connect(self.edit_project_properties)
        overview.design_selection_requested.connect(lambda: self._show_page(PAGE_SELECTION))
        self._overview = overview

        selection = DesignSelectionPage()
        selection.design_selected.connect(self.open_design)
        self._selection = selection

        self._editors: dict[DesignType, DesignEditorPage] = {
            design_type: DesignEditorPage(design_type, self._pm) for design_type in DesignType
        }

        self._add_page(PAGE_WELCOME, welcome)
        self._add_page(PAGE_OVERVIEW, overview)
        self._add_page(PAGE_SELECTION, selection)
        for design_type, editor in self._editors.items():
            self._add_page(design_type.value, editor)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(self._sidebar)
        splitter.addWidget(self._stack)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([250, 1100])
        splitter.setChildrenCollapsible(False)
        self.setCentralWidget(splitter)

    def _add_page(self, key: str, widget: QWidget) -> None:
        self._pages[key] = widget
        self._stack.addWidget(widget)

    def _create_status_bar(self) -> None:
        status = self.statusBar()
        self._project_status = QLabel()
        self._standard_status = QLabel()
        self._unit_status = QLabel()
        for label in (self._project_status, self._standard_status, self._unit_status):
            status.addPermanentWidget(label)
        status.showMessage("Ready")

    # ============================================================ navigation
    def _current_editor(self) -> DesignEditorPage | None:
        try:
            return self._editors.get(DesignType(self._current_page))
        except ValueError:
            return None

    def _commit_editor(self) -> bool:
        """Apply pending edits in the visible editor. False = user cancelled."""
        editor = self._current_editor()
        return editor.commit_pending() if editor is not None else True

    def _show_page(self, key: str, check_pending: bool = True) -> bool:
        """Switch the workspace page; returns False if navigation was cancelled."""
        if key != PAGE_WELCOME and not self._pm.has_project:
            key = PAGE_WELCOME
        if key == self._current_page and self._stack.currentWidget() is self._pages[key]:
            return True
        if check_pending and not self._commit_editor():
            return False
        self._current_page = key
        self._stack.setCurrentWidget(self._pages[key])
        return True

    def open_design(self, design_type: DesignType) -> None:
        """Show the editor of *design_type*."""
        if not self._pm.has_project:
            QMessageBox.information(self, APP_NAME, "Please create or open a project first.")
            return
        if self._show_page(design_type.value):
            self.statusBar().showMessage(design_type.description, 3000)

    def _on_sidebar_page(self, key: str) -> None:
        self._show_page(key)

    def _on_sidebar_member(self, design_type: DesignType, member_id: str) -> None:
        if self._show_page(design_type.value):
            self._editors[design_type].select_member(member_id)

    # ======================================================= project events
    def _on_project_event(self, event: ProjectEvent) -> None:
        if event == ProjectEvent.OPENED:
            for editor in self._editors.values():
                editor.load_project()
            self._refresh_all()
            self._show_page(PAGE_SELECTION, check_pending=False)
        elif event == ProjectEvent.CLOSED:
            for editor in self._editors.values():
                editor.load_project()
            self._refresh_all()
            self._show_page(PAGE_WELCOME, check_pending=False)
        else:
            self._refresh_all()

    def _refresh_all(self) -> None:
        project = self._pm.project
        has_project = project is not None
        for action in (self.act_save, self.act_save_as, self.act_close,
                       self.act_properties, self.act_selection, *self.design_actions.values()):
            action.setEnabled(has_project)

        self._sidebar.refresh(project)
        self._selection.update_counts(project)
        self._overview.update_project(project, self._pm.file_path)
        self._welcome.set_recent_projects(self._settings.settings.recent_projects)
        self._rebuild_recent_menu()

        if project is None:
            self.setWindowTitle(APP_NAME)
            self.setWindowModified(False)
            self._project_status.setText("No project")
            self._standard_status.setText("")
            self._unit_status.setText("")
        else:
            self.setWindowTitle(f"{self._pm.display_name}[*] — {APP_NAME}")
            self.setWindowModified(self._pm.is_modified)
            file_text = self._pm.file_path.name if self._pm.file_path else "not saved"
            self._project_status.setText(
                f"Project: {self._pm.display_name} ({file_text})"
                + ("  ● modified" if self._pm.is_modified else "")
            )
            self._standard_status.setText(f"Standard: {project.settings.standard.value}")
            self._unit_status.setText(f"Units: {project.settings.units.value}")

    def _rebuild_recent_menu(self) -> None:
        self._recent_menu.clear()
        recent = self._settings.settings.recent_projects
        if not recent:
            empty = self._recent_menu.addAction("(empty)")
            empty.setEnabled(False)
            return
        for index, path in enumerate(recent, start=1):
            action = self._recent_menu.addAction(f"&{index}  {path}")
            action.triggered.connect(lambda _=False, p=path: self.open_project(Path(p)))
        self._recent_menu.addSeparator()
        clear = self._recent_menu.addAction("Clear Recent Projects")
        clear.triggered.connect(self._clear_recent)

    def _clear_recent(self) -> None:
        self._settings.clear_recent_projects()
        self._refresh_all()

    # ======================================================== file commands
    def _maybe_save_changes(self) -> bool:
        """Ask to save unsaved changes. Returns True if the caller may continue."""
        if not self._commit_editor():
            return False
        if not self._pm.has_project or not self._pm.is_modified:
            return True
        answer = QMessageBox.question(
            self, APP_NAME,
            f"The project '{self._pm.display_name}' has unsaved changes.\n"
            "Do you want to save them?",
            QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Discard
            | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Save,
        )
        if answer == QMessageBox.StandardButton.Save:
            return self.save_project()
        return answer == QMessageBox.StandardButton.Discard

    def new_project(self) -> None:
        """File → New Project."""
        if not self._maybe_save_changes():
            return
        library = self._material_db
        dialog = NewProjectDialog(self._settings.settings, self, library=library)
        if not dialog.exec():
            return
        # Each project gets its own copy of the library so the file is self-contained.
        self._pm.new_project(dialog.information(), dialog.design_settings(), materials={
            "concretes": library.concretes,
            "rebar_grades": library.rebar_grades,
            "rebar_sizes": library.rebar_sizes,
        })
        self.statusBar().showMessage("New project created — select a design type.", 5000)

    def open_project(self, path: Path | None = None) -> bool:
        """File → Open Project (or open *path* directly)."""
        if not self._maybe_save_changes():
            return False
        if path is None:
            path = ProjectFileDialog.get_open_path(self, self._settings.settings.last_directory)
            if path is None:
                return False
        try:
            self._pm.open_project(path)
        except ProjectFileError as exc:
            _log.warning("Open failed: %s", exc)
            if str(Path(path)) in self._settings.settings.recent_projects and not Path(path).exists():
                self._settings.remove_recent_project(path)
                self._refresh_all()
            QMessageBox.critical(self, "Open Project", f"The project could not be opened.\n\n{exc}")
            return False
        self._settings.add_recent_project(self._pm.file_path or path)
        self._refresh_all()
        self.statusBar().showMessage(f"Opened {path}", 5000)
        return True

    def save_project(self) -> bool:
        """File → Save Project. Returns True on success."""
        if not self._pm.has_project or not self._commit_editor():
            return False
        if self._pm.file_path is None:
            return self.save_project_as()
        return self._write_project(None)

    def save_project_as(self) -> bool:
        """File → Save Project As. Returns True on success."""
        if not self._pm.has_project or not self._commit_editor():
            return False
        start = (self._pm.file_path.parent if self._pm.file_path
                 else self._settings.settings.last_directory)
        path = ProjectFileDialog.get_save_path(self, start, self._pm.display_name)
        if path is None:
            return False
        return self._write_project(path)

    def _write_project(self, path: Path | None) -> bool:
        try:
            saved = self._pm.save_project(path)
        except (ProjectFileError, ProjectStateError) as exc:
            _log.error("Save failed: %s", exc)
            QMessageBox.critical(
                self, "Save Project",
                f"The project could not be saved.\n\n{exc}\n\n"
                "Your data is still open in the program; try another folder or file name.",
            )
            return False
        self._settings.add_recent_project(saved)
        self._refresh_all()
        self.statusBar().showMessage(f"Saved {saved}", 5000)
        return True

    def close_project(self) -> None:
        """File → Close Project."""
        if self._maybe_save_changes():
            self._pm.close_project()
            self.statusBar().showMessage("Project closed", 3000)

    def edit_project_properties(self) -> None:
        """Edit project information / design settings of the open project."""
        project = self._pm.project
        if project is None:
            return
        dialog = NewProjectDialog(
            self._settings.settings, self, project.information, project.settings,
            edit_mode=True,
            concrete_names=[c.name for c in project.concretes],
            grade_names=[g.name for g in project.rebar_grades],
        )
        if not dialog.exec():
            return
        if not self._commit_editor():
            return
        project.information = dialog.information()
        project.settings = dialog.design_settings()
        for editor in self._editors.values():
            editor.load_project()
        self._pm.mark_modified()

    # ======================================================== tools / help
    def show_settings(self) -> None:
        """Tools → Settings."""
        SettingsDialog(self._settings, self).exec()
        self._refresh_all()

    def show_material_database(self, tab: int = TAB_CONCRETE) -> None:
        """Tools → Material / Reinforcement Database."""
        if not self._commit_editor():
            return
        dialog = MaterialDatabaseDialog(self._material_db, self._pm, tab, self)
        dialog.exec()
        if dialog.project_changed:
            for editor in self._editors.values():
                editor.load_project()
            self._refresh_all()

    def show_manual(self) -> None:
        """Help → User Manual."""
        UserManualDialog(self).exec()

    def show_about(self) -> None:
        """Help → About."""
        AboutDialog(self).exec()

    # ============================================================ geometry
    def _restore_geometry(self) -> None:
        text = self._settings.settings.window_geometry
        if text:
            self.restoreGeometry(QByteArray.fromBase64(text.encode("ascii")))

    def closeEvent(self, event: QCloseEvent) -> None:  # noqa: N802 (Qt API)
        """Ask to save before exit and store window geometry."""
        if not self._maybe_save_changes():
            event.ignore()
            return
        self._settings.settings.window_geometry = bytes(
            self.saveGeometry().toBase64().data()
        ).decode("ascii")
        self._settings.save()
        _log.info("%s %s closed", APP_NAME, APP_VERSION)
        event.accept()
