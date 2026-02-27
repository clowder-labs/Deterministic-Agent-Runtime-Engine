"""CLI file logging helpers."""

from __future__ import annotations

import logging
from pathlib import Path

from dare_framework.config import Config

DEFAULT_CLI_LOG_FILENAME = "dare.log"
CLI_LOGGER_NAME = "dare.client.cli"


def resolve_cli_log_path(config: Config | None = None, *, cwd: Path | None = None) -> Path:
    """Resolve the CLI log path from config or fall back to ``./dare.log``."""
    base_dir = (cwd or Path.cwd()).expanduser().resolve()
    raw_path = config.cli.log_path if config is not None else None
    if raw_path is None or not raw_path.strip():
        return base_dir / DEFAULT_CLI_LOG_FILENAME

    path = Path(raw_path.strip()).expanduser()
    if not path.is_absolute():
        path = (base_dir / path).resolve()
    return path


def configure_cli_logging(log_path: Path, *, level: int = logging.INFO) -> Path:
    """Send Python logging output to a single file and nowhere else."""
    resolved = log_path.expanduser().resolve()
    resolved.parent.mkdir(parents=True, exist_ok=True)

    root = logging.getLogger()
    for handler in list(root.handlers):
        root.removeHandler(handler)
        handler.close()

    file_handler = logging.FileHandler(resolved, encoding="utf-8", delay=True)
    file_handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s")
    )
    root.addHandler(file_handler)
    root.setLevel(level)
    logging.captureWarnings(True)
    return resolved


__all__ = [
    "CLI_LOGGER_NAME",
    "DEFAULT_CLI_LOG_FILENAME",
    "configure_cli_logging",
    "resolve_cli_log_path",
]
