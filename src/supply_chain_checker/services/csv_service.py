"""CSV input/output helper service."""

from __future__ import annotations

import csv
import logging
from pathlib import Path

from supply_chain_checker.run_context import RunContext

logger = logging.getLogger(__name__)


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
