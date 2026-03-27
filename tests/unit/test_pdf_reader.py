"""Tests for direct PDF extraction and OCR fallback behavior."""

from __future__ import annotations

import logging
from pathlib import Path

import pytest

from supply_chain_checker.services.ocr_service import OcrService
from supply_chain_checker.services.pdf_reader import PdfReader


def test_read_text_prefers_direct_extraction_and_skips_ocr(caplog: pytest.LogCaptureFixture) -> None:
    ocr_calls: list[Path] = []

    def _direct_extractor(_: Path) -> str:
        return "Invoice No. 1001\nProduct: Steel Pipe\nQuantity: 100"

    def _ocr_engine(pdf_path: Path) -> str:
        ocr_calls.append(pdf_path)
        return "ocr text"

    reader = PdfReader(
        direct_extractor=_direct_extractor,
        ocr_service=OcrService(engine=_ocr_engine),
    )

    with caplog.at_level(logging.INFO):
        text = reader.read_text(Path("invoice.pdf"), run_id="run123", command="extract")

    assert "Steel Pipe" in text
    assert ocr_calls == []
    assert "pdf.read.succeeded" in caplog.text
    assert "ocr.started" not in caplog.text


def test_read_text_uses_ocr_for_unusable_direct_text(caplog: pytest.LogCaptureFixture) -> None:
    def _direct_extractor(_: Path) -> str:
        return " \n\t "

    def _ocr_engine(_: Path) -> str:
        return "Scanned invoice text from OCR"

    reader = PdfReader(
        direct_extractor=_direct_extractor,
        ocr_service=OcrService(engine=_ocr_engine),
    )

    with caplog.at_level(logging.INFO):
        text = reader.read_text(Path("scanned.pdf"), run_id="run123", command="extract")

    assert text == "Scanned invoice text from OCR"
    assert "pdf.read.unusable_text_detected" in caplog.text
    assert "ocr.started" in caplog.text
    assert "ocr.succeeded" in caplog.text
