"""Tests for CLI entry points."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from supply_chain_checker import cli

_MINIMAL_CONFIG = """
paths:
  logs_dir: logs
logging:
  level: INFO
  file_name: app.log
llm:
  provider: openai
  model: gpt-4.1-mini
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

    run_id_match = re.search(r"run_id='([a-f0-9]{12})'", stdout)
    assert run_id_match is not None
    run_id = run_id_match.group(1)

    output_files = list((tmp_path / "data" / "output").glob("extraction_*.csv"))
    assert len(output_files) == 1

    artifact_content = output_files[0].read_text(encoding="utf-8")
    assert "run_id" in artifact_content
    assert run_id in artifact_content


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


def test_main_creates_distinct_csv_artifacts_per_command(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.chdir(tmp_path)

    config_file = tmp_path / "config.yaml"
    config_file.write_text(_MINIMAL_CONFIG, encoding="utf-8")

    monkeypatch.setattr(
        "sys.argv", ["supply-chain-checker", "extract", "--config", str(config_file)]
    )
    assert cli.main() == 0

    monkeypatch.setattr(
        "sys.argv", ["supply-chain-checker", "assess", "--config", str(config_file)]
    )
    assert cli.main() == 0

    extract_files = list((tmp_path / "data" / "output").glob("extraction_*.csv"))
    assess_files = list((tmp_path / "data" / "output").glob("assessment_*.csv"))

    assert len(extract_files) == 1
    assert len(assess_files) == 1
    assert extract_files[0].name != assess_files[0].name
