"""Safe file input/output helpers.

Files are written atomically (write to a temporary file in the same folder,
flush, then ``os.replace``) so that a crash or power loss during saving can
never leave a half-written project file. The previous version is kept as a
``.bak`` backup.
"""

from __future__ import annotations

import json
import os
import shutil
import tempfile
from pathlib import Path
from typing import Any

from app.core.exceptions import ProjectFileError

BACKUP_SUFFIX: str = ".bak"


def ensure_extension(path: Path | str, extension: str) -> Path:
    """Return *path* with *extension* appended if it is missing."""
    result = Path(path)
    if result.suffix.lower() != extension.lower():
        result = result.with_name(result.name + extension)
    return result


def atomic_write_text(path: Path | str, text: str, keep_backup: bool = True) -> Path:
    """Write *text* to *path* atomically.

    Args:
        path: Destination file.
        text: Text content (UTF-8).
        keep_backup: Copy the existing file to ``<name>.bak`` first.

    Returns:
        The destination path.

    Raises:
        ProjectFileError: If the file cannot be written.
    """
    target = Path(path)
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        if keep_backup and target.exists():
            shutil.copy2(target, target.with_name(target.name + BACKUP_SUFFIX))
        fd, tmp_name = tempfile.mkstemp(
            prefix=f".{target.name}.", suffix=".tmp", dir=target.parent
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
                handle.write(text)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(tmp_name, target)
        except BaseException:
            Path(tmp_name).unlink(missing_ok=True)
            raise
    except OSError as exc:
        raise ProjectFileError(f"Cannot write file '{target}': {exc.strerror or exc}") from exc
    return target


def write_json(path: Path | str, data: Any, keep_backup: bool = True) -> Path:
    """Serialize *data* as pretty JSON and write it atomically."""
    try:
        text = json.dumps(data, indent=2, ensure_ascii=False)
    except (TypeError, ValueError) as exc:
        raise ProjectFileError(f"Data cannot be converted to JSON: {exc}") from exc
    return atomic_write_text(path, text + "\n", keep_backup=keep_backup)


def read_json(path: Path | str) -> Any:
    """Read and parse a JSON file.

    Raises:
        ProjectFileError: If the file is missing, unreadable or not valid JSON.
    """
    source = Path(path)
    if not source.is_file():
        raise ProjectFileError(f"File not found: '{source}'")
    try:
        text = source.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise ProjectFileError(f"Cannot read file '{source}': {exc}") from exc
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise ProjectFileError(
            f"File '{source.name}' is corrupted or is not a valid project file "
            f"(JSON error at line {exc.lineno}, column {exc.colno})."
        ) from exc
