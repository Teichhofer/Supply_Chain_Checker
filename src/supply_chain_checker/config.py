"""Configuration handling for Supply Chain Checker."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml  # type: ignore[import-untyped]

logger = logging.getLogger(__name__)

_VALID_LOG_LEVELS = {"DEBUG", "INFO", "WARNING", "ERROR"}


class ConfigurationError(Exception):
    """Raised when YAML configuration is invalid or cannot be loaded."""


@dataclass(frozen=True)
class LoggingConfig:
    """Runtime logging configuration loaded from YAML."""

    level: str
    file_name: str


@dataclass(frozen=True)
class PathsConfig:
    """Filesystem path configuration loaded from YAML."""

    input_dir: Path
    output_dir: Path
    state_dir: Path
    logs_dir: Path


@dataclass(frozen=True)
class LlmConfig:
    """LLM provider configuration."""

    provider: str
    model: str
    timeout_seconds: int
    max_retries: int
    temperature: float


@dataclass(frozen=True)
class PromptsConfig:
    """Prompt templates for extraction and assessment."""

    extraction: str
    assessment: str


@dataclass(frozen=True)
class ParametersConfig:
    """Runtime processing parameters."""

    use_ocr_fallback: bool
    max_products_per_document: int
    max_assessment_reason_words: int


@dataclass(frozen=True)
class AppConfig:
    """Root application configuration."""

    paths: PathsConfig
    logging: LoggingConfig
    llm: LlmConfig
    prompts: PromptsConfig
    parameters: ParametersConfig


def load_config(config_path: str | Path) -> AppConfig:
    """Load and validate application configuration from YAML."""

    raw_path = Path(config_path)
    try:
        raw_config = yaml.safe_load(raw_path.read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError) as exc:
        logger.error(
            "config.load.failed",
            extra={"event": "config.load.failed", "error_type": type(exc).__name__},
        )
        raise ConfigurationError(f"Could not load config file: {raw_path}") from exc

    if not isinstance(raw_config, dict):
        raise ConfigurationError("Top-level YAML structure must be a mapping.")

    paths_section = _mapping(raw_config.get("paths"), section_name="paths")
    logging_section = _mapping(raw_config.get("logging", {}), section_name="logging")
    llm_section = _mapping(raw_config.get("llm"), section_name="llm")
    prompts_section = _mapping(raw_config.get("prompts", {}), section_name="prompts")
    parameters_section = _mapping(raw_config.get("parameters", {}), section_name="parameters")

    level = _string(
        logging_section.get("level", "INFO"),
        "logging.level",
    ).upper()
    if level not in _VALID_LOG_LEVELS:
        raise ConfigurationError(
            "Invalid logging.level. Expected one of DEBUG, INFO, WARNING, ERROR."
        )

    file_name = _string(
        logging_section.get("file_name", "supply_chain_checker.log"),
        "logging.file_name",
    )

    provider = _required_string(llm_section, key="provider", section_name="llm")
    model = _required_string(llm_section, key="model", section_name="llm")

    timeout_seconds = _int(llm_section.get("timeout_seconds", 30), "llm.timeout_seconds", minimum=1)
    max_retries = _int(llm_section.get("max_retries", 2), "llm.max_retries", minimum=0)
    temperature = _float(
        llm_section.get("temperature", 0.0),
        "llm.temperature",
        minimum=0.0,
        maximum=2.0,
    )

    extraction_prompt = _string(
        prompts_section.get(
            "extraction",
            "Extract all products from the provided document text and respond as JSON.",
        ),
        "prompts.extraction",
    )
    assessment_prompt = _string(
        prompts_section.get(
            "assessment",
            "Assess supply-chain risk for {product_name} and respond as JSON.",
        ),
        "prompts.assessment",
    )

    use_ocr_fallback = _bool(
        parameters_section.get("use_ocr_fallback", True), "parameters.use_ocr_fallback"
    )
    max_products_per_document = _int(
        parameters_section.get("max_products_per_document", 100),
        "parameters.max_products_per_document",
        minimum=1,
    )
    max_assessment_reason_words = _int(
        parameters_section.get("max_assessment_reason_words", 100),
        "parameters.max_assessment_reason_words",
        minimum=1,
    )

    return AppConfig(
        paths=PathsConfig(
            input_dir=Path(
                _string(paths_section.get("input_dir", "data/input"), "paths.input_dir")
            ),
            output_dir=Path(
                _string(paths_section.get("output_dir", "data/output"), "paths.output_dir")
            ),
            state_dir=Path(
                _string(paths_section.get("state_dir", "data/state"), "paths.state_dir")
            ),
            logs_dir=Path(_string(paths_section.get("logs_dir", "logs"), "paths.logs_dir")),
        ),
        logging=LoggingConfig(level=level, file_name=file_name),
        llm=LlmConfig(
            provider=provider,
            model=model,
            timeout_seconds=timeout_seconds,
            max_retries=max_retries,
            temperature=temperature,
        ),
        prompts=PromptsConfig(extraction=extraction_prompt, assessment=assessment_prompt),
        parameters=ParametersConfig(
            use_ocr_fallback=use_ocr_fallback,
            max_products_per_document=max_products_per_document,
            max_assessment_reason_words=max_assessment_reason_words,
        ),
    )


def _mapping(value: Any, *, section_name: str) -> dict[str, Any]:
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise ConfigurationError(f"Section '{section_name}' must be a mapping.")
    return value


def _required_string(section: dict[str, Any], *, key: str, section_name: str) -> str:
    if key not in section:
        raise ConfigurationError(f"Missing required field '{section_name}.{key}'.")
    return _string(section[key], f"{section_name}.{key}")


def _string(value: Any, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ConfigurationError(f"Field '{field_name}' must be a non-empty string.")
    return value.strip()


def _bool(value: Any, field_name: str) -> bool:
    if not isinstance(value, bool):
        raise ConfigurationError(f"Field '{field_name}' must be a boolean.")
    return value


def _int(value: Any, field_name: str, *, minimum: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ConfigurationError(f"Field '{field_name}' must be an integer.")
    if value < minimum:
        raise ConfigurationError(f"Field '{field_name}' must be >= {minimum}.")
    return int(value)


def _float(value: Any, field_name: str, *, minimum: float, maximum: float) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ConfigurationError(f"Field '{field_name}' must be a number.")

    numeric_value = float(value)
    if numeric_value < minimum or numeric_value > maximum:
        raise ConfigurationError(f"Field '{field_name}' must be between {minimum} and {maximum}.")
    return numeric_value
