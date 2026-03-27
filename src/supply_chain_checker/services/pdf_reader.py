"""PDF text extraction service with OCR fallback."""

from __future__ import annotations

import logging
from collections.abc import Callable
from pathlib import Path

from supply_chain_checker.services.ocr_service import OcrService

logger = logging.getLogger(__name__)

_DEFAULT_MIN_TEXT_LENGTH = 20
_DEFAULT_MIN_ALNUM_RATIO = 0.3


class PdfProcessingError(Exception):
    """Raised when direct PDF text extraction fails."""


class PdfReader:
    """Read PDF text with direct extraction first and optional OCR fallback."""

    def __init__(
        self,
        *,
        direct_extractor: Callable[[Path], str],
        ocr_service: OcrService,
        min_text_length: int = _DEFAULT_MIN_TEXT_LENGTH,
        min_alnum_ratio: float = _DEFAULT_MIN_ALNUM_RATIO,
    ) -> None:
        self._direct_extractor = direct_extractor
        self._ocr_service = ocr_service
        self._min_text_length = min_text_length
        self._min_alnum_ratio = min_alnum_ratio

    def read_text(
        self,
        pdf_path: Path,
        *,
        use_ocr_fallback: bool = True,
        run_id: str | None = None,
        command: str | None = None,
    ) -> str:
        """Read PDF text via direct extraction and use OCR only when required."""

        logger.info(
            "pdf.read.started",
            extra={
                "event": "pdf.read.started",
                "run_id": run_id,
                "command": command,
                "document_path": str(pdf_path),
            },
        )
        try:
            direct_text = self._direct_extractor(pdf_path)
        except Exception as exc:
            logger.error(
                "pdf.read.failed",
                extra={
                    "event": "pdf.read.failed",
                    "run_id": run_id,
                    "command": command,
                    "document_path": str(pdf_path),
                    "error_type": type(exc).__name__,
                    "error_domain": "pdf",
                },
            )
            raise PdfProcessingError(f"Could not read PDF text from '{pdf_path}'.") from exc

        if self._is_usable_text(direct_text):
            logger.info(
                "pdf.read.succeeded",
                extra={
                    "event": "pdf.read.succeeded",
                    "run_id": run_id,
                    "command": command,
                    "document_path": str(pdf_path),
                    "text_source": "direct",
                    "text_length": len(direct_text),
                },
            )
            return direct_text

        if not use_ocr_fallback:
            logger.warning(
                "pdf.read.unusable_without_ocr",
                extra={
                    "event": "pdf.read.unusable_without_ocr",
                    "run_id": run_id,
                    "command": command,
                    "document_path": str(pdf_path),
                    "text_source": "direct",
                    "text_length": len(direct_text),
                    "ocr_enabled": False,
                },
            )
            return direct_text

        logger.warning(
            "pdf.read.unusable_text_detected",
            extra={
                "event": "pdf.read.unusable_text_detected",
                "run_id": run_id,
                "command": command,
                "document_path": str(pdf_path),
                "text_source": "direct",
                "text_length": len(direct_text),
                "ocr_enabled": True,
            },
        )
        return self._ocr_service.extract_text(pdf_path, run_id=run_id, command=command)

    def _is_usable_text(self, value: str) -> bool:
        stripped = value.strip()
        if len(stripped) < self._min_text_length:
            return False

        alnum_chars = sum(char.isalnum() for char in stripped)
        return (alnum_chars / len(stripped)) >= self._min_alnum_ratio
