"""Product extraction orchestration service."""

from __future__ import annotations

import logging
from pathlib import Path

from supply_chain_checker.services.ocr_service import OcrProcessingError
from supply_chain_checker.services.pdf_reader import PdfProcessingError, PdfReader

logger = logging.getLogger(__name__)


class ExtractionService:
    """Coordinate document text loading for extraction runs."""

    def __init__(self, pdf_reader: PdfReader) -> None:
        self._pdf_reader = pdf_reader

    def load_document_text(
        self,
        pdf_path: Path,
        *,
        use_ocr_fallback: bool,
        run_id: str | None = None,
        command: str = "extract",
    ) -> str:
        """Load text for a single PDF with OCR fallback handling."""

        logger.info(
            "extraction.started",
            extra={
                "event": "extraction.started",
                "run_id": run_id,
                "command": command,
                "document_path": str(pdf_path),
            },
        )
        try:
            text = self._pdf_reader.read_text(
                pdf_path,
                use_ocr_fallback=use_ocr_fallback,
                run_id=run_id,
                command=command,
            )
        except (PdfProcessingError, OcrProcessingError) as exc:
            logger.warning(
                "extraction.failed",
                extra={
                    "event": "extraction.failed",
                    "run_id": run_id,
                    "command": command,
                    "document_path": str(pdf_path),
                    "error_type": type(exc).__name__,
                },
            )
            raise

        logger.info(
            "extraction.succeeded",
            extra={
                "event": "extraction.succeeded",
                "run_id": run_id,
                "command": command,
                "document_path": str(pdf_path),
                "text_length": len(text),
            },
        )
        return text
