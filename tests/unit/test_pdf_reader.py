"""Tests for direct PDF extraction and OCR fallback behavior."""

from __future__ import annotations

import logging
import sys
import types
from pathlib import Path

import pytest

from supply_chain_checker.services.ocr_service import OcrProcessingError, OcrService
from supply_chain_checker.services.pdf_reader import (
    PdfProcessingError,
    PdfReader,
    extract_text_with_pypdf,
)


def test_read_text_prefers_direct_extraction_and_skips_ocr(
    caplog: pytest.LogCaptureFixture,
) -> None:
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


def test_read_text_returns_unusable_direct_text_when_ocr_disabled(
    caplog: pytest.LogCaptureFixture,
) -> None:
    reader = PdfReader(
        direct_extractor=lambda _: " \n\t ",
        ocr_service=OcrService(engine=lambda _: "should not be used"),
    )

    with caplog.at_level(logging.WARNING):
        text = reader.read_text(Path("invoice.pdf"), use_ocr_fallback=False)

    assert text == " \n\t "
    assert "pdf.read.unusable_without_ocr" in caplog.text


def test_read_text_raises_pdf_processing_error_for_direct_extractor_exception() -> None:
    def _broken_extractor(_: Path) -> str:
        raise RuntimeError("boom")

    reader = PdfReader(
        direct_extractor=_broken_extractor,
        ocr_service=OcrService(engine=lambda _: "unused"),
    )

    with pytest.raises(PdfProcessingError, match="Could not read PDF text"):
        reader.read_text(Path("invoice.pdf"))


def test_read_text_raises_ocr_processing_error_when_ocr_engine_fails() -> None:
    reader = PdfReader(
        direct_extractor=lambda _: "   ",
        ocr_service=OcrService(engine=lambda _: (_ for _ in ()).throw(RuntimeError("ocr down"))),
    )

    with pytest.raises(OcrProcessingError, match="OCR failed"):
        reader.read_text(Path("invoice.pdf"))


def test_extract_text_with_pypdf_returns_concatenated_page_text(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _FakePage:
        def __init__(self, text: str | None) -> None:
            self._text = text

        def extract_text(self) -> str | None:
            return self._text

    class _FakePdfReader:
        def __init__(self, _path: str) -> None:
            self.pages = [_FakePage("Invoice Header"), _FakePage(None), _FakePage("Line Item 1")]

    fake_module = types.SimpleNamespace(PdfReader=_FakePdfReader)
    monkeypatch.setitem(sys.modules, "pypdf", fake_module)

    text = extract_text_with_pypdf(Path("invoice.pdf"))

    assert text == "Invoice Header\nLine Item 1"
