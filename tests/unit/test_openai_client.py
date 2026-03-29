"""Tests for OpenAI LLM adapter clients."""

from __future__ import annotations

import io
import json
from urllib.error import HTTPError, URLError

import pytest

from supply_chain_checker.services.llm.base import (
    LlmAuthenticationError,
    LlmClientError,
    LlmConfigurationError,
    LlmRateLimitError,
    LlmRequestContext,
    LlmResponseError,
    LlmServiceError,
    LlmTimeoutError,
)
from supply_chain_checker.logging_setup import setup_logging
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


def test_openai_client_logs_prompt_and_response_in_llm_log(
    adapter_config: OpenAIAdapterConfig, tmp_path
) -> None:
    setup_logging(logs_dir=tmp_path, level="INFO", run_id="run123", file_name="app.log")
    client = OpenAIClient(
        config=adapter_config,
        extraction_invoker=lambda prompt: f"response for {prompt}",
    )

    response = client.extract_products(
        prompt="extract prompt",
        context=LlmRequestContext(run_id="run123", command="extract"),
    )

    assert response == "response for extract prompt"
    llm_log_content = (tmp_path / "app_llm.log").read_text(encoding="utf-8")
    assert "direction=request" in llm_log_content
    assert "payload=extract prompt" in llm_log_content
    assert "direction=response" in llm_log_content
    assert "payload=response for extract prompt" in llm_log_content


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
    monkeypatch,
    adapter_config: OpenAIAdapterConfig,
) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    client = OpenAIClient(config=adapter_config, api_key="")

    with pytest.raises(LlmConfigurationError, match="OPENAI_API_KEY"):
        client.extract_products(
            prompt="extract prompt",
            context=LlmRequestContext(run_id="run123", command="extract"),
        )


def test_openai_client_maps_unauthorized_http_error(
    monkeypatch, adapter_config: OpenAIAdapterConfig, caplog
) -> None:
    client = OpenAIClient(config=adapter_config, api_key="sk-test-key-1234")

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

    with caplog.at_level("WARNING"):
        with pytest.raises(LlmAuthenticationError, match="authentication failed"):
            client.extract_products(
                prompt="extract prompt",
                context=LlmRequestContext(run_id="run123", command="extract"),
            )

    assert "llm.authentication.failed api_key_suffix=1234" in caplog.text
    auth_failure_records = [
        record for record in caplog.records if record.message.startswith("llm.authentication.failed")
    ]
    assert auth_failure_records
    assert auth_failure_records[0].api_key_suffix == "1234"


def test_openai_client_logs_api_key_suffix_in_llm_error_payload(
    monkeypatch, adapter_config: OpenAIAdapterConfig, tmp_path
) -> None:
    setup_logging(logs_dir=tmp_path, level="INFO", run_id="run123", file_name="app.log")
    client = OpenAIClient(config=adapter_config, api_key="sk-test-key-1234")

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

    with pytest.raises(LlmAuthenticationError, match="api_key_suffix=1234"):
        client.extract_products(
            prompt="extract prompt",
            context=LlmRequestContext(run_id="run123", command="extract"),
        )

    llm_log_content = (tmp_path / "app_llm.log").read_text(encoding="utf-8")
    assert "direction=error" in llm_log_content
    assert "payload=OpenAI authentication failed (api_key_suffix=1234)." in llm_log_content


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


def test_openai_client_maps_rate_limit_http_error(
    monkeypatch, adapter_config: OpenAIAdapterConfig
) -> None:
    client = OpenAIClient(config=adapter_config, api_key="test-key")

    def _raise_http_error(*_args: object, **_kwargs: object):
        raise HTTPError(
            url="https://api.openai.com/v1/chat/completions",
            code=429,
            msg="Too Many Requests",
            hdrs=None,
            fp=io.BytesIO(b'{"error":"rate limit"}'),
        )

    monkeypatch.setattr(
        "supply_chain_checker.services.llm.openai_client.urlopen",
        _raise_http_error,
    )

    with pytest.raises(LlmRateLimitError, match="rate limit exceeded"):
        client.extract_products(
            prompt="extract prompt",
            context=LlmRequestContext(run_id="run123", command="extract"),
        )


