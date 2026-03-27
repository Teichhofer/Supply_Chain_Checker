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
    """Path configuration loaded from YAML."""

    logs_dir: Path


@dataclass(frozen=True)
class AppConfig:
    """Root application configuration."""

    paths: PathsConfig
    logging: LoggingConfig


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
    logs_dir_value = paths_section.get("logs_dir", "logs")

    logging_section = _mapping(raw_config.get("logging", {}), section_name="logging")
    level = str(logging_section.get("level", "INFO")).upper()
    if level not in _VALID_LOG_LEVELS:
        raise ConfigurationError(
            "Invalid logging.level. Expected one of DEBUG, INFO, WARNING, ERROR."
        )

    file_name = str(logging_section.get("file_name", "supply_chain_checker.log"))

    return AppConfig(
        paths=PathsConfig(logs_dir=Path(logs_dir_value)),
        logging=LoggingConfig(level=level, file_name=file_name),
    )


def _mapping(value: Any, *, section_name: str) -> dict[str, Any]:
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise ConfigurationError(f"Section '{section_name}' must be a mapping.")
    return value
