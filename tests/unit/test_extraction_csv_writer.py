"""Tests for extraction CSV writing."""

from __future__ import annotations

import csv
from datetime import UTC, datetime
from pathlib import Path

import pytest

from supply_chain_checker.models import ExtractedProduct
from supply_chain_checker.run_context import RunContext
from supply_chain_checker.services.csv_service import StorageIOError, write_extraction_products_csv


def test_write_extraction_products_csv_creates_one_run_bound_csv_with_required_columns(
    tmp_path,
) -> None:
    run_context = RunContext(
        run_id="run123abc456",
        started_at_utc=datetime(2026, 3, 27, 12, 30, tzinfo=UTC),
    )
    products = [
        ExtractedProduct(
            document_name="invoice.pdf",
            product_name="Aluminium",
            quantity="5",
            supplier="RawSupply",
            extraction_status="uncertain",
            extraction_hint="supplier inferred",
        )
    ]

    csv_path = write_extraction_products_csv(
        output_dir=tmp_path,
        run_context=run_context,
        products=products,
    )

    assert csv_path.name == "extraction_20260327T123000Z_run123abc456.csv"

    with csv_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)

    assert reader.fieldnames == [
        "run_id",
        "document_name",
        "product_name",
        "quantity",
        "supplier",
        "manufacturer",
        "article_number",
        "extraction_status",
        "extraction_hint",
    ]
    assert len(rows) == 1
    assert rows[0]["run_id"] == "run123abc456"
    assert rows[0]["extraction_status"] == "uncertain"


def test_write_extraction_products_csv_raises_storage_io_error_on_os_error(
    tmp_path, monkeypatch
) -> None:
    run_context = RunContext(
        run_id="run123abc456",
        started_at_utc=datetime(2026, 3, 27, 12, 30, tzinfo=UTC),
    )

    def _raise_open_error(self, *args, **kwargs):  # type: ignore[no-untyped-def]
        raise OSError("disk full")

    monkeypatch.setattr(Path, "open", _raise_open_error)

    with pytest.raises(StorageIOError, match="Could not write extraction CSV"):
        write_extraction_products_csv(
            output_dir=tmp_path,
            run_context=run_context,
            products=[],
        )
