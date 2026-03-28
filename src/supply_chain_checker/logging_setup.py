"""Logging setup for Supply Chain Checker."""

from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class _RunContextFilter(logging.Filter):
    def __init__(self, run_id: str) -> None:
        super().__init__()
        self._run_id = run_id

    def filter(self, record: logging.LogRecord) -> bool:
        if not hasattr(record, "run_id"):
            record.run_id = self._run_id
        return True


def setup_logging(*, logs_dir: Path, level: str, run_id: str, file_name: str) -> Path:
    """Configure root logger with unified formatter and file logging."""

    logs_dir.mkdir(parents=True, exist_ok=True)
    log_file_path = logs_dir / file_name

    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level))

    for handler in list(root_logger.handlers):
        root_logger.removeHandler(handler)
        if isinstance(handler, logging.FileHandler):
            handler.close()

    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)s | %(name)s | run_id=%(run_id)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    run_context_filter = _RunContextFilter(run_id=run_id)

    file_handler = logging.FileHandler(log_file_path, encoding="utf-8")
    file_handler.setLevel(getattr(logging, level))
    file_handler.setFormatter(formatter)
    file_handler.addFilter(run_context_filter)

    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(getattr(logging, level))
    stream_handler.setFormatter(formatter)
    stream_handler.addFilter(run_context_filter)

    root_logger.addHandler(file_handler)
    root_logger.addHandler(stream_handler)

    logger.debug(
        "logging.setup.completed",
        extra={"event": "logging.setup.completed", "run_id": run_id},
    )
    return log_file_path
