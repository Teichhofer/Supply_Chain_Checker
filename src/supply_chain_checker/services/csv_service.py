"""CSV input/output helper service."""

from __future__ import annotations

import csv
import logging
from pathlib import Path
from typing import Iterable

from supply_chain_checker.run_context import RunContext

logger = logging.getLogger(__name__)


def build_extraction_csv_path(*, output_dir: Path, run_context: RunContext) -> Path:
    """Build a unique extraction CSV file path for one run."""

    return output_dir / f"extraction_{run_context.artifact_suffix}.csv"


def build_assessment_csv_path(*, output_dir: Path, run_context: RunContext) -> Path:
    """Build a unique assessment CSV file path for one run."""

    return output_dir / f"assessment_{run_context.artifact_suffix}.csv"


def write_csv_rows(
    *,
    output_path: Path,
    rows: Iterable[dict[str, str]],
    run_context: RunContext,
) -> Path:
    """Write rows to CSV while injecting run metadata for correlation."""

    normalized_rows = list(rows)
    run_columns = ("run_id", "run_timestamp")

    if normalized_rows:
        data_fieldnames = sorted({key for row in normalized_rows for key in row})
    else:
        data_fieldnames = []
    fieldnames = [*run_columns, *data_fieldnames]

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()

        for row in normalized_rows:
            writer.writerow(
                {
                    "run_id": run_context.run_id,
                    "run_timestamp": run_context.started_at_iso,
                    **row,
                }
            )

    logger.info(
        "csv.write.succeeded",
        extra={
            "event": "csv.write.succeeded",
            "run_id": run_context.run_id,
            "output_path": str(output_path),
            "row_count": len(normalized_rows),
        },
    )
    return output_path
