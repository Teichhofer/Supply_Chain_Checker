"""CSV input/output helper service."""

from __future__ import annotations

import csv
import logging
import re
from datetime import UTC, datetime
from pathlib import Path

from supply_chain_checker.models import ExtractedProduct, ExtractionStatus
from supply_chain_checker.run_context import RunContext
from supply_chain_checker.services.assessment_service import ProductAssessmentResult

logger = logging.getLogger(__name__)


class StorageIOError(Exception):
    """Raised when CSV artefacts cannot be written."""


_EXTRACTION_CSV_PATTERN = re.compile(
    r"^extraction_(?P<timestamp>\d{8}T\d{6}Z)_(?P<run_id>[A-Za-z0-9_-]+)\.csv$"
)


def _normalize_extraction_status(raw_status: str | None) -> ExtractionStatus:
    normalized = (raw_status or "uncertain").strip().lower()
    return "confirmed" if normalized == "confirmed" else "uncertain"


def build_run_csv_filename(*, command: str, run_context: RunContext) -> str:
    """Build a deterministic filename for run-bound CSV artefacts."""

    prefix_by_command = {
        "extract": "extraction",
        "assess": "assessment",
    }
    prefix = prefix_by_command.get(command, command)
    return f"{prefix}_{run_context.timestamp_compact}_{run_context.run_id}.csv"


def create_run_csv_artifact(*, output_dir: Path, command: str, run_context: RunContext) -> Path:
    """Create a per-run CSV artefact containing run metadata for traceability."""

    output_dir.mkdir(parents=True, exist_ok=True)
    artifact_path = output_dir / build_run_csv_filename(command=command, run_context=run_context)

    with artifact_path.open("w", encoding="utf-8", newline="") as csv_file:
        writer = csv.DictWriter(
            csv_file,
            fieldnames=("run_id", "run_timestamp_utc", "command", "status"),
        )
        writer.writeheader()
        writer.writerow(
            {
                "run_id": run_context.run_id,
                "run_timestamp_utc": run_context.started_at_utc.isoformat(),
                "command": command,
                "status": "placeholder",
            }
        )

    logger.info(
        "csv.artifact.created",
        extra={
            "event": "csv.artifact.created",
            "command": command,
            "run_id": run_context.run_id,
            "csv_path": str(artifact_path),
        },
    )

    return artifact_path


def select_latest_extraction_csv(*, output_dir: Path) -> Path:
    """Return the newest extraction CSV based on timestamp encoded in file names."""

    candidates: list[tuple[datetime, str, Path]] = []
    for candidate in output_dir.glob("extraction_*.csv"):
        match = _EXTRACTION_CSV_PATTERN.match(candidate.name)
        if match is None:
            continue
        timestamp = datetime.strptime(match.group("timestamp"), "%Y%m%dT%H%M%SZ").replace(
            tzinfo=UTC
        )
        candidates.append((timestamp, candidate.name, candidate))

    if not candidates:
        logger.error(
            "csv.extraction.latest.missing",
            extra={
                "event": "csv.extraction.latest.missing",
                "command": "assess",
                "output_dir": str(output_dir),
                "error_type": "StorageIOError",
            },
        )
        raise StorageIOError(f"No extraction CSV available in '{output_dir}'. Run 'extract' first.")

    latest_candidate = max(candidates, key=lambda entry: (entry[0], entry[1]))[2]
    logger.info(
        "csv.extraction.latest.selected",
        extra={
            "event": "csv.extraction.latest.selected",
            "command": "assess",
            "csv_path": str(latest_candidate),
        },
    )
    return latest_candidate


def write_extraction_products_csv(
    *,
    output_dir: Path,
    run_context: RunContext,
    products: list[ExtractedProduct],
) -> Path:
    """Write one extraction CSV artefact per run with required columns."""

    output_dir.mkdir(parents=True, exist_ok=True)
    csv_path = output_dir / build_run_csv_filename(command="extract", run_context=run_context)

    fieldnames = (
        "run_id",
        "document_name",
        "product_name",
        "quantity",
        "supplier",
        "manufacturer",
        "article_number",
        "extraction_status",
        "extraction_hint",
    )

    logger.info(
        "csv.write.started",
        extra={
            "event": "csv.write.started",
            "command": "extract",
            "run_id": run_context.run_id,
            "csv_path": str(csv_path),
            "row_count": len(products),
        },
    )

    try:
        with csv_path.open("w", encoding="utf-8", newline="") as csv_file:
            writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
            writer.writeheader()
            for product in products:
                writer.writerow(
                    {
                        "run_id": run_context.run_id,
                        "document_name": product.document_name,
                        "product_name": product.product_name,
                        "quantity": product.quantity,
                        "supplier": product.supplier,
                        "manufacturer": product.manufacturer or "",
                        "article_number": product.article_number or "",
                        "extraction_status": product.extraction_status,
                        "extraction_hint": product.extraction_hint or "",
                    }
                )
    except OSError as exc:
        logger.error(
            "csv.write.failed",
            extra={
                "event": "csv.write.failed",
                "command": "extract",
                "run_id": run_context.run_id,
                "csv_path": str(csv_path),
                "error_type": type(exc).__name__,
            },
        )
        raise StorageIOError(f"Could not write extraction CSV: {csv_path}") from exc

    logger.info(
        "csv.write.succeeded",
        extra={
            "event": "csv.write.succeeded",
            "command": "extract",
            "run_id": run_context.run_id,
            "csv_path": str(csv_path),
            "row_count": len(products),
        },
    )
    return csv_path


