"""Tests for CSV helper service."""

from __future__ import annotations

import csv
from datetime import datetime, timezone

from supply_chain_checker.run_context import RunContext
from supply_chain_checker.services.csv_service import (
    build_assessment_csv_path,
    build_extraction_csv_path,
    write_csv_rows,
)


def _context() -> RunContext:
    return RunContext(
        run_id="abc123def456",
        started_at_utc=datetime(2026, 3, 27, 12, 0, 0, tzinfo=timezone.utc),
    )


def test_build_csv_paths_include_unique_artifact_suffix(tmp_path) -> None:
    context = _context()

    extraction_path = build_extraction_csv_path(output_dir=tmp_path, run_context=context)
    assessment_path = build_assessment_csv_path(output_dir=tmp_path, run_context=context)

    assert extraction_path.name == "extraction_20260327T120000Z_abc123def456.csv"
    assert assessment_path.name == "assessment_20260327T120000Z_abc123def456.csv"


def test_write_csv_rows_injects_run_metadata_columns(tmp_path) -> None:
    context = _context()
    output_path = tmp_path / "out.csv"

    write_csv_rows(
        output_path=output_path,
        run_context=context,
        rows=[{"document_name": "invoice.pdf", "product_name": "Steel"}, {"product_name": "Copper"}],
    )

    with output_path.open("r", newline="", encoding="utf-8") as csv_file:
        reader = csv.DictReader(csv_file)
        rows = list(reader)

    assert reader.fieldnames is not None
    assert reader.fieldnames[:2] == ["run_id", "run_timestamp"]
    assert rows[0]["run_id"] == "abc123def456"
    assert rows[0]["run_timestamp"] == "2026-03-27T12:00:00Z"
    assert rows[0]["product_name"] == "Steel"
    assert rows[1]["document_name"] == ""
