"""Tests for deterministic per-product assessment orchestration."""

from __future__ import annotations

import pytest

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

        return (
            '{"risikostufe": 4, "preisänderung_prozent": 3.5, '
            '"begründung": "stabile lieferkette"}'
        )


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
    assert all(result.normalized_assessment is not None for result in results)
    assert [result.normalized_assessment.risk_level for result in results] == [4, 4, 4]


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


def test_assess_products_marks_parse_errors_instead_of_dropping_rows() -> None:
    product = ExtractedProduct(
        document_name="a.pdf", product_name="Bolt", quantity="10", supplier="ACME"
    )

    class InvalidPayloadClient:
        def assess_product(self, *, prompt: str, context: LlmRequestContext) -> str:
            del prompt, context
            return '{"risikostufe": 7, "begründung": "fehlendes pflichtfeld"}'

    service = AssessmentService(llm_client=InvalidPayloadClient())

    results = service.assess_products(
        products=[product],
        assessment_prompt_template="Assess {product_name}",
        run_id="run100",
    )

    assert len(results) == 1
    assert results[0].assessment_status == "parse_error"
    assert results[0].normalized_assessment is None
    assert results[0].error_type == "ParsingError"
    assert results[0].raw_response is not None
    assert "preisänderung_prozent" in (results[0].assessment_hint or "")


def test_assess_products_skips_uncertain_products_without_sending_llm_request() -> None:
    product = ExtractedProduct(
        document_name="a.pdf",
        product_name="UNKNOWN",
        quantity="10",
        supplier="ACME",
        extraction_status="uncertain",
    )
    llm_client = RecordingAssessmentClient()
    service = AssessmentService(llm_client=llm_client)

    results = service.assess_products(
        products=[product],
        assessment_prompt_template="Assess {product_name}",
    )

    assert llm_client.prompts == []
    assert len(results) == 1
    assert results[0].assessment_status == "skipped"
    assert results[0].skip_reason == "UNCONFIRMED_EXTRACTION"


def test_assess_products_skips_products_with_missing_required_fields() -> None:
    product = ExtractedProduct(
        document_name="a.pdf",
        product_name="Bolt",
        quantity="N/A",
        supplier="ACME",
        extraction_status="confirmed",
    )
    llm_client = RecordingAssessmentClient()
    service = AssessmentService(llm_client=llm_client)

    results = service.assess_products(
        products=[product],
        assessment_prompt_template="Assess {product_name}",
    )

    assert llm_client.prompts == []
    assert len(results) == 1
    assert results[0].assessment_status == "skipped"
    assert results[0].skip_reason == "MISSING_QUANTITY"


@pytest.mark.parametrize(
    ("product_name", "supplier", "expected_reason"),
    [
        ("UNKNOWN", "ACME", "MISSING_PRODUCT_NAME"),
        ("Bolt", "N/A", "MISSING_SUPPLIER"),
    ],
)
def test_assess_products_skips_when_product_or_supplier_is_missing(
    product_name: str, supplier: str, expected_reason: str
) -> None:
    product = ExtractedProduct(
        document_name="a.pdf",
        product_name=product_name,
        quantity="10",
        supplier=supplier,
        extraction_status="confirmed",
    )
    llm_client = RecordingAssessmentClient()
    service = AssessmentService(llm_client=llm_client)

    results = service.assess_products(
        products=[product],
        assessment_prompt_template="Assess {product_name}",
    )

    assert llm_client.prompts == []
    assert len(results) == 1
    assert results[0].assessment_status == "skipped"
    assert results[0].skip_reason == expected_reason
