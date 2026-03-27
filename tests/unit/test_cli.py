"""Tests for CLI entry points."""

from __future__ import annotations

from pathlib import Path

import pytest

from supply_chain_checker import cli

_MINIMAL_CONFIG = """
paths:
  logs_dir: logs
logging:
  level: INFO
  file_name: app.log
"""


def test_build_parser_supports_extract_and_assess() -> None:
    parser = cli._build_parser()

    extract_args = parser.parse_args(["extract", "--config", "config/config.yaml"])
    assess_args = parser.parse_args(["assess", "--config", "config/config.yaml"])

    assert extract_args.command == "extract"
    assert assess_args.command == "assess"


def test_main_ensures_layout_and_returns_success(monkeypatch, tmp_path: Path, capsys) -> None:
    monkeypatch.chdir(tmp_path)

    config_file = tmp_path / "config.yaml"
    config_file.write_text(_MINIMAL_CONFIG, encoding="utf-8")

    monkeypatch.setattr(
        "sys.argv", ["supply-chain-checker", "extract", "--config", str(config_file)]
    )

    exit_code = cli.main()

    assert exit_code == 0
    assert (tmp_path / "data" / "input").exists()
    assert (tmp_path / "tests" / "unit").exists()
    assert (tmp_path / "logs" / "app.log").exists()

    stdout = capsys.readouterr().out
    assert "scaffold is ready" in stdout
    assert "run_id='" in stdout


def test_main_logs_run_finished_even_when_command_raises(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.chdir(tmp_path)

    config_file = tmp_path / "config.yaml"
    config_file.write_text(_MINIMAL_CONFIG, encoding="utf-8")

    monkeypatch.setattr(
        "sys.argv", ["supply-chain-checker", "extract", "--config", str(config_file)]
    )

    def _raise_runtime_error(*_args: object, **_kwargs: object) -> None:
        raise RuntimeError

    monkeypatch.setattr("builtins.print", _raise_runtime_error)

    with pytest.raises(RuntimeError):
        cli.main()

    log_content = (tmp_path / "logs" / "app.log").read_text(encoding="utf-8")
    assert "run.started" in log_content
    assert "run.finished" in log_content
