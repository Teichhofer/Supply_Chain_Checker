"""Smoke tests for package main module."""

from __future__ import annotations

from runpy import run_module


def test_module_main_executes(monkeypatch, capsys) -> None:
    monkeypatch.setattr("sys.argv", ["supply_chain_checker", "assess", "--config", "config/config.yaml"])

    try:
        run_module("supply_chain_checker", run_name="__main__")
    except SystemExit as exc:
        assert exc.code == 0

    stdout = capsys.readouterr().out
    assert "Command='assess'" in stdout
