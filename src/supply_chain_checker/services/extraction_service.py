"""Product extraction orchestration service."""

from __future__ import annotations

import logging
from collections.abc import Callable
from pathlib import Path

from supply_chain_checker.models import ExtractedProduct
from supply_chain_checker.parsers import ParsingError, parse_extraction_response
from supply_chain_checker.services.llm import (
    LlmGateway,
    LlmRequestContext,
    build_extraction_prompt,
)
from supply_chain_checker.services.llm.base import LlmClientError
from supply_chain_checker.services.ocr_service import OcrProcessingError
from supply_chain_checker.services.pdf_reader import PdfProcessingError, PdfReader

logger = logging.getLogger(__name__)


class ExtractionService:
    """Coordinate document text loading and LLM-based product extraction."""

    def __init__(
        self,
        *,
        pdf_reader: PdfReader,
        llm_client: LlmGateway,
        prompt_builder: Callable[..., str] = build_extraction_prompt,
        response_parser: Callable[..., list[ExtractedProduct]] = parse_extraction_response,
    ) -> None:
        self._pdf_reader = pdf_reader
        self._llm_client = llm_client
        self._prompt_builder = prompt_builder
        self._response_parser = response_parser

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
                    "error_message": str(exc),
                },
                exc_info=exc,
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

    def extract_products_from_document(
        self,
        *,
        pdf_path: Path,
        extraction_prompt_template: str,
        max_products_per_document: int,
        use_ocr_fallback: bool,
        run_id: str | None = None,
        command: str = "extract",
    ) -> list[ExtractedProduct]:
        """Extract products from a PDF using only the LLM interface contract."""

        text = self.load_document_text(
            pdf_path,
            use_ocr_fallback=use_ocr_fallback,
            run_id=run_id,
            command=command,
        )
        prompt = self._prompt_builder(
            template=extraction_prompt_template,
            document_text=text,
            document_name=pdf_path.name,
            max_products_per_document=max_products_per_document,
        )
        llm_response = self._llm_client.extract_products(
            prompt=prompt,
            context=LlmRequestContext(run_id=run_id, command=command),
        )
        try:
            products = self._response_parser(response_text=llm_response, document_name=pdf_path.name)
        except ParsingError as exc:
            logger.warning(
                "extraction.response.parse.failed",
                extra={
                    "event": "extraction.response.parse.failed",
                    "run_id": run_id,
                    "command": command,
                    "document_path": str(pdf_path),
                    "error_type": type(exc).__name__,
                    "error_message": str(exc),
                    "response_length": len(llm_response),
                },
                exc_info=exc,
            )
            raise

        logger.info(
            "extraction.products.parsed",
            extra={
                "event": "extraction.products.parsed",
                "run_id": run_id,
                "command": command,
                "document_path": str(pdf_path),
                "product_count": len(products),
            },
        )
        return products


__all__ = ["ExtractionService", "LlmClientError", "ParsingError"]
