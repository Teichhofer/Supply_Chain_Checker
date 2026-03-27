"""Tests for logging conventions in core modules."""

from __future__ import annotations

import importlib
import logging

CORE_MODULES = (
    "supply_chain_checker.cli",
    "supply_chain_checker.config",
    "supply_chain_checker.logging_setup",
    "supply_chain_checker.scaffold",
    "supply_chain_checker.services.pdf_reader",
    "supply_chain_checker.services.ocr_service",
    "supply_chain_checker.services.extraction_service",
    "supply_chain_checker.services.assessment_service",
    "supply_chain_checker.services.csv_service",
    "supply_chain_checker.services.status_service",
    "supply_chain_checker.services.llm.base",
    "supply_chain_checker.services.llm.openai_client",
)


def test_core_modules_define_named_logger() -> None:
    for module_name in CORE_MODULES:
        module = importlib.import_module(module_name)

        assert hasattr(module, "logger"), f"{module_name} is missing module logger"

        module_logger = module.logger
        assert isinstance(module_logger, logging.Logger)
        assert module_logger.name == module_name
