"""Generic add / edit dialog for any material kind (built from the schema)."""

from __future__ import annotations

from typing import Any, Callable, Union

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QVBoxLayout,
    QWidget,
)

from app.gui.styles import ERROR, TEXT_MUTED
from app.materials.schema import (
    CHOICE,
    MAX_NAME_LENGTH,
    OPTIONAL_NUMBER,
    TEXT,
    MaterialItem,
    MaterialSchema,
    number_or_text,
)

#: Returns an error message if the name is not acceptable, else None.
NameValidator = Callable[[str], Union[str, None]]


class MaterialEditDialog(QDialog):
    """Form generated from :class:`MaterialSchema` fields."""

    def __init__(self, schema: MaterialSchema, values: dict[str, Any], title: str,
                 name_validator: NameValidator | None = None,
                 parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumWidth(440)
        self._schema = schema
        self._name_validator = name_validator
        self._item: MaterialItem | None = None
        self._editors: dict[str, Union[QLineEdit, QComboBox]] = {}

        form = QFormLayout()
        for spec in schema.fields:
            value = values.get(spec.key, spec.default)
            if spec.kind == CHOICE:
                combo = QComboBox()
                combo.addItems(list(spec.choices))
                index = combo.findText(str(value))
                combo.setCurrentIndex(max(index, 0))
                editor: Union[QLineEdit, QComboBox] = combo
            else:
                line = QLineEdit("" if value is None else (f"{value:g}" if isinstance(value, float)
                                                           else str(value)))
                if spec.kind != TEXT:
                    line.setAlignment(Qt.AlignmentFlag.AlignRight)
                if spec.key == schema.id_key:
                    line.setMaxLength(MAX_NAME_LENGTH)
                if spec.kind == OPTIONAL_NUMBER:
                    line.setPlaceholderText("blank = by design standard")
                editor = line
            if spec.tooltip:
                editor.setToolTip(spec.tooltip)
            self._editors[spec.key] = editor
            row = QWidget()
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(0, 0, 0, 0)
            row_layout.addWidget(editor, 1)
            unit = QLabel(spec.unit)
            unit.setMinimumWidth(48)
            unit.setStyleSheet(f"color: {TEXT_MUTED};")
            row_layout.addWidget(unit)
            required = spec.key == schema.id_key or spec.kind not in (TEXT, OPTIONAL_NUMBER, CHOICE)
            form.addRow(spec.label + (" *" if required else ""), row)

        self._error_label = QLabel()
        self._error_label.setWordWrap(True)
        self._error_label.setStyleSheet(f"color: {ERROR};")

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(self._error_label)
        layout.addWidget(buttons)
        first = self._editors.get(schema.id_key)
        if first is not None:
            first.setFocus()

    def raw_values(self) -> dict[str, Any]:
        """Current raw form values (numbers parsed where possible)."""
        values: dict[str, Any] = {}
        for spec in self._schema.fields:
            editor = self._editors[spec.key]
            if isinstance(editor, QComboBox):
                values[spec.key] = editor.currentText()
            elif spec.kind == TEXT:
                values[spec.key] = editor.text().strip()
            else:
                values[spec.key] = number_or_text(editor.text())
        return values

    def item(self) -> MaterialItem | None:
        """Validated item (available after the dialog was accepted)."""
        return self._item

    def _on_accept(self) -> None:
        result, item = self._schema.validate(self.raw_values())
        errors = list(result.errors)
        if item is not None and self._name_validator is not None:
            message = self._name_validator(item.name)
            if message:
                errors.append(message)
        if errors:
            self._error_label.setText("\n".join(errors))
            QMessageBox.warning(self, "Invalid Input", "\n".join(errors))
            return
        self._item = item
        self.accept()