def read_extraction_products_csv(*, csv_path: Path) -> list[ExtractedProduct]:
    """Load extracted products from a previous extraction CSV artefact."""

    try:
        with csv_path.open("r", encoding="utf-8", newline="") as csv_file:
            reader = csv.DictReader(csv_file)
            products = [
                ExtractedProduct(
                    document_name=(row.get("document_name") or "").strip(),
                    product_name=(row.get("product_name") or "").strip(),
                    quantity=(row.get("quantity") or "").strip(),
                    supplier=(row.get("supplier") or "").strip(),
                    manufacturer=(row.get("manufacturer") or "").strip() or None,
                    article_number=(row.get("article_number") or "").strip() or None,
                    extraction_status=_normalize_extraction_status(row.get("extraction_status")),
                    extraction_hint=(row.get("extraction_hint") or "").strip() or None,
                )
                for row in reader
            ]
    except OSError as exc:
        raise StorageIOError(f"Could not read extraction CSV: {csv_path}") from exc

    return products


def write_assessment_results_csv(
    *,
    output_dir: Path,
    run_context: RunContext,
    results: list[ProductAssessmentResult],
) -> Path:
    """Persist per-product assessment outcomes including skipped rows."""

    output_dir.mkdir(parents=True, exist_ok=True)
    csv_path = output_dir / build_run_csv_filename(command="assess", run_context=run_context)
    fieldnames = (
        "run_id",
        "document_name",
        "product_name",
        "quantity",
        "supplier",
        "manufacturer",
        "article_number",
        "extraction_status",
        "extraction_hint",
        "bewertungsstatus",
        "skip_reason",
        "risikostufe",
        "preisänderung_prozent",
        "begründung",
        "assessment_hint",
        "error_type",
    )

    logger.info(
        "csv.write.started",
        extra={
            "event": "csv.write.started",
            "command": "assess",
            "run_id": run_context.run_id,
            "csv_path": str(csv_path),
            "row_count": len(results),
        },
    )

    try:
        with csv_path.open("w", encoding="utf-8", newline="") as csv_file:
            writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
            writer.writeheader()
            for result in results:
                writer.writerow(
                    {
                        "run_id": run_context.run_id,
                        "document_name": result.product.document_name,
                        "product_name": result.product.product_name,
                        "quantity": result.product.quantity,
                        "supplier": result.product.supplier,
                        "manufacturer": result.product.manufacturer or "",
                        "article_number": result.product.article_number or "",
                        "extraction_status": result.product.extraction_status,
                        "extraction_hint": result.product.extraction_hint or "",
                        "bewertungsstatus": result.assessment_status,
                        "skip_reason": result.skip_reason or "",
                        "risikostufe": (
                            result.normalized_assessment.risk_level
                            if result.normalized_assessment is not None
                            else ""
                        ),
                        "preisänderung_prozent": (
                            result.normalized_assessment.price_change_percent
                            if result.normalized_assessment is not None
                            else ""
                        ),
                        "begründung": (
                            result.normalized_assessment.reason
                            if result.normalized_assessment is not None
                            else ""
                        ),
                        "assessment_hint": result.assessment_hint or "",
                        "error_type": result.error_type or "",
                    }
                )
    except OSError as exc:
        logger.error(
            "csv.write.failed",
            extra={
                "event": "csv.write.failed",
                "command": "assess",
                "run_id": run_context.run_id,
                "csv_path": str(csv_path),
                "error_type": type(exc).__name__,
            },
        )
        raise StorageIOError(f"Could not write assessment CSV: {csv_path}") from exc

    logger.info(
        "csv.write.succeeded",
        extra={
            "event": "csv.write.succeeded",
            "command": "assess",
            "run_id": run_context.run_id,
            "csv_path": str(csv_path),
            "row_count": len(results),
        },
    )

    return csv_path
