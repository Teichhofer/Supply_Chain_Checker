"""OpenAI client implementation for extraction and assessment gateway methods."""

from __future__ import annotations

import json
import logging
import os
import time
from collections.abc import Callable
from dataclasses import dataclass
from http import HTTPStatus
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from supply_chain_checker.services.llm.base import (
    LlmAuthenticationError,
    LlmClientError,
    LlmConfigurationError,
    LlmGateway,
    LlmRateLimitError,
    LlmRequestContext,
    LlmResponseError,
    LlmServiceError,
    LlmTimeoutError,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class OpenAIAdapterConfig:
    """Runtime options for the OpenAI adapter."""

    model: str
    timeout_seconds: int
    max_retries: int
    temperature: float


class OpenAIClient(LlmGateway):
    """Production-ready OpenAI adapter with retries and domain-specific errors."""

    def __init__(
        self,
        *,
        config: OpenAIAdapterConfig,
        api_key: str | None = None,
        base_url: str = "https://api.openai.com/v1",
        extraction_invoker: Callable[[str], str] | None = None,
        assessment_invoker: Callable[[str], str] | None = None,
    ) -> None:
        self._config = config
        self._api_key = (api_key or os.getenv("OPENAI_API_KEY", "")).strip()
        self._base_url = base_url.rstrip("/")
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
        response = self._call_with_error_mapping(
            prompt=prompt,
            context=context,
            operation="extraction",
            invoker=self._extraction_invoker,
        )
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
        response = self._call_with_error_mapping(
            prompt=prompt,
            context=context,
            operation="assessment",
            invoker=self._assessment_invoker,
        )
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

    def _call_with_error_mapping(
        self,
        *,
        prompt: str,
        context: LlmRequestContext,
        operation: str,
        invoker: Callable[[str], str] | None,
    ) -> str:
        last_error: Exception | None = None

        for attempt in range(self._config.max_retries + 1):
            try:
                if invoker is not None:
                    return invoker(prompt)
                return self._invoke_openai(prompt)
            except LlmClientError as exc:
                last_error = exc
                if not isinstance(exc, (LlmTimeoutError, LlmServiceError, LlmRateLimitError)):
                    self._log_failure(
                        context=context, operation=operation, error=exc, attempt=attempt
                    )
                    raise
                if attempt >= self._config.max_retries:
                    self._log_failure(
                        context=context, operation=operation, error=exc, attempt=attempt
                    )
                    raise
            except Exception as exc:  # noqa: BLE001
                last_error = LlmClientError(f"OpenAI {operation} request failed.")
                self._log_failure(context=context, operation=operation, error=exc, attempt=attempt)
                raise last_error from exc

            backoff_seconds = min(2**attempt, 8)
            logger.warning(
                "llm.request.retrying",
                extra={
                    "event": "llm.request.retrying",
                    "run_id": context.run_id,
                    "command": context.command,
                    "operation": operation,
                    "attempt": attempt + 1,
                    "max_retries": self._config.max_retries,
                    "backoff_seconds": backoff_seconds,
                    "error_type": type(last_error).__name__ if last_error else "UnknownError",
                },
            )
            time.sleep(backoff_seconds)

        raise LlmServiceError(f"OpenAI {operation} request exhausted retries.")

    def _invoke_openai(self, prompt: str) -> str:
        if not self._api_key:
            raise LlmConfigurationError("OPENAI_API_KEY is required for OpenAI provider requests.")

        payload = {
            "model": self._config.model,
            "temperature": self._config.temperature,
            "messages": [{"role": "user", "content": prompt}],
        }

        request = Request(
            url=f"{self._base_url}/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            method="POST",
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
            },
        )

        try:
            with urlopen(request, timeout=self._config.timeout_seconds) as response:
                raw_body = response.read().decode("utf-8")
        except HTTPError as exc:
            self._raise_http_error(exc)
        except TimeoutError as exc:
            raise LlmTimeoutError("OpenAI request timed out.") from exc
        except URLError as exc:
            if isinstance(exc.reason, TimeoutError):
                raise LlmTimeoutError("OpenAI request timed out.") from exc
            raise LlmServiceError("OpenAI service request failed.") from exc

        try:
            parsed = json.loads(raw_body)
            content = parsed["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
            raise LlmResponseError("OpenAI response format was invalid.") from exc

        if not isinstance(content, str) or not content.strip():
            raise LlmResponseError("OpenAI response content was empty or not a string.")

        return content

    def _raise_http_error(self, error: HTTPError) -> None:
        status_code = error.code
        if status_code == HTTPStatus.UNAUTHORIZED:
            raise LlmAuthenticationError("OpenAI authentication failed.") from error
        if status_code == HTTPStatus.TOO_MANY_REQUESTS:
            raise LlmRateLimitError("OpenAI rate limit exceeded.") from error
        if status_code in {
            HTTPStatus.BAD_GATEWAY,
            HTTPStatus.SERVICE_UNAVAILABLE,
            HTTPStatus.GATEWAY_TIMEOUT,
            HTTPStatus.INTERNAL_SERVER_ERROR,
        }:
            raise LlmServiceError(f"OpenAI temporary service error: {status_code}.") from error
        raise LlmClientError(f"OpenAI request failed with status code {status_code}.") from error

    def _log_failure(
        self,
        *,
        context: LlmRequestContext,
        operation: str,
        error: Exception,
        attempt: int,
    ) -> None:
        logger.warning(
            f"llm.{operation}.failed",
            extra={
                "event": f"llm.{operation}.failed",
                "run_id": context.run_id,
                "command": context.command,
                "attempt": attempt + 1,
                "error_type": type(error).__name__,
            },
        )
