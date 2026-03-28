"""Tests for recoverable/non-recoverable logging levels."""

from __future__ import annotations

import logging

import pytest

from supply_chain_checker.services.csv_service import StorageIOError, select_latest_extraction_csv
from supply_chain_checker.services.status_service import StatusService, StatusTrackingError


def test_recoverable_corrupt_status_file_is_logged_as_warning(tmp_path, caplog) -> None:
    status_path = tmp_path / "processed_files.json"
    status_path.write_text("{invalid json", encoding="utf-8")

    service = StatusService(status_file_path=status_path)

    with caplog.at_level(logging.WARNING):
        loaded = service.load(on_corrupt_file="fallback_empty")

    assert loaded == {}
    relevant = [
        record
        for record in caplog.records
        if getattr(record, "event", None) == "status.load.corrupt"
    ]
    assert len(relevant) == 1
    assert relevant[0].levelno == logging.WARNING


def test_nonrecoverable_corrupt_status_file_is_logged_as_error(tmp_path, caplog) -> None:
    status_path = tmp_path / "processed_files.json"
    status_path.write_text("{invalid json", encoding="utf-8")

    service = StatusService(status_file_path=status_path)

    with caplog.at_level(logging.ERROR), pytest.raises(StatusTrackingError):
        service.load(on_corrupt_file="abort")

    relevant = [
        record
        for record in caplog.records
        if getattr(record, "event", None) == "status.load.corrupt"
    ]
    assert len(relevant) == 1
    assert relevant[0].levelno == logging.ERROR


def test_missing_extraction_csv_is_logged_as_error(tmp_path, caplog) -> None:
    with caplog.at_level(logging.ERROR), pytest.raises(StorageIOError):
        select_latest_extraction_csv(output_dir=tmp_path)

    relevant = [
        record
        for record in caplog.records
        if getattr(record, "event", None) == "csv.extraction.latest.missing"
    ]
    assert len(relevant) == 1
    assert relevant[0].levelno == logging.ERROR
