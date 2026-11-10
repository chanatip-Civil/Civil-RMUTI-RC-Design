"""Read-only text report viewer with Copy and Save."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtGui import QFontDatabase, QGuiApplication
from PySide6.QtWidgets import (
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.core.exceptions import ProjectFileError
from app.utils.file_manager import atomic_write_text, ensure_extension


class ReportDialog(QDialog):
    """Shows a plain text report."""

    def __init__(self, title: str, text: str, suggested_name: str,
                 parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(title)
        self.resize(820, 640)
        self._text = text
        self._suggested_name = "".join(
            ch if ch.isalnum() or ch in "-_" else "_" for ch in suggested_name
        )

        editor = QPlainTextEdit(text)
        editor.setReadOnly(True)
        editor.setFont(QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont))
        editor.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)

        copy_button = QPushButton("Copy")
        copy_button.clicked.connect(self._copy)
        save_button = QPushButton("Save as Text...")
        save_button.clicked.connect(self._save)
        close_button = QPushButton("Close")
        close_button.setObjectName("PrimaryButton")
        close_button.clicked.connect(self.accept)

        buttons = QHBoxLayout()
        buttons.addWidget(copy_button)
        buttons.addWidget(save_button)
        buttons.addStretch()
        buttons.addWidget(close_button)

        layout = QVBoxLayout(self)
        layout.addWidget(editor)
        layout.addLayout(buttons)

    def _copy(self) -> None:
        QGuiApplication.clipboard().setText(self._text)

    def _save(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Report", f"{self._suggested_name}_report.txt", "Text files (*.txt)"
        )
        if not path:
            return
        try:
            atomic_write_text(ensure_extension(Path(path), ".txt"), self._text, keep_backup=False)
        except ProjectFileError as exc:
            QMessageBox.critical(self, "Save Report", str(exc))
