"""Tests for processed-file status persistence."""

from __future__ import annotations

import json

import pytest

from supply_chain_checker.services.status_service import StatusService, StatusTrackingError


def test_status_service_loads_missing_file_as_empty(tmp_path) -> None:
    service = StatusService(status_file_path=tmp_path / "processed_files.json")

    loaded = service.load()

    assert loaded == {}


def test_status_service_persists_minimum_fields_and_timestamp(tmp_path) -> None:
    status_path = tmp_path / "state" / "processed_files.json"
    service = StatusService(status_file_path=status_path)

    service.load()
    service.mark_processed("invoice_01.pdf")
    service.persist()

    payload = json.loads(status_path.read_text(encoding="utf-8"))

    assert "processed_files" in payload
    assert len(payload["processed_files"]) == 1
    first_entry = payload["processed_files"][0]
    assert first_entry["file_name"] == "invoice_01.pdf"
    assert isinstance(first_entry["processed_at_utc"], str)
    assert first_entry["processed_at_utc"].endswith("Z")


def test_status_service_supports_optional_hash_field(tmp_path) -> None:
    status_path = tmp_path / "processed_files.json"
    service = StatusService(status_file_path=status_path)

    service.load()
    service.mark_processed("invoice_02.pdf", file_hash="abc123")
    service.persist()

    payload = json.loads(status_path.read_text(encoding="utf-8"))

    assert payload["processed_files"][0]["file_hash"] == "abc123"


def test_status_service_rejects_invalid_payload(tmp_path) -> None:
    status_path = tmp_path / "processed_files.json"
    status_path.write_text('{"processed_files": {}}', encoding="utf-8")

    service = StatusService(status_file_path=status_path)

    with pytest.raises(StatusTrackingError, match="format is invalid"):
        service.load()
