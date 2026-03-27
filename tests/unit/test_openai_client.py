"""Tests for OpenAI LLM adapter clients."""

from __future__ import annotations

import pytest

from supply_chain_checker.services.llm.base import LlmClientError, LlmRequestContext
from supply_chain_checker.services.llm.openai_client import OpenAIClient


def test_openai_client_returns_extraction_response_on_success() -> None:
    client = OpenAIClient(
        extraction_invoker=lambda prompt: f"response for {prompt}",
        assessment_invoker=lambda prompt: f"assessment for {prompt}",
    )

    response = client.extract_products(
        prompt="extract prompt",
        context=LlmRequestContext(run_id="run123", command="extract"),
    )

    assert response == "response for extract prompt"


def test_openai_client_wraps_extraction_errors_in_llm_client_error() -> None:
    def _raise_error(_: str) -> str:
        raise RuntimeError("provider down")

    client = OpenAIClient(
        extraction_invoker=_raise_error,
        assessment_invoker=lambda prompt: f"assessment for {prompt}",
    )

    with pytest.raises(LlmClientError, match="OpenAI extraction request failed"):
        client.extract_products(
            prompt="extract prompt",
            context=LlmRequestContext(run_id="run123", command="extract"),
        )


def test_openai_client_returns_assessment_response_on_success() -> None:
    client = OpenAIClient(
        extraction_invoker=lambda prompt: f"response for {prompt}",
        assessment_invoker=lambda prompt: f"assessment for {prompt}",
    )

    response = client.assess_product(
        prompt="assess prompt",
        context=LlmRequestContext(run_id="run123", command="assess"),
    )

    assert response == "assessment for assess prompt"


def test_openai_client_wraps_assessment_errors_in_llm_client_error() -> None:
    def _raise_error(_: str) -> str:
        raise RuntimeError("provider down")

    client = OpenAIClient(
        extraction_invoker=lambda prompt: f"response for {prompt}",
        assessment_invoker=_raise_error,
    )

    with pytest.raises(LlmClientError, match="OpenAI assessment request failed"):
        client.assess_product(
            prompt="assess prompt",
            context=LlmRequestContext(run_id="run123", command="assess"),
        )
