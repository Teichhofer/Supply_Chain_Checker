"""Configuration handling for Supply Chain Checker."""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal, cast

import yaml  # type: ignore[import-untyped]

logger = logging.getLogger(__name__)

_VALID_LOG_LEVELS = {"DEBUG", "INFO", "WARNING", "ERROR"}
_ALLOWED_ON_CORRUPT_STATUS_FILE = {"abort", "fallback_empty"}

_SCHEMA_REQUIRED_FIELDS: dict[str, set[str]] = {
    "__root__": {"paths", "logging", "llm", "prompts", "parameters"},
    "paths": {"input_dir", "output_dir", "state_dir", "logs_dir"},
    "logging": {"level", "file_name"},
    "llm": {"provider", "model", "timeout_seconds", "max_retries", "temperature"},
    "prompts": {"extraction", "assessment"},
    "parameters": {
        "use_ocr_fallback",
        "max_products_per_document",
        "max_assessment_reason_words",
        "on_corrupt_status_file",
    },
}


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
    on_corrupt_status_file: Literal["abort", "fallback_empty"]


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

    _validate_schema(raw_config)

    paths_section = _mapping(raw_config.get("paths"), section_name="paths")
    logging_section = _mapping(raw_config.get("logging"), section_name="logging")
    llm_section = _mapping(raw_config.get("llm"), section_name="llm")
    prompts_section = _mapping(raw_config.get("prompts"), section_name="prompts")
    parameters_section = _mapping(raw_config.get("parameters"), section_name="parameters")

    level = _string(
        logging_section["level"],
        "logging.level",
    ).upper()
    if level not in _VALID_LOG_LEVELS:
        raise ConfigurationError(
            "Invalid logging.level. Expected one of DEBUG, INFO, WARNING, ERROR."
        )

    file_name = _string(
        logging_section["file_name"],
        "logging.file_name",
    )

    provider = _string(llm_section["provider"], "llm.provider")
    model = _string(llm_section["model"], "llm.model")

    timeout_seconds = _int(llm_section["timeout_seconds"], "llm.timeout_seconds", minimum=1)
    max_retries = _int(llm_section["max_retries"], "llm.max_retries", minimum=0)
    temperature = _float(
        llm_section["temperature"],
        "llm.temperature",
        minimum=0.0,
        maximum=2.0,
    )

    extraction_prompt = _string(
        prompts_section["extraction"],
        "prompts.extraction",
    )
    assessment_prompt = _string(
        prompts_section["assessment"],
        "prompts.assessment",
    )

    use_ocr_fallback = _bool(
        parameters_section["use_ocr_fallback"], "parameters.use_ocr_fallback"
    )
    max_products_per_document = _int(
        parameters_section["max_products_per_document"],
        "parameters.max_products_per_document",
        minimum=1,
    )
    max_assessment_reason_words = _int(
        parameters_section["max_assessment_reason_words"],
        "parameters.max_assessment_reason_words",
        minimum=1,
    )
    on_corrupt_status_file_raw = _string(
        parameters_section["on_corrupt_status_file"],
        "parameters.on_corrupt_status_file",
    ).lower()
    if on_corrupt_status_file_raw not in _ALLOWED_ON_CORRUPT_STATUS_FILE:
        raise ConfigurationError(
            "Field 'parameters.on_corrupt_status_file' must be one of: abort, fallback_empty."
        )
    on_corrupt_status_file: Literal["abort", "fallback_empty"] = cast(
        Literal["abort", "fallback_empty"], on_corrupt_status_file_raw
    )

    return AppConfig(
        paths=PathsConfig(
            input_dir=Path(
                _string(paths_section["input_dir"], "paths.input_dir")
            ),
            output_dir=Path(
                _string(paths_section["output_dir"], "paths.output_dir")
            ),
            state_dir=Path(
                _string(paths_section["state_dir"], "paths.state_dir")
            ),
            logs_dir=Path(_string(paths_section["logs_dir"], "paths.logs_dir")),
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
            on_corrupt_status_file=on_corrupt_status_file,
        ),
    )


def _mapping(value: Any, *, section_name: str) -> dict[str, Any]:
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise ConfigurationError(f"Section '{section_name}' must be a mapping.")
    return value


def _validate_schema(raw_config: dict[str, Any]) -> None:
    _require_fields(raw_config, _SCHEMA_REQUIRED_FIELDS["__root__"], section_name="root")
    _reject_unknown_fields(raw_config, _SCHEMA_REQUIRED_FIELDS["__root__"], section_name="root")

    for section_name in ("paths", "logging", "llm", "prompts", "parameters"):
        section = _mapping(raw_config.get(section_name), section_name=section_name)
        required_fields = _SCHEMA_REQUIRED_FIELDS[section_name]
        _require_fields(section, required_fields, section_name=section_name)
        _reject_unknown_fields(section, required_fields, section_name=section_name)


def _require_fields(
    section: dict[str, Any], required_fields: set[str], *, section_name: str
) -> None:
    missing_fields = sorted(required_fields.difference(section.keys()))
    if not missing_fields:
        return

    if section_name == "root":
        qualified_missing = [f"'{field}'" for field in missing_fields]
    else:
        qualified_missing = [f"'{section_name}.{field}'" for field in missing_fields]
    missing_fields_text = ", ".join(qualified_missing)
    raise ConfigurationError(f"Missing required field(s): {missing_fields_text}.")


def _reject_unknown_fields(
    section: dict[str, Any], allowed_fields: set[str], *, section_name: str
) -> None:
    unknown_fields = sorted(set(section.keys()).difference(allowed_fields))
    if not unknown_fields:
        return

    if section_name == "root":
        qualified_unknown = [f"'{field}'" for field in unknown_fields]
    else:
        qualified_unknown = [f"'{section_name}.{field}'" for field in unknown_fields]
    unknown_fields_text = ", ".join(qualified_unknown)
    raise ConfigurationError(f"Unknown field(s) not allowed: {unknown_fields_text}.")


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
    if not math.isfinite(numeric_value):
        raise ConfigurationError(f"Field '{field_name}' must be finite.")
    if numeric_value < minimum or numeric_value > maximum:
        raise ConfigurationError(f"Field '{field_name}' must be between {minimum} and {maximum}.")
    return numeric_value
