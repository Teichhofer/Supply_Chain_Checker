"""CLI entry points for Supply Chain Checker."""

from __future__ import annotations

import argparse
from pathlib import Path

from supply_chain_checker.scaffold import ensure_repository_layout


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

    if args.command in {"extract", "assess"}:
        print(
            f"Supply Chain Checker scaffold is ready. "
            f"Command='{args.command}', config='{args.config}'."
        )

    return 0
