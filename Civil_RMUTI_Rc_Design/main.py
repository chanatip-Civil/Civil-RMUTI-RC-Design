"""Entry point of Civil RMUTI Rc Design.

Usage::

    python main.py                      # start with the welcome page
    python main.py path/to/file.rcproj  # start and open a project
"""

from __future__ import annotations

import sys
from pathlib import Path


def _check_python() -> None:
    if sys.version_info < (3, 10):
        sys.stderr.write("Civil RMUTI Rc Design requires Python 3.10 or newer (3.12+ recommended).\n")
        sys.exit(1)


def _set_windows_app_id() -> None:
    """Give the app its own taskbar identity so Windows shows its icon."""
    if sys.platform == "win32":
        try:
            import ctypes

            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("RMUTI.CivilRcDesign")
        except (AttributeError, OSError):
            pass


def _message(text: str) -> None:
    """Print to the console when there is one (the installed app has none)."""
    if sys.stderr is not None:
        sys.stderr.write(text)


def main() -> int:
    """Create the Qt application and run the event loop."""
    _check_python()
    _set_windows_app_id()
    try:
        from PySide6.QtCore import Qt
        from PySide6.QtGui import QGuiApplication
        from PySide6.QtWidgets import QApplication
    except ImportError:
        _message("PySide6 is not installed.\nRun:  pip install -r requirements.txt\n")
        return 1

    from app.core.constants import (
        APP_NAME,
        APP_SHORT_NAME,
        APP_VERSION,
        ORGANIZATION_DOMAIN,
        ORGANIZATION_NAME,
        PROJECT_FILE_EXTENSION,
    )
    from app.core.logger import get_logger, setup_logging
    from app.core.project_manager import ProjectManager
    from app.core.settings import SettingsManager, logs_dir
    from app.gui.error_handler import GlobalExceptionHandler
    from app.gui.main_window import MainWindow
    from app.gui.styles import APP_STYLESHEET
    from app.gui.widgets.icons import app_icon

    setup_logging(logs_dir())
    log = get_logger("main")
    log.info("Starting %s %s", APP_NAME, APP_VERSION)

    # High-DPI: Qt 6 scales automatically; keep fractional factors (125 %, 150 %).
    QGuiApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    app = QApplication(sys.argv)
    app.setApplicationName(APP_SHORT_NAME)
    app.setApplicationDisplayName(APP_NAME)
    app.setApplicationVersion(APP_VERSION)
    app.setOrganizationName(ORGANIZATION_NAME)
    app.setOrganizationDomain(ORGANIZATION_DOMAIN)
    app.setStyle("Fusion")
    app.setStyleSheet(APP_STYLESHEET)
    app.setWindowIcon(app_icon())

    project_manager = ProjectManager()
    settings_manager = SettingsManager()
    window = MainWindow(settings_manager, project_manager)
    GlobalExceptionHandler(project_manager, lambda: window).install()
    window.show()

    for argument in sys.argv[1:]:
        if argument.lower().endswith((PROJECT_FILE_EXTENSION, ".json")) and Path(argument).is_file():
            window.open_project(Path(argument))
            break

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
