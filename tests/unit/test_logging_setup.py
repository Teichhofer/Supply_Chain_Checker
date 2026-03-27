"""Tests for logging setup and run lifecycle logging."""

from __future__ import annotations

import logging

from supply_chain_checker.logging_setup import setup_logging


def test_setup_logging_writes_unified_format_with_run_id(tmp_path) -> None:
    log_file = setup_logging(logs_dir=tmp_path, level="INFO", run_id="run-123", file_name="app.log")

    logger = logging.getLogger("supply_chain_checker.tests")
    logger.info("run.started")

    content = log_file.read_text(encoding="utf-8")
    assert "INFO" in content
    assert "supply_chain_checker.tests" in content
    assert "run_id=run-123" in content
    assert "run.started" in content


def test_setup_logging_respects_warning_level(tmp_path) -> None:
    log_file = setup_logging(
        logs_dir=tmp_path,
        level="WARNING",
        run_id="run-456",
        file_name="warning.log",
    )

    logger = logging.getLogger("supply_chain_checker.tests")
    logger.info("should_not_be_logged")
    logger.warning("should_be_logged")

    content = log_file.read_text(encoding="utf-8")
    assert "should_not_be_logged" not in content
    assert "should_be_logged" in content
