"""Smoke tests for package main module."""

from __future__ import annotations

from runpy import run_module


def test_module_main_executes(monkeypatch, capsys, tmp_path) -> None:
    config_file = tmp_path / "config.yaml"
    config_file.write_text(
        "paths:\n"
        "  logs_dir: logs\n"
        "logging:\n"
        "  level: INFO\n"
        "llm:\n"
        "  provider: openai\n"
        "  model: gpt-4.1-mini\n",
        encoding="utf-8",
    )

    monkeypatch.chdir(tmp_path)
    output_dir = tmp_path / "data" / "output"
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "extraction_20260327T120000Z_run123abc456.csv").write_text(
        "run_id,document_name\nrun123,invoice.pdf\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(
        "sys.argv", ["supply_chain_checker", "assess", "--config", str(config_file)]
    )

    try:
        run_module("supply_chain_checker", run_name="__main__")
    except SystemExit as exc:
        assert exc.code == 0

    stdout = capsys.readouterr().out
    assert "Command='assess'" in stdout
