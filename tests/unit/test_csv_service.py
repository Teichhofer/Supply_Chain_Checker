"""Tests for CSV artefact creation."""

from __future__ import annotations

import csv
from datetime import UTC, datetime

import pytest

from supply_chain_checker.models import ExtractedProduct
from supply_chain_checker.run_context import RunContext
from supply_chain_checker.services.assessment_service import ProductAssessmentResult
from supply_chain_checker.services.csv_service import (
    StorageIOError,
    build_run_csv_filename,
    create_run_csv_artifact,
    read_extraction_products_csv,
    select_latest_extraction_csv,
    write_assessment_results_csv,
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


def test_select_latest_extraction_csv_uses_timestamp_in_file_name(tmp_path) -> None:
    older = tmp_path / "extraction_20260327T100000Z_runolder1234.csv"
    newer = tmp_path / "extraction_20260327T120000Z_runnewer1234.csv"
    ignored = tmp_path / "extraction_invalid.csv"

    older.write_text("old", encoding="utf-8")
    newer.write_text("new", encoding="utf-8")
    ignored.write_text("ignored", encoding="utf-8")

    selected = select_latest_extraction_csv(output_dir=tmp_path)

    assert selected == newer


def test_select_latest_extraction_csv_raises_when_no_valid_file_exists(tmp_path) -> None:
    (tmp_path / "assessment_20260327T120000Z_run1234.csv").write_text("", encoding="utf-8")

    with pytest.raises(StorageIOError, match="Run 'extract' first"):
        select_latest_extraction_csv(output_dir=tmp_path)


def test_read_extraction_products_csv_loads_domain_rows(tmp_path) -> None:
    csv_path = tmp_path / "extraction_20260327T120000Z_run123.csv"
    csv_path.write_text(
        "\n".join(
            [
                "run_id,document_name,product_name,quantity,supplier,manufacturer,article_number,extraction_status,extraction_hint",
                "run123,invoice.pdf,Bolt,5,ACME,SupplierCo,ART-1,confirmed,",
            ]
        ),
        encoding="utf-8",
    )

    products = read_extraction_products_csv(csv_path=csv_path)

    assert len(products) == 1
    assert products[0].product_name == "Bolt"
    assert products[0].extraction_status == "confirmed"


def test_write_assessment_results_csv_keeps_skipped_products_and_skip_reason(tmp_path) -> None:
    context = RunContext(
        run_id="runid1234567",
        started_at_utc=datetime(2026, 3, 27, 12, 0, tzinfo=UTC),
    )
    result = ProductAssessmentResult(
        product=ExtractedProduct(
            document_name="invoice.pdf",
            product_name="UNKNOWN",
            quantity="5",
            supplier="ACME",
            extraction_status="uncertain",
        ),
        assessment_status="skipped",
        raw_response=None,
        skip_reason="UNCONFIRMED_EXTRACTION",
    )

    csv_path = write_assessment_results_csv(
        output_dir=tmp_path,
        run_context=context,
        results=[result],
    )
    with csv_path.open("r", encoding="utf-8", newline="") as csv_file:
        rows = list(csv.DictReader(csv_file))

    assert len(rows) == 1
    assert rows[0]["bewertungsstatus"] == "skipped"
    assert rows[0]["skip_reason"] == "UNCONFIRMED_EXTRACTION"
