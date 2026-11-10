"""Project explorer sidebar (tree of pages and members)."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QLabel,
    QStyle,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.core.constants import DesignType
from app.core.project_model import Project
from app.gui.widgets.icons import design_icon

PAGE_OVERVIEW: str = "overview"
PAGE_SELECTION: str = "selection"

_ROLE = Qt.ItemDataRole.UserRole


class ProjectSidebar(QFrame):
    """Tree with Project / Design sections.

    Signals:
        page_requested(str): ``"overview"``, ``"selection"`` or a DesignType value.
        member_requested(object, str): ``(DesignType, member_id)``.
    """

    page_requested = Signal(str)
    member_requested = Signal(object, str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("SidebarFrame")
        self.setMinimumWidth(210)

        header = QLabel("PROJECT EXPLORER")
        header.setObjectName("SidebarHeader")

        self._tree = QTreeWidget()
        self._tree.setHeaderHidden(True)
        self._tree.setIndentation(16)
        self._tree.itemClicked.connect(self._on_item_activated)
        self._tree.itemActivated.connect(self._on_item_activated)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(header)
        layout.addWidget(self._tree)
        self.refresh(None)

    # ----------------------------------------------------------------- build
    def refresh(self, project: Project | None) -> None:
        """Rebuild the tree from *project* (None shows an empty hint)."""
        expanded = self._expanded_keys()
        self._tree.blockSignals(True)
        self._tree.clear()
        if project is None:
            hint = QTreeWidgetItem(["No project open"])
            hint.setFlags(Qt.ItemFlag.NoItemFlags)
            self._tree.addTopLevelItem(hint)
            self._tree.blockSignals(False)
            return

        style = self.style()
        project_root = QTreeWidgetItem([f"Project: {project.information.project_name or 'Untitled'}"])
        project_root.setIcon(0, style.standardIcon(QStyle.StandardPixmap.SP_DirHomeIcon))
        project_root.setData(0, _ROLE, ("page", PAGE_OVERVIEW))
        info_item = QTreeWidgetItem(["Project Information"])
        info_item.setIcon(0, style.standardIcon(QStyle.StandardPixmap.SP_FileDialogDetailedView))
        info_item.setData(0, _ROLE, ("page", PAGE_OVERVIEW))
        project_root.addChild(info_item)

        design_root = QTreeWidgetItem(["Design"])
        design_root.setIcon(0, style.standardIcon(QStyle.StandardPixmap.SP_DirIcon))
        design_root.setData(0, _ROLE, ("page", PAGE_SELECTION))
        for design_type in DesignType:
            members = project.members_of(design_type)
            type_item = QTreeWidgetItem([f"{design_type.title} ({len(members)})"])
            type_item.setIcon(0, design_icon(design_type))
            type_item.setData(0, _ROLE, ("page", design_type.value))
            for member in members:
                child = QTreeWidgetItem([member.name])
                child.setData(0, _ROLE, ("member", design_type.value, member.member_id))
                type_item.addChild(child)
            design_root.addChild(type_item)

        self._tree.addTopLevelItem(project_root)
        self._tree.addTopLevelItem(design_root)
        project_root.setExpanded(True)
        design_root.setExpanded(True)
        for index in range(design_root.childCount()):
            item = design_root.child(index)
            if self._item_key(item) in expanded:
                item.setExpanded(True)
        self._tree.blockSignals(False)

    def _expanded_keys(self) -> set[str]:
        keys: set[str] = set()
        for index in range(self._tree.topLevelItemCount()):
            top = self._tree.topLevelItem(index)
            for child_index in range(top.childCount()):
                child = top.child(child_index)
                if child.isExpanded():
                    keys.add(self._item_key(child))
        return keys

    @staticmethod
    def _item_key(item: QTreeWidgetItem) -> str:
        data = item.data(0, _ROLE)
        return "|".join(str(part) for part in data) if isinstance(data, tuple) else item.text(0)

    # --------------------------------------------------------------- signals
    def _on_item_activated(self, item: QTreeWidgetItem, _column: int = 0) -> None:
        data = item.data(0, _ROLE)
        if not isinstance(data, tuple):
            return
        if data[0] == "page":
            self.page_requested.emit(str(data[1]))
        elif data[0] == "member":
            self.member_requested.emit(DesignType(data[1]), str(data[2]))
