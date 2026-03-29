"""Tests for extraction XLSX writing."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from openpyxl import load_workbook

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

    xlsx_path = write_extraction_products_csv(
        output_dir=tmp_path,
        run_context=run_context,
        products=products,
    )

    assert xlsx_path.name == "extraction_20260327T123000Z_run123abc456.xlsx"

    workbook = load_workbook(xlsx_path, read_only=True, data_only=True)
    rows = list(workbook.active.iter_rows(values_only=True))

    assert list(rows[0]) == [
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
    assert len(rows) == 2
    assert rows[1][0] == "run123abc456"
    assert rows[1][7] == "uncertain"


def test_write_extraction_products_csv_raises_storage_io_error_on_os_error(
    tmp_path, monkeypatch
) -> None:
    run_context = RunContext(
        run_id="run123abc456",
        started_at_utc=datetime(2026, 3, 27, 12, 30, tzinfo=UTC),
    )

    def _raise_save(self, _path):
        raise OSError("disk full")

    monkeypatch.setattr("openpyxl.workbook.workbook.Workbook.save", _raise_save)

    with pytest.raises(StorageIOError, match="Could not write extraction XLSX"):
        write_extraction_products_csv(
            output_dir=tmp_path,
            run_context=run_context,
            products=[],
        )
