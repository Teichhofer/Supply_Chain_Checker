"""Base abstractions for LLM clients."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Protocol

logger = logging.getLogger(__name__)


class LlmClientError(Exception):
    """Raised when communication with an LLM provider fails."""


@dataclass(frozen=True)
class LlmRequestContext:
    """Context metadata for an LLM request used in logs and retries."""

    run_id: str | None
    command: str


class LlmGateway(Protocol):
    """Unified abstraction for extraction and assessment requests."""

    def extract_products(self, *, prompt: str, context: LlmRequestContext) -> str:
        """Return raw model response for extraction prompt."""

    def assess_product(self, *, prompt: str, context: LlmRequestContext) -> str:
        """Return raw model response for one product assessment prompt."""
