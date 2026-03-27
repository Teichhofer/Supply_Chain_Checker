"""Tests for deterministic per-product assessment orchestration."""

from __future__ import annotations

from supply_chain_checker.models import ExtractedProduct
from supply_chain_checker.services.assessment_service import AssessmentService
from supply_chain_checker.services.llm.base import LlmClientError, LlmRequestContext


class RecordingAssessmentClient:
    def __init__(self, *, failing_products: set[str] | None = None) -> None:
        self.failing_products = failing_products or set()
        self.prompts: list[str] = []
        self.contexts: list[LlmRequestContext] = []

    def assess_product(self, *, prompt: str, context: LlmRequestContext) -> str:
        self.prompts.append(prompt)
        self.contexts.append(context)

        if any(product_name in prompt for product_name in self.failing_products):
            raise LlmClientError("simulated provider failure")

        return '{"risk_level": 4, "reason": "stable"}'


def test_assess_products_sends_exactly_one_llm_request_per_product() -> None:
    products = [
        ExtractedProduct(
            document_name="a.pdf", product_name="Bolt", quantity="10", supplier="ACME"
        ),
        ExtractedProduct(document_name="b.pdf", product_name="Nut", quantity="20", supplier="ACME"),
        ExtractedProduct(
            document_name="c.pdf", product_name="Screw", quantity="30", supplier="ACME"
        ),
    ]
    llm_client = RecordingAssessmentClient()
    service = AssessmentService(llm_client=llm_client)

    results = service.assess_products(
        products=products,
        assessment_prompt_template="Assess {product_name} from {supplier}",
        run_id="run42",
    )

    assert len(llm_client.prompts) == len(products)
    assert all("Assess" in prompt for prompt in llm_client.prompts)
    assert llm_client.contexts == [LlmRequestContext(run_id="run42", command="assess")] * 3

    assert len(results) == len(products)
    assert [result.product.product_name for result in results] == ["Bolt", "Nut", "Screw"]
    assert {result.assessment_status for result in results} == {"assessed"}


def test_assess_products_isolates_llm_failures_per_product() -> None:
    products = [
        ExtractedProduct(
            document_name="a.pdf", product_name="Bolt", quantity="10", supplier="ACME"
        ),
        ExtractedProduct(document_name="b.pdf", product_name="Nut", quantity="20", supplier="ACME"),
        ExtractedProduct(
            document_name="c.pdf", product_name="Screw", quantity="30", supplier="ACME"
        ),
    ]
    llm_client = RecordingAssessmentClient(failing_products={"Nut"})
    service = AssessmentService(llm_client=llm_client)

    results = service.assess_products(
        products=products,
        assessment_prompt_template="Assess {product_name}",
        run_id="run99",
    )

    assert len(llm_client.prompts) == len(products)
    assert [result.product.product_name for result in results] == ["Bolt", "Nut", "Screw"]
    assert [result.assessment_status for result in results] == ["assessed", "failed", "assessed"]
    assert [result.error_type for result in results] == [None, "LlmClientError", None]
