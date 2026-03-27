"""OCR fallback service."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Callable

logger = logging.getLogger(__name__)


class OcrProcessingError(Exception):
    """Raised when OCR text extraction fails."""


class OcrService:
    """Extract text from PDFs via an OCR backend."""

    def __init__(self, engine: Callable[[Path], str]) -> None:
        self._engine = engine

    def extract_text(
        self,
        pdf_path: Path,
        *,
        run_id: str | None = None,
        command: str | None = None,
    ) -> str:
        """Run OCR and return extracted text."""

        logger.info(
            "ocr.started",
            extra={
                "event": "ocr.started",
                "run_id": run_id,
                "command": command,
                "document_path": str(pdf_path),
            },
        )
        try:
            text = self._engine(pdf_path)
        except Exception as exc:  # pragma: no cover - defensive translation boundary
            logger.error(
                "ocr.failed",
                extra={
                    "event": "ocr.failed",
                    "run_id": run_id,
                    "command": command,
                    "document_path": str(pdf_path),
                    "error_type": type(exc).__name__,
                    "error_domain": "ocr",
                },
            )
            raise OcrProcessingError(f"OCR failed for '{pdf_path}'.") from exc

        logger.info(
            "ocr.succeeded",
            extra={
                "event": "ocr.succeeded",
                "run_id": run_id,
                "command": command,
                "document_path": str(pdf_path),
                "text_length": len(text),
            },
        )
        return text
