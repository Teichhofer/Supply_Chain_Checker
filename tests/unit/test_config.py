"""Tests for YAML configuration loading."""

from __future__ import annotations

import pytest

from supply_chain_checker.config import ConfigurationError, load_config


def test_load_config_reads_full_settings(tmp_path) -> None:
    config_file = tmp_path / "config.yaml"
    config_file.write_text(
        "paths:\n"
        "  input_dir: data/in\n"
        "  output_dir: data/out\n"
        "  state_dir: data/state\n"
        "  logs_dir: app_logs\n"
        "logging:\n"
        "  level: debug\n"
        "  file_name: runtime.log\n"
        "llm:\n"
        "  provider: openai\n"
        "  model: gpt-4.1-mini\n"
        "  timeout_seconds: 15\n"
        "  max_retries: 3\n"
        "  temperature: 0.4\n"
        "prompts:\n"
        "  extraction: Extract products as JSON\n"
        "  assessment: Assess risk for {product_name}\n"
        "parameters:\n"
        "  use_ocr_fallback: false\n"
        "  max_products_per_document: 42\n"
        "  max_assessment_reason_words: 80\n",
        encoding="utf-8",
    )

    config = load_config(config_file)

    assert config.paths.input_dir.as_posix() == "data/in"
    assert config.paths.output_dir.as_posix() == "data/out"
    assert config.paths.state_dir.as_posix() == "data/state"
    assert config.paths.logs_dir.as_posix() == "app_logs"
    assert config.logging.level == "DEBUG"
    assert config.logging.file_name == "runtime.log"
    assert config.llm.provider == "openai"
    assert config.llm.model == "gpt-4.1-mini"
    assert config.llm.timeout_seconds == 15
    assert config.llm.max_retries == 3
    assert config.llm.temperature == 0.4
    assert config.prompts.extraction == "Extract products as JSON"
    assert config.prompts.assessment == "Assess risk for {product_name}"
    assert config.parameters.use_ocr_fallback is False
    assert config.parameters.max_products_per_document == 42
    assert config.parameters.max_assessment_reason_words == 80


def test_load_config_applies_defaults_for_optional_fields(tmp_path) -> None:
    config_file = tmp_path / "config.yaml"
    config_file.write_text(
        "llm:\n  provider: openai\n  model: gpt-4.1-mini\n",
        encoding="utf-8",
    )

    config = load_config(config_file)

    assert config.paths.logs_dir.as_posix() == "logs"
    assert config.paths.input_dir.as_posix() == "data/input"
    assert config.logging.level == "INFO"
    assert config.llm.timeout_seconds == 30
    assert config.prompts.extraction
    assert config.parameters.use_ocr_fallback is True


def test_load_config_rejects_invalid_level(tmp_path) -> None:
    config_file = tmp_path / "config.yaml"
    config_file.write_text(
        "llm:\n  provider: openai\n  model: gpt-4.1-mini\nlogging:\n  level: verbose\n",
        encoding="utf-8",
    )

    with pytest.raises(ConfigurationError, match="Invalid logging.level"):
        load_config(config_file)


def test_load_config_requires_llm_provider_and_model(tmp_path) -> None:
    config_file = tmp_path / "config.yaml"
    config_file.write_text("llm: {}\n", encoding="utf-8")

    with pytest.raises(ConfigurationError, match="Missing required field 'llm.provider'"):
        load_config(config_file)


def test_load_config_rejects_non_mapping_sections(tmp_path) -> None:
    config_file = tmp_path / "config.yaml"
    config_file.write_text("llm: []\n", encoding="utf-8")

    with pytest.raises(ConfigurationError):
        load_config(config_file)


def test_load_config_rejects_invalid_numeric_ranges(tmp_path) -> None:
    config_file = tmp_path / "config.yaml"
    config_file.write_text(
        "llm:\n  provider: openai\n  model: gpt-4.1-mini\n  temperature: 4\n",
        encoding="utf-8",
    )

    with pytest.raises(ConfigurationError, match="llm.temperature"):
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


def test_load_config_rejects_blank_required_string(tmp_path) -> None:
    config_file = tmp_path / "config.yaml"
    config_file.write_text(
        "llm:\n  provider: '   '\n  model: gpt-4.1-mini\n",
        encoding="utf-8",
    )

    with pytest.raises(ConfigurationError, match="llm.provider"):
        load_config(config_file)


def test_load_config_rejects_non_boolean_ocr_flag(tmp_path) -> None:
    config_file = tmp_path / "config.yaml"
    config_file.write_text(
        "llm:\n"
        "  provider: openai\n"
        "  model: gpt-4.1-mini\n"
        "parameters:\n"
        "  use_ocr_fallback: 1\n",
        encoding="utf-8",
    )

    with pytest.raises(ConfigurationError, match="parameters.use_ocr_fallback"):
        load_config(config_file)


def test_load_config_rejects_non_integer_timeout(tmp_path) -> None:
    config_file = tmp_path / "config.yaml"
    config_file.write_text(
        "llm:\n"
        "  provider: openai\n"
        "  model: gpt-4.1-mini\n"
        "  timeout_seconds: '30'\n",
        encoding="utf-8",
    )

    with pytest.raises(ConfigurationError, match="llm.timeout_seconds"):
        load_config(config_file)


def test_load_config_rejects_integer_below_minimum(tmp_path) -> None:
    config_file = tmp_path / "config.yaml"
    config_file.write_text(
        "llm:\n"
        "  provider: openai\n"
        "  model: gpt-4.1-mini\n"
        "  max_retries: -1\n",
        encoding="utf-8",
    )

    with pytest.raises(ConfigurationError, match="llm.max_retries"):
        load_config(config_file)


def test_load_config_rejects_non_numeric_temperature(tmp_path) -> None:
    config_file = tmp_path / "config.yaml"
    config_file.write_text(
        "llm:\n"
        "  provider: openai\n"
        "  model: gpt-4.1-mini\n"
        "  temperature: false\n",
        encoding="utf-8",
    )

    with pytest.raises(ConfigurationError, match="llm.temperature"):
        load_config(config_file)