def test_openai_client_maps_generic_http_error_to_client_error(
    monkeypatch, adapter_config: OpenAIAdapterConfig
) -> None:
    client = OpenAIClient(config=adapter_config, api_key="test-key")

    def _raise_http_error(*_args: object, **_kwargs: object):
        raise HTTPError(
            url="https://api.openai.com/v1/chat/completions",
            code=418,
            msg="I'm a teapot",
            hdrs=None,
            fp=io.BytesIO(b'{"error":"teapot"}'),
        )

    monkeypatch.setattr(
        "supply_chain_checker.services.llm.openai_client.urlopen",
        _raise_http_error,
    )

    with pytest.raises(LlmClientError, match="status code 418"):
        client.extract_products(
            prompt="extract prompt",
            context=LlmRequestContext(run_id="run123", command="extract"),
        )


def test_openai_client_maps_direct_timeout_error(
    monkeypatch, adapter_config: OpenAIAdapterConfig
) -> None:
    client = OpenAIClient(config=adapter_config, api_key="test-key")

    def _raise_timeout(*_args: object, **_kwargs: object):
        raise TimeoutError("timeout")

    monkeypatch.setattr("supply_chain_checker.services.llm.openai_client.urlopen", _raise_timeout)

    with pytest.raises(LlmTimeoutError, match="timed out"):
        client.extract_products(
            prompt="extract prompt",
            context=LlmRequestContext(run_id="run123", command="extract"),
        )


def test_openai_client_maps_urlerror_timeout_reason(
    monkeypatch, adapter_config: OpenAIAdapterConfig
) -> None:
    client = OpenAIClient(config=adapter_config, api_key="test-key")

    def _raise_timeout(*_args: object, **_kwargs: object):
        raise URLError(TimeoutError("timeout"))

    monkeypatch.setattr("supply_chain_checker.services.llm.openai_client.urlopen", _raise_timeout)

    with pytest.raises(LlmTimeoutError, match="timed out"):
        client.extract_products(
            prompt="extract prompt",
            context=LlmRequestContext(run_id="run123", command="extract"),
        )


def test_openai_client_maps_urlerror_service_failure(
    monkeypatch, adapter_config: OpenAIAdapterConfig
) -> None:
    client = OpenAIClient(config=adapter_config, api_key="test-key")

    def _raise_urlerror(*_args: object, **_kwargs: object):
        raise URLError("dns failure")

    monkeypatch.setattr("supply_chain_checker.services.llm.openai_client.urlopen", _raise_urlerror)

    with pytest.raises(LlmServiceError, match="service request failed"):
        client.extract_products(
            prompt="extract prompt",
            context=LlmRequestContext(run_id="run123", command="extract"),
        )


def test_openai_client_rejects_invalid_response_shape(
    monkeypatch, adapter_config: OpenAIAdapterConfig
) -> None:
    client = OpenAIClient(config=adapter_config, api_key="test-key")

    class _DummyResponse:
        def read(self) -> bytes:
            return b'{"choices":[]}'

        def __enter__(self) -> _DummyResponse:
            return self

        def __exit__(self, *_exc: object) -> None:
            return None

    monkeypatch.setattr(
        "supply_chain_checker.services.llm.openai_client.urlopen",
        lambda *_args, **_kwargs: _DummyResponse(),
    )

    with pytest.raises(LlmResponseError, match="format was invalid"):
        client.assess_product(
            prompt="assess prompt",
            context=LlmRequestContext(run_id="run123", command="assess"),
        )


def test_openai_client_rejects_empty_content_response(
    monkeypatch, adapter_config: OpenAIAdapterConfig
) -> None:
    client = OpenAIClient(config=adapter_config, api_key="test-key")

    class _DummyResponse:
        def read(self) -> bytes:
            return b'{"choices":[{"message":{"content":"  "}}]}'

        def __enter__(self) -> _DummyResponse:
            return self

        def __exit__(self, *_exc: object) -> None:
            return None

    monkeypatch.setattr(
        "supply_chain_checker.services.llm.openai_client.urlopen",
        lambda *_args, **_kwargs: _DummyResponse(),
    )

    with pytest.raises(LlmResponseError, match="empty or not a string"):
        client.assess_product(
            prompt="assess prompt",
            context=LlmRequestContext(run_id="run123", command="assess"),
        )


def test_openai_client_handles_unreachable_retry_exhausted_guard() -> None:
    config = OpenAIAdapterConfig(
        model="gpt-4.1-mini",
        timeout_seconds=5,
        max_retries=-1,
        temperature=0.1,
    )
    client = OpenAIClient(config=config, extraction_invoker=lambda _prompt: "ok")

    with pytest.raises(LlmServiceError, match="exhausted retries"):
        client.extract_products(
            prompt="extract prompt",
            context=LlmRequestContext(run_id="run123", command="extract"),
        )
