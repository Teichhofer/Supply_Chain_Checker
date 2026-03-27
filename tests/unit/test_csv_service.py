"""Tests for CSV artefact creation."""

from __future__ import annotations

import csv
from datetime import UTC, datetime

from supply_chain_checker.run_context import RunContext
from supply_chain_checker.services.csv_service import (
    build_run_csv_filename,
    create_run_csv_artifact,
)


def test_build_run_csv_filename_uses_domain_prefix_and_run_metadata() -> None:
    context = RunContext(
        run_id="abc123def456",
        started_at_utc=datetime(2026, 3, 27, 12, 0, tzinfo=UTC),
    )

    extraction_name = build_run_csv_filename(command="extract", run_context=context)
    assessment_name = build_run_csv_filename(command="assess", run_context=context)

    assert extraction_name == "extraction_20260327T120000Z_abc123def456.csv"
    assert assessment_name == "assessment_20260327T120000Z_abc123def456.csv"


def test_create_run_csv_artifact_contains_run_id_for_log_correlation(tmp_path) -> None:
    context = RunContext(
        run_id="runid1234567",
        started_at_utc=datetime(2026, 3, 27, 12, 0, tzinfo=UTC),
    )

    artifact_path = create_run_csv_artifact(
        output_dir=tmp_path,
        command="extract",
        run_context=context,
    )

    with artifact_path.open("r", encoding="utf-8", newline="") as csv_file:
        rows = list(csv.DictReader(csv_file))

    assert len(rows) == 1
    assert rows[0]["run_id"] == "runid1234567"
    assert rows[0]["command"] == "extract"
