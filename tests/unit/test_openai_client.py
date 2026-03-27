"""Tests for OpenAI LLM adapter clients."""

from __future__ import annotations

import pytest

from supply_chain_checker.services.llm.base import LlmClientError, LlmRequestContext
from supply_chain_checker.services.llm.openai_client import OpenAIAssessmentClient, OpenAIExtractionClient


def test_openai_extraction_client_returns_response_on_success() -> None:
    client = OpenAIExtractionClient(invoker=lambda prompt: f"response for {prompt}")

    response = client.extract_products(
        prompt="extract prompt",
        context=LlmRequestContext(run_id="run123", command="extract"),
    )

    assert response == "response for extract prompt"


def test_openai_extraction_client_wraps_errors_in_llm_client_error() -> None:
    def _raise_error(_: str) -> str:
        raise RuntimeError("provider down")

    client = OpenAIExtractionClient(invoker=_raise_error)

    with pytest.raises(LlmClientError, match="OpenAI extraction request failed"):
        client.extract_products(
            prompt="extract prompt",
            context=LlmRequestContext(run_id="run123", command="extract"),
        )


def test_openai_assessment_client_returns_response_on_success() -> None:
    client = OpenAIAssessmentClient(invoker=lambda prompt: f"assessment for {prompt}")

    response = client.assess_product(
        prompt="assess prompt",
        context=LlmRequestContext(run_id="run123", command="assess"),
    )

    assert response == "assessment for assess prompt"


def test_openai_assessment_client_wraps_errors_in_llm_client_error() -> None:
    def _raise_error(_: str) -> str:
        raise RuntimeError("provider down")

    client = OpenAIAssessmentClient(invoker=_raise_error)

    with pytest.raises(LlmClientError, match="OpenAI assessment request failed"):
        client.assess_product(
            prompt="assess prompt",
            context=LlmRequestContext(run_id="run123", command="assess"),
        )
