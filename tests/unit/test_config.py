"""Tests for YAML configuration loading."""

from __future__ import annotations

from copy import deepcopy

import pytest
import yaml

from supply_chain_checker.config import ConfigurationError, load_config


def _base_config() -> dict[str, object]:
    return {
        "paths": {
            "input_dir": "data/input",
            "output_dir": "data/output",
            "state_dir": "data/state",
            "logs_dir": "logs",
        },
        "logging": {"level": "INFO", "file_name": "app.log"},
        "llm": {
            "provider": "openai",
            "model": "gpt-4.1-mini",
            "timeout_seconds": 30,
            "max_retries": 2,
            "temperature": 0.0,
        },
        "prompts": {
            "extraction": "Extract products as JSON",
            "assessment": "Assess risk for {product_name}",
        },
        "parameters": {
            "use_ocr_fallback": True,
            "max_products_per_document": 100,
            "max_assessment_reason_words": 100,
            "on_corrupt_status_file": "abort",
        },
    }


def _write_config(tmp_path, payload: dict[str, object]) -> object:
    config_file = tmp_path / "config.yaml"
    config_file.write_text(yaml.safe_dump(payload), encoding="utf-8")
    return config_file


def test_load_config_reads_full_settings(tmp_path) -> None:
    payload = _base_config()
    payload["paths"] = {
        "input_dir": "data/in",
        "output_dir": "data/out",
        "state_dir": "data/state",
        "logs_dir": "app_logs",
    }
    payload["logging"] = {"level": "debug", "file_name": "runtime.log"}
    payload["llm"] = {
        "provider": "openai",
        "model": "gpt-4.1-mini",
        "timeout_seconds": 15,
        "max_retries": 3,
        "temperature": 0.4,
    }
    payload["prompts"] = {
        "extraction": "Extract products as JSON",
        "assessment": "Assess risk for {product_name}",
    }
    payload["parameters"] = {
        "use_ocr_fallback": False,
        "max_products_per_document": 42,
        "max_assessment_reason_words": 80,
        "on_corrupt_status_file": "abort",
    }
    config_file = _write_config(tmp_path, payload)

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
    assert config.parameters.on_corrupt_status_file == "abort"


def test_load_config_requires_all_required_sections_and_fields(tmp_path) -> None:
    config_file = tmp_path / "config.yaml"
    config_file.write_text("llm:\n  provider: openai\n  model: gpt-4.1-mini\n", encoding="utf-8")

    with pytest.raises(ConfigurationError, match="Missing required field"):
        load_config(config_file)


def test_load_config_accepts_status_fallback_strategy(tmp_path) -> None:
    payload = _base_config()
    payload["parameters"]["on_corrupt_status_file"] = "fallback_empty"  # type: ignore[index]
    config_file = _write_config(tmp_path, payload)

    config = load_config(config_file)
    assert config.parameters.on_corrupt_status_file == "fallback_empty"


def test_load_config_rejects_invalid_level(tmp_path) -> None:
    payload = _base_config()
    payload["logging"]["level"] = "verbose"  # type: ignore[index]
    config_file = _write_config(tmp_path, payload)

    with pytest.raises(ConfigurationError, match="Invalid logging.level"):
        load_config(config_file)


def test_load_config_requires_llm_provider_and_model(tmp_path) -> None:
    payload = _base_config()
    del payload["llm"]["provider"]  # type: ignore[index]
    config_file = _write_config(tmp_path, payload)

    with pytest.raises(ConfigurationError, match="Missing required field"):
        load_config(config_file)


def test_load_config_rejects_unknown_root_field(tmp_path) -> None:
    payload = _base_config()
    payload["feature_flags"] = {"demo": True}
    config_file = _write_config(tmp_path, payload)

    with pytest.raises(ConfigurationError, match="Unknown field"):
        load_config(config_file)


def test_load_config_rejects_non_mapping_sections(tmp_path) -> None:
    payload = _base_config()
    payload["llm"] = []  # type: ignore[assignment]
    config_file = _write_config(tmp_path, payload)

    with pytest.raises(ConfigurationError, match="Section 'llm' must be a mapping"):
        load_config(config_file)


def test_load_config_rejects_invalid_numeric_ranges(tmp_path) -> None:
    payload = _base_config()
    payload["llm"]["temperature"] = 4  # type: ignore[index]
    config_file = _write_config(tmp_path, payload)

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
    payload = _base_config()
    payload["llm"]["provider"] = "   "  # type: ignore[index]
    config_file = _write_config(tmp_path, payload)

    with pytest.raises(ConfigurationError, match="llm.provider"):
        load_config(config_file)


def test_load_config_rejects_non_boolean_ocr_flag(tmp_path) -> None:
    payload = _base_config()
    payload["parameters"]["use_ocr_fallback"] = 1  # type: ignore[index]
    config_file = _write_config(tmp_path, payload)

    with pytest.raises(ConfigurationError, match="parameters.use_ocr_fallback"):
        load_config(config_file)


def test_load_config_rejects_non_integer_timeout(tmp_path) -> None:
    payload = _base_config()
    payload["llm"]["timeout_seconds"] = "30"  # type: ignore[index]
    config_file = _write_config(tmp_path, payload)

    with pytest.raises(ConfigurationError, match="llm.timeout_seconds"):
        load_config(config_file)


def test_load_config_rejects_integer_below_minimum(tmp_path) -> None:
    payload = _base_config()
    payload["llm"]["max_retries"] = -1  # type: ignore[index]
    config_file = _write_config(tmp_path, payload)

    with pytest.raises(ConfigurationError, match="llm.max_retries"):
        load_config(config_file)


def test_load_config_rejects_non_numeric_temperature(tmp_path) -> None:
    payload = _base_config()
    payload["llm"]["temperature"] = False  # type: ignore[index]
    config_file = _write_config(tmp_path, payload)

    with pytest.raises(ConfigurationError, match="llm.temperature"):
        load_config(config_file)


def test_load_config_rejects_unknown_status_corruption_strategy(tmp_path) -> None:
    payload = _base_config()
    payload["parameters"]["on_corrupt_status_file"] = "continue"  # type: ignore[index]
    config_file = _write_config(tmp_path, payload)

    with pytest.raises(ConfigurationError, match="parameters.on_corrupt_status_file"):
        load_config(config_file)


@pytest.mark.parametrize("temperature", ["nan", "inf", "-inf"])
def test_load_config_rejects_non_finite_temperature(tmp_path, temperature: str) -> None:
    payload = _base_config()
    payload["llm"]["temperature"] = temperature  # type: ignore[index]
    config_file = _write_config(tmp_path, payload)

    with pytest.raises(ConfigurationError, match="llm.temperature"):
        load_config(config_file)


@pytest.mark.parametrize("temperature", [".nan", ".inf", "-.inf"])
def test_load_config_rejects_yaml_non_finite_temperature_literals(
    tmp_path, temperature: str
) -> None:
    payload = _base_config()
    payload["llm"]["temperature"] = temperature  # type: ignore[index]
    config_file = _write_config(tmp_path, payload)

    with pytest.raises(ConfigurationError, match="llm.temperature"):
        load_config(config_file)


def test_load_config_rejects_unknown_nested_field(tmp_path) -> None:
    payload = deepcopy(_base_config())
    payload["paths"]["archive_dir"] = "data/archive"  # type: ignore[index]
    config_file = _write_config(tmp_path, payload)

    with pytest.raises(ConfigurationError, match="Unknown field"):
        load_config(config_file)
