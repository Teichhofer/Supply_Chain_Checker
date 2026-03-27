"""CLI entry points for Supply Chain Checker."""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

from supply_chain_checker.config import load_config
from supply_chain_checker.logging_setup import setup_logging
from supply_chain_checker.run_context import create_run_context
from supply_chain_checker.scaffold import ensure_repository_layout
from supply_chain_checker.services.csv_service import create_run_csv_artifact
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
            artifact_path = create_run_csv_artifact(
                output_dir=config.paths.output_dir,
                command=args.command,
                run_context=run_context,
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
