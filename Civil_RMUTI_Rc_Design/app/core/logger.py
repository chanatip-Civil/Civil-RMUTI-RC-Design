"""Logging configuration (console + rotating error log file)."""

from __future__ import annotations

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

LOGGER_NAME: str = "rcdesign"
LOG_FILE_NAME: str = "rcdesign.log"
_LOG_FORMAT: str = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"


def setup_logging(log_dir: Path, level: int = logging.INFO) -> Path:
    """Configure the application logger.

    Args:
        log_dir: Directory for the log file (created if missing).
        level: Minimum log level.

    Returns:
        Path of the log file.
    """
    logger = logging.getLogger(LOGGER_NAME)
    logger.setLevel(level)
    log_path = Path(log_dir) / LOG_FILE_NAME
    if logger.handlers:
        return log_path

    formatter = logging.Formatter(_LOG_FORMAT)
    if sys.stderr is not None:  # The installed Windows app has no console.
        console = logging.StreamHandler()
        console.setFormatter(formatter)
        logger.addHandler(console)

    try:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = RotatingFileHandler(
            log_path, maxBytes=1_000_000, backupCount=3, encoding="utf-8"
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    except OSError as exc:  # Logging must never stop the application.
        logger.warning("File logging disabled: %s", exc)
    return log_path


def get_logger(name: str) -> logging.Logger:
    """Return a child logger of the application logger."""
    return logging.getLogger(f"{LOGGER_NAME}.{name}")
