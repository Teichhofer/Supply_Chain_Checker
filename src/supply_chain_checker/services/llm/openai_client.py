"""OpenAI client implementation for extraction and assessment gateway methods."""

from __future__ import annotations

import logging
from collections.abc import Callable

from supply_chain_checker.services.llm.base import (
    LlmClientError,
    LlmGateway,
    LlmRequestContext,
)

logger = logging.getLogger(__name__)


class OpenAIClient(LlmGateway):
    """Thin adapter that hides provider-specific invocation details."""

    def __init__(
        self,
        *,
        extraction_invoker: Callable[[str], str],
        assessment_invoker: Callable[[str], str],
    ) -> None:
        self._extraction_invoker = extraction_invoker
        self._assessment_invoker = assessment_invoker

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
            response = self._extraction_invoker(prompt)
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

    def assess_product(self, *, prompt: str, context: LlmRequestContext) -> str:
        logger.info(
            "llm.assessment.requested",
            extra={
                "event": "llm.assessment.requested",
                "run_id": context.run_id,
                "command": context.command,
            },
        )
        try:
            response = self._assessment_invoker(prompt)
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "llm.assessment.failed",
                extra={
                    "event": "llm.assessment.failed",
                    "run_id": context.run_id,
                    "command": context.command,
                    "error_type": type(exc).__name__,
                },
            )
            raise LlmClientError("OpenAI assessment request failed.") from exc

        logger.info(
            "llm.assessment.succeeded",
            extra={
                "event": "llm.assessment.succeeded",
                "run_id": context.run_id,
                "command": context.command,
                "response_length": len(response),
            },
        )
        return response
