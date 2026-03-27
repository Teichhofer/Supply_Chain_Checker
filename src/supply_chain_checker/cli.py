"""CLI entry points for Supply Chain Checker."""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

from supply_chain_checker.config import AppConfig, load_config
from supply_chain_checker.logging_setup import setup_logging
from supply_chain_checker.models import ExtractedProduct
from supply_chain_checker.run_context import RunContext, create_run_context
from supply_chain_checker.scaffold import ensure_repository_layout
from supply_chain_checker.services.csv_service import (
    create_run_csv_artifact,
    select_latest_extraction_csv,
    write_extraction_products_csv,
)
from supply_chain_checker.services.extraction_service import (
    ExtractionService,
    LlmClientError,
    ParsingError,
)
from supply_chain_checker.services.llm.openai_client import OpenAIExtractionClient
from supply_chain_checker.services.ocr_service import OcrProcessingError, OcrService
from supply_chain_checker.services.pdf_reader import PdfProcessingError, PdfReader
from supply_chain_checker.services.status_service import StatusService

logger = logging.getLogger(__name__)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="supply-chain-checker")
    subparsers = parser.add_subparsers(dest="command", required=True)

    extract = subparsers.add_parser("extract", help="Extract products from PDFs")
    extract.add_argument("--config", required=True, help="Path to YAML config file")

    assess = subparsers.add_parser("assess", help="Assess extracted products")
    assess.add_argument("--config", required=True, help="Path to YAML config file")

    return parser


def main() -> int:
    """Run CLI and return an exit code."""

    ensure_repository_layout(base_dir=Path.cwd())

    parser = _build_parser()
    args = parser.parse_args()

    config = load_config(args.config)
    run_context = create_run_context()
    log_file_path = setup_logging(
        logs_dir=config.paths.logs_dir,
        level=config.logging.level,
        run_id=run_context.run_id,
        file_name=config.logging.file_name,
    )

    logger.info(
        "run.started",
        extra={"event": "run.started", "command": args.command, "run_id": run_context.run_id},
    )

    status_service = StatusService(status_file_path=config.paths.state_dir / "processed_files.json")
    status_service.load(on_corrupt_file=config.parameters.on_corrupt_status_file)

    try:
        if args.command in {"extract", "assess"}:
            logger.info(
                "command.received",
                extra={
                    "event": "command.received",
                    "command": args.command,
                    "run_id": run_context.run_id,
                },
            )
            print(
                f"Supply Chain Checker scaffold is ready. "
                f"Command='{args.command}', config='{args.config}', run_id='{run_context.run_id}'."
            )
            artifact_path = (
                _run_extract_command(
                    config=config,
                    run_id=run_context.run_id,
                    run_context=run_context,
                    status_service=status_service,
                )
                if args.command == "extract"
                else _run_assess_command(config=config, run_context=run_context)
            )
            logger.info(
                "run.artifact.created",
                extra={
                    "event": "run.artifact.created",
                    "command": args.command,
                    "run_id": run_context.run_id,
                    "artifact_path": str(artifact_path),
                },
            )

            if args.command == "assess":
                for pdf_path in status_service.select_unprocessed_pdfs(config.paths.input_dir):
                    status_service.mark_processed(pdf_path.name)

            status_service.persist()
    finally:
        logger.info(
            "run.finished",
            extra={"event": "run.finished", "command": args.command, "run_id": run_context.run_id},
        )
        logger.info(
            "logging.file",
            extra={
                "event": "logging.file",
                "run_id": run_context.run_id,
                "log_file_path": str(log_file_path),
            },
        )

    return 0


def _build_extraction_service() -> ExtractionService:
    return ExtractionService(
        pdf_reader=PdfReader(
            direct_extractor=_read_document_text_placeholder,
            ocr_service=OcrService(engine=_run_ocr_placeholder),
        ),
        llm_client=OpenAIExtractionClient(invoker=_invoke_extraction_llm_placeholder),
    )


def _run_extract_command(
    *,
    config: AppConfig,
    run_id: str,
    run_context: RunContext,
    status_service: StatusService,
) -> Path:
    extraction_service = _build_extraction_service()
    extracted_products: list[ExtractedProduct] = []

    for pdf_path in status_service.select_unprocessed_pdfs(config.paths.input_dir):
        try:
            extracted_products.extend(
                extraction_service.extract_products_from_document(
                    pdf_path=pdf_path,
                    extraction_prompt_template=config.prompts.extraction,
                    max_products_per_document=config.parameters.max_products_per_document,
                    use_ocr_fallback=config.parameters.use_ocr_fallback,
                    run_id=run_id,
                    command="extract",
                )
            )
        except (PdfProcessingError, OcrProcessingError, LlmClientError, ParsingError) as exc:
            logger.warning(
                "extraction.document.failed",
                extra={
                    "event": "extraction.document.failed",
                    "command": "extract",
                    "run_id": run_id,
                    "document_path": str(pdf_path),
                    "error_type": type(exc).__name__,
                },
            )
            extracted_products.append(
                ExtractedProduct(
                    document_name=pdf_path.name,
                    product_name="UNKNOWN",
                    quantity="UNKNOWN",
                    supplier="UNKNOWN",
                    extraction_status="uncertain",
                    extraction_hint=f"Document processing failed: {type(exc).__name__}",
                )
            )
        finally:
            status_service.mark_processed(pdf_path.name)

    if not extracted_products:
        extracted_products.append(
            ExtractedProduct(
                document_name="",
                product_name="NO_PRODUCTS_FOUND",
                quantity="",
                supplier="",
                extraction_status="uncertain",
                extraction_hint="No unprocessed PDF files available for extraction.",
            )
        )

    return write_extraction_products_csv(
        output_dir=config.paths.output_dir,
        run_context=run_context,
        products=extracted_products,
    )


def _run_assess_command(*, config: AppConfig, run_context: RunContext) -> Path:
    latest_extraction_csv = select_latest_extraction_csv(output_dir=config.paths.output_dir)
    logger.info(
        "assessment.input.selected",
        extra={
            "event": "assessment.input.selected",
            "command": "assess",
            "run_id": run_context.run_id,
            "csv_path": str(latest_extraction_csv),
        },
    )
    return create_run_csv_artifact(
        output_dir=config.paths.output_dir,
        command="assess",
        run_context=run_context,
    )


def _read_document_text_placeholder(pdf_path: Path) -> str:
    return pdf_path.read_text(encoding="utf-8")


def _run_ocr_placeholder(pdf_path: Path) -> str:
    raise RuntimeError(f"OCR backend is not configured for '{pdf_path.name}'.")


def _invoke_extraction_llm_placeholder(_prompt: str) -> str:
    raise RuntimeError("LLM provider invocation is not configured.")
