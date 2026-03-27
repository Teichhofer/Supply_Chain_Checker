"""Tests for CLI entry points."""

from __future__ import annotations

from pathlib import Path

from supply_chain_checker import cli


def test_build_parser_supports_extract_and_assess() -> None:
    parser = cli._build_parser()

    extract_args = parser.parse_args(["extract", "--config", "config/config.yaml"])
    assess_args = parser.parse_args(["assess", "--config", "config/config.yaml"])

    assert extract_args.command == "extract"
    assert assess_args.command == "assess"


def test_main_ensures_layout_and_returns_success(monkeypatch, tmp_path: Path, capsys) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        "sys.argv", ["supply-chain-checker", "extract", "--config", "config/config.yaml"]
    )

    exit_code = cli.main()

    assert exit_code == 0
    assert (tmp_path / "data" / "input").exists()
    assert (tmp_path / "tests" / "unit").exists()

    stdout = capsys.readouterr().out
    assert "scaffold is ready" in stdout
