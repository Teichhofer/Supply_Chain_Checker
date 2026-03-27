"""Tests for YAML configuration loading."""

from __future__ import annotations

import pytest

from supply_chain_checker.config import ConfigurationError, load_config


def test_load_config_reads_logging_settings(tmp_path) -> None:
    config_file = tmp_path / "config.yaml"
    config_file.write_text(
        "paths:\n  logs_dir: app_logs\nlogging:\n  level: debug\n  file_name: runtime.log\n",
        encoding="utf-8",
    )

    config = load_config(config_file)

    assert config.paths.logs_dir.as_posix() == "app_logs"
    assert config.logging.level == "DEBUG"
    assert config.logging.file_name == "runtime.log"


def test_load_config_rejects_invalid_level(tmp_path) -> None:
    config_file = tmp_path / "config.yaml"
    config_file.write_text("logging:\n  level: verbose\n", encoding="utf-8")

    with pytest.raises(ConfigurationError):
        load_config(config_file)


def test_load_config_rejects_non_mapping_sections(tmp_path) -> None:
    config_file = tmp_path / "config.yaml"
    config_file.write_text("logging: []\n", encoding="utf-8")

    with pytest.raises(ConfigurationError):
        load_config(config_file)


def test_load_config_raises_for_missing_file(tmp_path) -> None:
    missing = tmp_path / "missing.yaml"

    with pytest.raises(ConfigurationError):
        load_config(missing)


def test_load_config_rejects_non_mapping_top_level(tmp_path) -> None:
    config_file = tmp_path / "config.yaml"
    config_file.write_text("- item\n", encoding="utf-8")

    with pytest.raises(ConfigurationError):
        load_config(config_file)
