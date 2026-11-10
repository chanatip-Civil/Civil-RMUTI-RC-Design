"""Locations of bundled resources, valid both from source and in the installed app.

When the program runs from a PyInstaller build, data files are unpacked
next to the executable (``sys._MEIPASS``); otherwise they live in the
source tree. User data is never stored here (see :mod:`app.core.settings`).
"""

from __future__ import annotations

import sys
from pathlib import Path

_SOURCE_ROOT: Path = Path(__file__).resolve().parent.parent.parent


def is_frozen() -> bool:
    """True when running from the installed (PyInstaller) build."""
    return bool(getattr(sys, "frozen", False))


def app_root() -> Path:
    """Folder that contains the ``app`` package and bundled resources."""
    bundle = getattr(sys, "_MEIPASS", None)
    return Path(bundle) if bundle else _SOURCE_ROOT


def resource_path(*parts: str) -> Path:
    """Path of a bundled resource, e.g. ``resource_path("app", "gui", "resources", "x.png")``."""
    return app_root().joinpath(*parts)
