"""Tests for OpenAI LLM adapter clients."""

from __future__ import annotations

import io
import json
from urllib.error import HTTPError

import pytest

from supply_chain_checker.services.llm.base import (
    LlmAuthenticationError,
    LlmClientError,
    LlmConfigurationError,
    LlmRateLimitError,
    LlmRequestContext,
    LlmServiceError,
)
from supply_chain_checker.services.llm.openai_client import OpenAIAdapterConfig, OpenAIClient


@pytest.fixture
def adapter_config() -> OpenAIAdapterConfig:
    return OpenAIAdapterConfig(
        model="gpt-4.1-mini",
        timeout_seconds=5,
        max_retries=2,
        temperature=0.1,
    )


def test_openai_client_returns_extraction_response_on_success(
    adapter_config: OpenAIAdapterConfig,
) -> None:
    client = OpenAIClient(
        config=adapter_config,
        extraction_invoker=lambda prompt: f"response for {prompt}",
        assessment_invoker=lambda prompt: f"assessment for {prompt}",
    )

    response = client.extract_products(
        prompt="extract prompt",
        context=LlmRequestContext(run_id="run123", command="extract"),
    )

    assert response == "response for extract prompt"


def test_openai_client_wraps_unexpected_extraction_errors_in_llm_client_error(
    adapter_config: OpenAIAdapterConfig,
) -> None:
    def _raise_error(_: str) -> str:
        raise RuntimeError("provider down")

    client = OpenAIClient(
        config=adapter_config,
        extraction_invoker=_raise_error,
        assessment_invoker=lambda prompt: f"assessment for {prompt}",
    )

    with pytest.raises(LlmClientError, match="OpenAI extraction request failed"):
        client.extract_products(
            prompt="extract prompt",
            context=LlmRequestContext(run_id="run123", command="extract"),
        )


def test_openai_client_returns_assessment_response_on_success(
    adapter_config: OpenAIAdapterConfig,
) -> None:
    client = OpenAIClient(
        config=adapter_config,
        extraction_invoker=lambda prompt: f"response for {prompt}",
        assessment_invoker=lambda prompt: f"assessment for {prompt}",
    )

    response = client.assess_product(
        prompt="assess prompt",
        context=LlmRequestContext(run_id="run123", command="assess"),
    )

    assert response == "assessment for assess prompt"


def test_openai_client_preserves_domain_specific_assessment_errors(
    adapter_config: OpenAIAdapterConfig,
) -> None:
    def _raise_error(_: str) -> str:
        raise LlmRateLimitError("slow down")

    client = OpenAIClient(
        config=adapter_config,
        extraction_invoker=lambda prompt: f"response for {prompt}",
        assessment_invoker=_raise_error,
    )

    with pytest.raises(LlmRateLimitError, match="slow down"):
        client.assess_product(
            prompt="assess prompt",
            context=LlmRequestContext(run_id="run123", command="assess"),
        )


def test_openai_client_raises_configuration_error_without_api_key(
    adapter_config: OpenAIAdapterConfig,
) -> None:
    client = OpenAIClient(config=adapter_config, api_key="")

    with pytest.raises(LlmConfigurationError, match="OPENAI_API_KEY"):
        client.extract_products(
            prompt="extract prompt",
            context=LlmRequestContext(run_id="run123", command="extract"),
        )


def test_openai_client_maps_unauthorized_http_error(
    monkeypatch, adapter_config: OpenAIAdapterConfig
) -> None:
    client = OpenAIClient(config=adapter_config, api_key="test-key")

    def _raise_http_error(*_args: object, **_kwargs: object):
        raise HTTPError(
            url="https://api.openai.com/v1/chat/completions",
            code=401,
            msg="Unauthorized",
            hdrs=None,
            fp=io.BytesIO(b'{"error":"unauthorized"}'),
        )

    monkeypatch.setattr(
        "supply_chain_checker.services.llm.openai_client.urlopen", _raise_http_error
    )

    with pytest.raises(LlmAuthenticationError, match="authentication failed"):
        client.extract_products(
            prompt="extract prompt",
            context=LlmRequestContext(run_id="run123", command="extract"),
        )


def test_openai_client_retries_transient_errors_and_succeeds(
    monkeypatch,
    adapter_config: OpenAIAdapterConfig,
) -> None:
    attempts = {"count": 0}

    def _invoker(_: str) -> str:
        attempts["count"] += 1
        if attempts["count"] < 3:
            raise LlmServiceError("temporary outage")
        return "ok"

    client = OpenAIClient(config=adapter_config, extraction_invoker=_invoker)
    monkeypatch.setattr(
        "supply_chain_checker.services.llm.openai_client.time.sleep", lambda _: None
    )

    response = client.extract_products(
        prompt="extract prompt",
        context=LlmRequestContext(run_id="run123", command="extract"),
    )

    assert response == "ok"
    assert attempts["count"] == 3


def test_openai_client_raises_service_error_for_5xx(
    monkeypatch, adapter_config: OpenAIAdapterConfig
) -> None:
    client = OpenAIClient(config=adapter_config, api_key="test-key")

    def _raise_http_error(*_args: object, **_kwargs: object):
        raise HTTPError(
            url="https://api.openai.com/v1/chat/completions",
            code=503,
            msg="Service unavailable",
            hdrs=None,
            fp=io.BytesIO(b'{"error":"service unavailable"}'),
        )

    monkeypatch.setattr(
        "supply_chain_checker.services.llm.openai_client.urlopen", _raise_http_error
    )
    monkeypatch.setattr(
        "supply_chain_checker.services.llm.openai_client.time.sleep", lambda _: None
    )

    with pytest.raises(LlmServiceError, match="temporary service error"):
        client.extract_products(
            prompt="extract prompt",
            context=LlmRequestContext(run_id="run123", command="extract"),
        )


def test_openai_client_parses_real_http_response(
    monkeypatch, adapter_config: OpenAIAdapterConfig
) -> None:
    client = OpenAIClient(config=adapter_config, api_key="test-key")

    class _DummyResponse:
        def __init__(self, body: str) -> None:
            self._body = body

        def read(self) -> bytes:
            return self._body.encode("utf-8")

        def __enter__(self) -> _DummyResponse:
            return self

        def __exit__(self, *_exc: object) -> None:
            return None

    def _urlopen(*_args: object, **_kwargs: object) -> _DummyResponse:
        return _DummyResponse(
            json.dumps(
                {
                    "choices": [
                        {
                            "message": {
                                "content": "json-response",
                            }
                        }
                    ]
                }
            )
        )

    monkeypatch.setattr("supply_chain_checker.services.llm.openai_client.urlopen", _urlopen)

    response = client.assess_product(
        prompt="assess prompt",
        context=LlmRequestContext(run_id="run123", command="assess"),
    )

    assert response == "json-response"
