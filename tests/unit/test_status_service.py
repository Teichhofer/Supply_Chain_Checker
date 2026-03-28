"""Tests for processed-file status persistence."""

from __future__ import annotations

import json
from pathlib import Path

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


def test_status_service_rejects_non_mapping_root_payload(tmp_path) -> None:
    status_path = tmp_path / "processed_files.json"
    status_path.write_text('["invalid"]', encoding="utf-8")
    service = StatusService(status_file_path=status_path)

    with pytest.raises(StatusTrackingError, match="format is invalid"):
        service.load()


def test_status_service_logs_error_domain_for_invalid_payload(tmp_path, caplog) -> None:
    status_path = tmp_path / "processed_files.json"
    status_path.write_text('{"processed_files": {}}', encoding="utf-8")
    service = StatusService(status_file_path=status_path)

    with caplog.at_level("ERROR"), pytest.raises(StatusTrackingError):
        service.load(on_corrupt_file="abort")

    assert "status.load.corrupt" in caplog.text
    assert any(record.__dict__.get("error_domain") == "status" for record in caplog.records)


def test_status_service_raises_on_invalid_json(tmp_path) -> None:
    status_path = tmp_path / "processed_files.json"
    status_path.write_text("{invalid json", encoding="utf-8")

    service = StatusService(status_file_path=status_path)

    with pytest.raises(StatusTrackingError, match="Could not read status file"):
        service.load()


def test_status_service_fallbacks_to_empty_entries_for_invalid_json(tmp_path, caplog) -> None:
    status_path = tmp_path / "processed_files.json"
    status_path.write_text("{invalid json", encoding="utf-8")
    service = StatusService(status_file_path=status_path)

    with caplog.at_level("WARNING"):
        loaded = service.load(on_corrupt_file="fallback_empty")

    assert loaded == {}
    assert "status.load.corrupt" in caplog.text
    assert any(record.__dict__.get("error_domain") == "status" for record in caplog.records)


def test_status_service_rejects_invalid_entry_shape(tmp_path) -> None:
    status_path = tmp_path / "processed_files.json"
    status_path.write_text('{"processed_files": ["bad"]}', encoding="utf-8")

    service = StatusService(status_file_path=status_path)

    with pytest.raises(StatusTrackingError, match="must be a mapping"):
        service.load()


def test_status_service_rejects_invalid_entry_fields(tmp_path) -> None:
    status_path = tmp_path / "processed_files.json"
    status_path.write_text(
        json.dumps(
            {
                "processed_files": [
                    {"file_name": "", "processed_at_utc": "2026-01-01T00:00:00Z"},
                ]
            }
        ),
        encoding="utf-8",
    )

    service = StatusService(status_file_path=status_path)

    with pytest.raises(StatusTrackingError, match="invalid file_name"):
        service.load()


def test_status_service_rejects_invalid_processed_timestamp(tmp_path) -> None:
    status_path = tmp_path / "processed_files.json"
    status_path.write_text(
        json.dumps(
            {
                "processed_files": [
                    {"file_name": "invoice_01.pdf", "processed_at_utc": ""},
                ]
            }
        ),
        encoding="utf-8",
    )

    service = StatusService(status_file_path=status_path)

    with pytest.raises(StatusTrackingError, match="invalid processed_at_utc"):
        service.load()


def test_status_service_rejects_invalid_hash_type(tmp_path) -> None:
    status_path = tmp_path / "processed_files.json"
    status_path.write_text(
        json.dumps(
            {
                "processed_files": [
                    {
                        "file_name": "invoice_01.pdf",
                        "processed_at_utc": "2026-01-01T00:00:00Z",
                        "file_hash": 123,
                    },
                ]
            }
        ),
        encoding="utf-8",
    )

    service = StatusService(status_file_path=status_path)

    with pytest.raises(StatusTrackingError, match="invalid file_hash"):
        service.load()


def test_status_service_load_reads_valid_entries(tmp_path) -> None:
    status_path = tmp_path / "processed_files.json"
    status_path.write_text(
        json.dumps(
            {
                "processed_files": [
                    {
                        "file_name": "invoice_01.pdf",
                        "processed_at_utc": "2026-01-01T00:00:00Z",
                        "file_hash": "hash-1",
                    },
                    {
                        "file_name": "invoice_02.pdf",
                        "processed_at_utc": "2026-01-02T00:00:00Z",
                        "file_hash": None,
                    },
                ]
            }
        ),
        encoding="utf-8",
    )

    service = StatusService(status_file_path=status_path)
    loaded = service.load()

    assert loaded["invoice_01.pdf"].file_hash == "hash-1"
    assert loaded["invoice_02.pdf"].processed_at_utc == "2026-01-02T00:00:00Z"


def test_status_service_rejects_blank_file_name_on_mark_processed(tmp_path) -> None:
    service = StatusService(status_file_path=tmp_path / "processed_files.json")

    with pytest.raises(StatusTrackingError, match="file_name must be a non-empty string"):
        service.mark_processed("   ")


def test_status_service_raises_when_persist_write_fails(tmp_path, monkeypatch) -> None:
    status_path = tmp_path / "processed_files.json"
    service = StatusService(status_file_path=status_path)
    service.load()
    service.mark_processed("invoice_03.pdf")

    def _raise_os_error(*args, **kwargs) -> None:
        raise OSError("disk full")

    monkeypatch.setattr(Path, "write_text", _raise_os_error)

    with pytest.raises(StatusTrackingError, match="Could not persist status file"):
        service.persist()


def test_select_unprocessed_pdfs_returns_sorted_new_pdfs_only(tmp_path) -> None:
    input_dir = tmp_path / "input"
    input_dir.mkdir(parents=True, exist_ok=True)
    (input_dir / "b_invoice.pdf").write_text("dummy", encoding="utf-8")
    (input_dir / "a_invoice.PDF").write_text("dummy", encoding="utf-8")
    (input_dir / "notes.txt").write_text("dummy", encoding="utf-8")
    (input_dir / "subdir").mkdir()

    service = StatusService(status_file_path=tmp_path / "processed_files.json")
    service.load()
    service.mark_processed("b_invoice.pdf")

    selected = service.select_unprocessed_pdfs(input_dir)

    assert [path.name for path in selected] == ["a_invoice.PDF"]


def test_select_unprocessed_pdfs_logs_processed_skip_count(tmp_path, caplog) -> None:
    input_dir = tmp_path / "input"
    input_dir.mkdir(parents=True, exist_ok=True)
    (input_dir / "invoice_a.pdf").write_text("dummy", encoding="utf-8")
    (input_dir / "invoice_b.pdf").write_text("dummy", encoding="utf-8")
    (input_dir / "ignore.csv").write_text("dummy", encoding="utf-8")

    service = StatusService(status_file_path=tmp_path / "processed_files.json")
    service.load()
    service.mark_processed("invoice_a.pdf")

    with caplog.at_level("INFO"):
        selected = service.select_unprocessed_pdfs(input_dir)

    assert [path.name for path in selected] == ["invoice_b.pdf"]
    selection_logs = [
        record for record in caplog.records if record.msg == "status.selection.completed"
    ]
    assert len(selection_logs) == 1
    assert selection_logs[0].discovered_pdf_count == 2
    assert selection_logs[0].selected_pdf_count == 1
    assert selection_logs[0].skipped_processed_count == 1
