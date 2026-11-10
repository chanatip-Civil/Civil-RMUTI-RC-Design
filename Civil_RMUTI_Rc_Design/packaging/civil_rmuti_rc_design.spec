# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller build recipe for Civil RMUTI Rc Design (Windows).

Run through packaging/build_installer.bat, or directly:

    pyinstaller packaging/civil_rmuti_rc_design.spec --noconfirm --clean

Output: dist/CivilRMUTIRcDesign/CivilRMUTIRcDesign.exe (one-folder build:
starts faster and triggers fewer antivirus false alarms than one-file).
"""

import sys
from pathlib import Path

from PyInstaller.utils.hooks import collect_submodules

ROOT = Path(SPECPATH).resolve().parent
sys.path.insert(0, str(ROOT))

from app.core.constants import APP_NAME, APP_VERSION, ORGANIZATION_NAME  # noqa: E402

EXE_NAME = "CivilRMUTIRcDesign"
ICON = ROOT / "packaging" / "build" / "app.ico"


def _version_tuple(text: str) -> tuple[int, int, int, int]:
    numbers = [int(part) for part in text.split(".") if part.isdigit()][:4]
    return tuple(numbers + [0] * (4 - len(numbers)))


def _version_info():
    from PyInstaller.utils.win32.versioninfo import (
        FixedFileInfo, StringFileInfo, StringStruct, StringTable, VarFileInfo, VarStruct, VSVersionInfo,
    )
    numbers = _version_tuple(APP_VERSION)
    return VSVersionInfo(
        ffi=FixedFileInfo(filevers=numbers, prodvers=numbers),
        kids=[
            StringFileInfo([StringTable("040904B0", [
                StringStruct("CompanyName", ORGANIZATION_NAME),
                StringStruct("FileDescription", APP_NAME),
                StringStruct("FileVersion", APP_VERSION),
                StringStruct("InternalName", EXE_NAME),
                StringStruct("OriginalFilename", f"{EXE_NAME}.exe"),
                StringStruct("ProductName", APP_NAME),
                StringStruct("ProductVersion", APP_VERSION),
            ])]),
            VarFileInfo([VarStruct("Translation", [1033, 1200])]),
        ],
    )


a = Analysis(
    [str(ROOT / "main.py")],
    pathex=[str(ROOT)],
    datas=[(str(ROOT / "app" / "gui" / "resources"), "app/gui/resources")],
    hiddenimports=collect_submodules("app") + ["matplotlib.backends.backend_qtagg"],
    excludes=[
        # Not used; excluding keeps the installer small and avoids mixing Qt bindings.
        "tkinter", "PyQt5", "PyQt6", "PySide2",
        "PySide6.QtWebEngineCore", "PySide6.QtWebEngineWidgets", "PySide6.QtQuick",
        "PySide6.QtQml", "PySide6.Qt3DCore", "PySide6.QtMultimedia", "PySide6.QtCharts",
        "PySide6.QtDataVisualization", "PySide6.QtBluetooth", "PySide6.QtPositioning",
        "pytest", "tests", "tools", "IPython", "notebook",
    ],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name=EXE_NAME,
    icon=str(ICON) if ICON.exists() else None,
    version=_version_info() if sys.platform == "win32" else None,
    console=False,            # GUI app: no black console window
    disable_windowed_traceback=False,
    upx=False,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name=EXE_NAME,
)
