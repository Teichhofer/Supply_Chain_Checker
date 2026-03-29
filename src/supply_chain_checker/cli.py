"""CLI entry points for Supply Chain Checker."""

from __future__ import annotations

import argparse
import logging
import os
import shutil
import stat
from pathlib import Path

from supply_chain_checker.config import AppConfig, load_config
from supply_chain_checker.logging_setup import setup_logging
from supply_chain_checker.models import ExtractedProduct
from supply_chain_checker.run_context import RunContext, create_run_context
from supply_chain_checker.scaffold import ensure_repository_layout
from supply_chain_checker.services.assessment_service import (
    AssessmentService,
    ProductAssessmentResult,
)
from supply_chain_checker.services.csv_service import (
    read_extraction_products_csv,
    select_latest_extraction_csv,
    write_assessment_results_csv,
    write_extraction_products_csv,
)
from supply_chain_checker.services.extraction_service import (
    ExtractionService,
    LlmClientError,
    ParsingError,
)
from supply_chain_checker.services.llm.base import LlmConfigurationError
from supply_chain_checker.services.llm.openai_client import OpenAIAdapterConfig, OpenAIClient
from supply_chain_checker.services.ocr_service import OcrProcessingError, OcrService
from supply_chain_checker.services.pdf_reader import (
    PdfProcessingError,
    PdfReader,
    extract_text_with_pypdf,
)
from supply_chain_checker.services.status_service import StatusService

logger = logging.getLogger(__name__)
DEFAULT_CONFIG_PATH = Path("config/config.yaml")
STATUS_FILE_NAME = "processed_files.json"


def _load_secrets_env(config_path: str | Path) -> None:
    """Load environment variables from a sibling secrets.env file when present."""

    secrets_path = Path(config_path).resolve().parent / "secrets.env"
    if not secrets_path.exists():
        logger.info(
            "secrets.load.skipped",
            extra={
                "event": "secrets.load.skipped",
                "secrets_path": str(secrets_path),
                "reason": "file_not_found",
            },
        )
        return

    loaded_keys = 0
    for raw_line in secrets_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue

        if line.startswith("export "):
            line = line[len("export ") :].strip()

        if "=" not in line:
            logger.warning(
                "secrets.load.entry.invalid",
                extra={
                    "event": "secrets.load.entry.invalid",
                    "secrets_path": str(secrets_path),
                    "entry": raw_line,
                },
            )
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if not key:
            logger.warning(
                "secrets.load.entry.invalid",
                extra={
                    "event": "secrets.load.entry.invalid",
                    "secrets_path": str(secrets_path),
                    "entry": raw_line,
                },
            )
            continue

        os.environ[key] = value
        loaded_keys += 1

    logger.info(
        "secrets.load.succeeded",
        extra={
            "event": "secrets.load.succeeded",
            "secrets_path": str(secrets_path),
            "loaded_keys": loaded_keys,
        },
    )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="supply-chain-checker")
    subparsers = parser.add_subparsers(dest="command", required=True)

    extract = subparsers.add_parser("extract", help="Extract products from PDFs")
    extract.add_argument(
        "--config",
        default=str(DEFAULT_CONFIG_PATH),
        help=f"Path to YAML config file (default: {DEFAULT_CONFIG_PATH})",
    )

    assess = subparsers.add_parser("assess", help="Assess extracted products")
    assess.add_argument(
        "--config",
        default=str(DEFAULT_CONFIG_PATH),
        help=f"Path to YAML config file (default: {DEFAULT_CONFIG_PATH})",
    )

    run = subparsers.add_parser(
        "run",
        help="Run extraction and assessment sequentially",
    )
    run.add_argument(
        "--config",
        default=str(DEFAULT_CONFIG_PATH),
        help=f"Path to YAML config file (default: {DEFAULT_CONFIG_PATH})",
    )

    clear = subparsers.add_parser(
        "clear",
        help="Delete logs, output, and state directories",
    )
    clear.add_argument(
        "--config",
        default=str(DEFAULT_CONFIG_PATH),
        help=f"Path to YAML config file (default: {DEFAULT_CONFIG_PATH})",
    )

    return parser


def main() -> int:
    """Run CLI and return an exit code."""

    ensure_repository_layout(base_dir=Path.cwd())

    parser = _build_parser()
    args = parser.parse_args()

    _load_secrets_env(args.config)
    config = load_config(args.config)

    if args.command == "clear":
        _run_clear_command(config=config)
        return 0

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
        if args.command in {"extract", "assess", "run"}:
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
            artifact_paths: list[Path] = []
            if args.command in {"extract", "run"}:
                artifact_paths.append(
                    _run_extract_command(
                        config=config,
                        run_id=run_context.run_id,
                        run_context=run_context,
                        status_service=status_service,
                    )
                )
            if args.command in {"assess", "run"}:
                artifact_paths.append(_run_assess_command(config=config, run_context=run_context))

            for artifact_path in artifact_paths:
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


def _build_extraction_service(*, config: AppConfig) -> ExtractionService:
    return ExtractionService(
        pdf_reader=PdfReader(
            direct_extractor=extract_text_with_pypdf,
            ocr_service=OcrService(engine=_run_ocr_placeholder),
        ),
        llm_client=OpenAIClient(
            config=OpenAIAdapterConfig(
                model=config.llm.model,
                timeout_seconds=config.llm.timeout_seconds,
                max_retries=config.llm.max_retries,
                temperature=config.llm.temperature,
            ),
        ),
    )


