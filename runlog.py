"""Run logging — a persistent debug log for post-mortem troubleshooting.

The console output is a progress display: it tells you what phase is running,
not why something failed. The failures worth debugging are usually swallowed —
a javac error that gets handed to the repair loop, an LLM retry storm, a
classpath that silently resolved empty.

So the log file is **always** written, to `<project>/.testgen-agent/run.log`
(the same directory as the checkpoint and reports — outside `target/`, which
`mvn clean` deletes). `--verbose` only controls whether debug output is
*also* echoed to the console.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Optional

LOGGER_NAME = "testgen"
LOG_FILENAME = "run.log"
_FORMAT = "%(asctime)s %(levelname)-5s [%(name)s] %(message)s"
_DATEFMT = "%H:%M:%S"

# The project whose log we are attached to. Guards against attaching a second
# set of handlers when setup_logging() is called from more than one entry point.
_configured_for: Optional[Path] = None


def setup_logging(project_path: Path, verbose: bool = False) -> Optional[Path]:
    """Attach the run logger to `<project>/.testgen-agent/run.log`.

    Idempotent: calling it again for the same project only re-checks the
    --verbose flag. Returns the log path, or None if the file could not be
    created — logging must never take down a run.
    """
    global _configured_for

    logger = logging.getLogger(LOGGER_NAME)
    log_path = project_path / ".testgen-agent" / LOG_FILENAME

    if _configured_for is not None and _configured_for == log_path:
        if verbose:
            _add_console_handler(logger)
        return log_path

    logger.setLevel(logging.DEBUG)
    logger.propagate = False
    for handler in list(logger.handlers):
        logger.removeHandler(handler)

    written: Optional[Path] = log_path
    try:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        # mode="w": one log per run. The run you want to debug is the one you
        # just finished.
        file_handler = logging.FileHandler(log_path, mode="w", encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(logging.Formatter(_FORMAT, _DATEFMT))
        logger.addHandler(file_handler)
    except OSError:
        # Read-only project dir, disk full, etc. Fall back to console only.
        written = None

    if verbose or written is None:
        _add_console_handler(logger)

    _configured_for = written
    return written


def _add_console_handler(logger: logging.Logger) -> None:
    """Add the stderr handler once (used only when --verbose)."""
    for handler in logger.handlers:
        if isinstance(handler, logging.StreamHandler) and not isinstance(
            handler, logging.FileHandler
        ):
            return
    stream = logging.StreamHandler(sys.stderr)
    stream.setLevel(logging.DEBUG)
    stream.setFormatter(logging.Formatter(_FORMAT, _DATEFMT))
    logger.addHandler(stream)


def get_logger(name: str) -> logging.Logger:
    """Get the logger for a module — call with __name__."""
    return logging.getLogger(f"{LOGGER_NAME}.{name}")


def log_path_for(project_path: Path) -> Path:
    """Where the log for a project lives (does not require setup first)."""
    return project_path / ".testgen-agent" / LOG_FILENAME
