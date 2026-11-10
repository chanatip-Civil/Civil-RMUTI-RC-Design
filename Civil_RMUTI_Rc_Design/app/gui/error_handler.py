"""Global handler for unexpected exceptions.

Unhandled exceptions are logged with a full traceback, an emergency recovery
copy of the open project is written, and a readable message is shown. The
application keeps running.
"""

from __future__ import annotations

import sys
import traceback
from types import TracebackType
from typing import Callable

from PySide6.QtWidgets import QApplication, QMessageBox, QWidget

from app.core.logger import get_logger
from app.core.project_manager import ProjectManager
from app.core.settings import logs_dir, recovery_dir

_log = get_logger("error_handler")


class GlobalExceptionHandler:
    """Installs itself as ``sys.excepthook``."""

    def __init__(self, project_manager: ProjectManager,
                 parent_provider: Callable[[], QWidget | None]) -> None:
        self._pm = project_manager
        self._parent_provider = parent_provider
        self._handling = False
        self._previous_hook = sys.excepthook

    def install(self) -> None:
        """Activate the handler."""
        sys.excepthook = self.handle

    def uninstall(self) -> None:
        """Restore the previous hook."""
        sys.excepthook = self._previous_hook

    def handle(self, exc_type: type[BaseException], exc: BaseException,
               tb: TracebackType | None) -> None:
        """Log, save a recovery copy and inform the user."""
        if issubclass(exc_type, KeyboardInterrupt):
            self._previous_hook(exc_type, exc, tb)
            return
        _log.critical("Unhandled exception:\n%s",
                      "".join(traceback.format_exception(exc_type, exc, tb)))
        if self._handling:  # Error while showing an error: log only.
            return
        self._handling = True
        try:
            recovery = self._pm.save_recovery_copy(recovery_dir())
            message = (
                "An unexpected error occurred, but the program is still running.\n\n"
                f"{exc_type.__name__}: {exc}\n\n"
                f"Details were written to the error log:\n{logs_dir()}"
            )
            if recovery is not None:
                message += f"\n\nA recovery copy of your project was saved to:\n{recovery}"
            if QApplication.instance() is not None:
                QMessageBox.critical(self._parent_provider(), "Unexpected Error", message)
        except Exception:  # pragma: no cover - last line of defence
            _log.exception("Error handler failed")
        finally:
            self._handling = False