def _run_clear_command(*, config: AppConfig) -> None:
    status_files_to_clear = [
        config.paths.state_dir / STATUS_FILE_NAME,
        Path(STATUS_FILE_NAME),
    ]
    for status_file in status_files_to_clear:
        if status_file.exists() and status_file.is_file():
            status_file.unlink()

    directories_to_clear = [
        config.paths.logs_dir,
        config.paths.output_dir,
        config.paths.state_dir,
    ]
    for directory in directories_to_clear:
        if directory.exists():
            shutil.rmtree(directory, onerror=_handle_remove_readonly)
        directory.mkdir(parents=True, exist_ok=True)


def _handle_remove_readonly(function: object, path: str, _: BaseException) -> None:
    path_obj = Path(path)
    try:
        path_obj.chmod(stat.S_IWRITE)
    except OSError:
        return

    try:
        function(path_obj)
    except OSError:
        return


def _run_extract_command(
    *,
    config: AppConfig,
    run_id: str,
    run_context: RunContext,
    status_service: StatusService,
) -> Path:
    extraction_service = _build_extraction_service(config=config)
    extracted_products: list[ExtractedProduct] = []
    attempted_documents = 0

    for pdf_path in status_service.select_unprocessed_pdfs(config.paths.input_dir):
        attempted_documents += 1
        logger.info(
            "extraction.document.started",
            extra={
                "event": "extraction.document.started",
                "command": "extract",
                "run_id": run_id,
                "document_path": str(pdf_path),
            },
        )
        try:
            document_products = extraction_service.extract_products_from_document(
                pdf_path=pdf_path,
                extraction_prompt_template=config.prompts.extraction,
                max_products_per_document=config.parameters.max_products_per_document,
                use_ocr_fallback=config.parameters.use_ocr_fallback,
                run_id=run_id,
                command="extract",
            )
            extracted_products.extend(document_products)
            logger.info(
                "extraction.document.succeeded",
                extra={
                    "event": "extraction.document.succeeded",
                    "command": "extract",
                    "run_id": run_id,
                    "document_path": str(pdf_path),
                    "product_count": len(document_products),
                },
            )
            status_service.mark_processed_and_persist(pdf_path.name)
        except LlmConfigurationError as exc:
            logger.error(
                "extraction.command.failed",
                extra={
                    "event": "extraction.command.failed",
                    "command": "extract",
                    "run_id": run_id,
                    "document_path": str(pdf_path),
                    "error_type": type(exc).__name__,
                    "error_message": str(exc),
                },
                exc_info=exc,
            )
            raise
        except (PdfProcessingError, OcrProcessingError, LlmClientError, ParsingError) as exc:
            logger.warning(
                "extraction.document.failed",
                extra={
                    "event": "extraction.document.failed",
                    "command": "extract",
                    "run_id": run_id,
                    "document_path": str(pdf_path),
                    "error_type": type(exc).__name__,
                    "error_message": str(exc),
                },
                exc_info=exc,
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

    logger.info(
        "extraction.command.summary",
        extra={
            "event": "extraction.command.summary",
            "command": "extract",
            "run_id": run_id,
            "document_count": attempted_documents,
            "product_count": len(extracted_products),
        },
    )

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
    products = read_extraction_products_csv(csv_path=latest_extraction_csv)
    assessment_service = _build_assessment_service(
        config=config,
        max_reason_words=config.parameters.max_assessment_reason_words,
    )
    results = assessment_service.assess_products(
        products=products,
        assessment_prompt_template=config.prompts.assessment,
        run_id=run_context.run_id,
        command="assess",
    )
    _print_assessment_console_results(results=results)
    return write_assessment_results_csv(
        output_dir=config.paths.output_dir,
        run_context=run_context,
        results=results,
    )


def _print_assessment_console_results(*, results: list[ProductAssessmentResult]) -> None:
    """Print an operational summary with one line per assessed product."""

    print("Assessment results (Produkt, Lieferant, Risikostufe, Preisänderung, Status):")
    if not results:
        print("- keine Produkte vorhanden")
        return

    for result in results:
        risk_level = (
            str(result.normalized_assessment.risk_level)
            if result.normalized_assessment is not None
            else "-"
        )
        price_change = (
            f"{result.normalized_assessment.price_change_percent:.2f}%"
            if result.normalized_assessment is not None
            else "-"
        )
        status_detail = (
            result.skip_reason
            or result.error_type
            or result.assessment_hint
            or "OK"
        )
        print(
            f"- Produktname: {result.product.product_name} | "
            f"Lieferant: {result.product.supplier} | "
            f"Risikostufe: {risk_level} | "
            f"Preisänderung: {price_change} | "
            f"Status: {result.assessment_status} ({status_detail})"
        )
def _run_ocr_placeholder(pdf_path: Path) -> str:
    raise RuntimeError(f"OCR backend is not configured for '{pdf_path.name}'.")


def _read_document_text_placeholder(pdf_path: Path) -> str:
    raise RuntimeError(f"PDF text reader is not configured for '{pdf_path.name}'.")


def _invoke_extraction_llm_placeholder(_prompt: str) -> str:
    raise RuntimeError("LLM provider invocation is not configured.")


def _build_assessment_service(*, config: AppConfig, max_reason_words: int) -> AssessmentService:
    return AssessmentService(
        llm_client=OpenAIClient(
            config=OpenAIAdapterConfig(
                model=config.llm.model,
                timeout_seconds=config.llm.timeout_seconds,
                max_retries=config.llm.max_retries,
                temperature=config.llm.temperature,
            ),
        ),
        max_reason_words=max_reason_words,
    )


def _invoke_assessment_llm_placeholder(_prompt: str) -> str:
    raise RuntimeError("LLM provider invocation is not configured.")
