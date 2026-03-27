"""OpenAI client implementation for the extraction gateway."""

from __future__ import annotations

import logging
from collections.abc import Callable

from supply_chain_checker.services.llm.base import (
    ExtractionLlmGateway,
    LlmClientError,
    LlmRequestContext,
)

logger = logging.getLogger(__name__)


class OpenAIExtractionClient(ExtractionLlmGateway):
    """Thin adapter that hides provider-specific invocation details."""

    def __init__(self, invoker: Callable[[str], str]) -> None:
        self._invoker = invoker

    def extract_products(self, *, prompt: str, context: LlmRequestContext) -> str:
        logger.info(
            "llm.extraction.requested",
            extra={
                "event": "llm.extraction.requested",
                "run_id": context.run_id,
                "command": context.command,
            },
        )
        try:
            response = self._invoker(prompt)
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "llm.extraction.failed",
                extra={
                    "event": "llm.extraction.failed",
                    "run_id": context.run_id,
                    "command": context.command,
                    "error_type": type(exc).__name__,
                },
            )
            raise LlmClientError("OpenAI extraction request failed.") from exc

        logger.info(
            "llm.extraction.succeeded",
            extra={
                "event": "llm.extraction.succeeded",
                "run_id": context.run_id,
                "command": context.command,
                "response_length": len(response),
            },
        )
        return response
