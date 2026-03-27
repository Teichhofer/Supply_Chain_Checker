"""CSV input/output helper service."""

from __future__ import annotations

import csv
import logging
from pathlib import Path

from supply_chain_checker.models import ExtractedProduct
from supply_chain_checker.run_context import RunContext

logger = logging.getLogger(__name__)


class StorageIOError(Exception):
    """Raised when CSV artefacts cannot be written."""


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
