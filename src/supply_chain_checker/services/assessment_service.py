"""Product risk assessment service."""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from typing import Literal

from supply_chain_checker.models import ExtractedProduct
from supply_chain_checker.services.llm import AssessmentLlmGateway, LlmRequestContext
from supply_chain_checker.services.llm.base import LlmClientError

logger = logging.getLogger(__name__)

AssessmentStatus = Literal["assessed", "failed"]


@dataclass(frozen=True)
class ProductAssessmentResult:
    """Assessment outcome bound to one input product."""

    product: ExtractedProduct
    assessment_status: AssessmentStatus
    raw_response: str | None
    error_type: str | None = None


class AssessmentService:
    """Coordinate per-product LLM risk assessments without batching."""

    def __init__(
        self,
        *,
        llm_client: AssessmentLlmGateway,
        prompt_builder: Callable[..., str] | None = None,
    ) -> None:
        self._llm_client = llm_client
        self._prompt_builder = prompt_builder or _build_assessment_prompt

    def assess_products(
        self,
        *,
        products: list[ExtractedProduct],
        assessment_prompt_template: str,
        run_id: str | None = None,
        command: str = "assess",
    ) -> list[ProductAssessmentResult]:
        """Assess each product individually and isolate request-level failures."""

        results: list[ProductAssessmentResult] = []
        for product in products:
            logger.info(
                "assessment.started",
                extra={
                    "event": "assessment.started",
                    "run_id": run_id,
                    "command": command,
                    "document_name": product.document_name,
                    "product_name": product.product_name,
                },
            )
            prompt = self._prompt_builder(template=assessment_prompt_template, product=product)
            try:
                response = self._llm_client.assess_product(
                    prompt=prompt,
                    context=LlmRequestContext(run_id=run_id, command=command),
                )
            except LlmClientError as exc:
                logger.warning(
                    "assessment.failed",
                    extra={
                        "event": "assessment.failed",
                        "run_id": run_id,
                        "command": command,
                        "document_name": product.document_name,
                        "product_name": product.product_name,
                        "error_type": type(exc).__name__,
                    },
                )
                results.append(
                    ProductAssessmentResult(
                        product=product,
                        assessment_status="failed",
                        raw_response=None,
                        error_type=type(exc).__name__,
                    )
                )
                continue

            logger.info(
                "assessment.succeeded",
                extra={
                    "event": "assessment.succeeded",
                    "run_id": run_id,
                    "command": command,
                    "document_name": product.document_name,
                    "product_name": product.product_name,
                },
            )
            results.append(
                ProductAssessmentResult(
                    product=product,
                    assessment_status="assessed",
                    raw_response=response,
                )
            )

        return results


def _build_assessment_prompt(*, template: str, product: ExtractedProduct) -> str:
    return template.format(
        product_name=product.product_name,
        supplier=product.supplier,
        quantity=product.quantity,
        manufacturer=product.manufacturer or "",
        article_number=product.article_number or "",
        document_name=product.document_name,
        extraction_status=product.extraction_status,
        extraction_hint=product.extraction_hint or "",
    )


__all__ = ["AssessmentService", "ProductAssessmentResult", "LlmClientError"]
