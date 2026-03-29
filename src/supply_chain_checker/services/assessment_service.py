"""Product risk assessment service."""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from typing import Literal

from supply_chain_checker.models import ExtractedProduct
from supply_chain_checker.parsers import ParsedAssessment, ParsingError, parse_assessment_response
from supply_chain_checker.services.llm import (
    LlmGateway,
    LlmRequestContext,
    build_assessment_prompt,
)
from supply_chain_checker.services.llm.base import LlmClientError, LlmConfigurationError

logger = logging.getLogger(__name__)

AssessmentStatus = Literal["assessed", "failed", "parse_error", "skipped"]


@dataclass(frozen=True)
class ProductAssessmentResult:
    """Assessment outcome bound to one input product."""

    product: ExtractedProduct
    assessment_status: AssessmentStatus
    raw_response: str | None
    normalized_assessment: ParsedAssessment | None = None
    assessment_hint: str | None = None
    error_type: str | None = None
    skip_reason: str | None = None


class AssessmentService:
    """Coordinate per-product LLM risk assessments without batching."""

    def __init__(
        self,
        *,
        llm_client: LlmGateway,
        prompt_builder: Callable[..., str] | None = None,
        max_reason_words: int = 100,
    ) -> None:
        self._llm_client = llm_client
        self._prompt_builder = prompt_builder or build_assessment_prompt
        self._max_reason_words = max_reason_words

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
            skip_reason = _determine_skip_reason(product)
            if skip_reason is not None:
                logger.info(
                    "assessment.skipped",
                    extra={
                        "event": "assessment.skipped",
                        "run_id": run_id,
                        "command": command,
                        "document_name": product.document_name,
                        "product_name": product.product_name,
                        "skip_reason": skip_reason,
                    },
                )
                results.append(
                    ProductAssessmentResult(
                        product=product,
                        assessment_status="skipped",
                        raw_response=None,
                        skip_reason=skip_reason,
                    )
                )
                continue

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
            except LlmConfigurationError as exc:
                logger.error(
                    "assessment.command.failed",
                    extra={
                        "event": "assessment.command.failed",
                        "run_id": run_id,
                        "command": command,
                        "document_name": product.document_name,
                        "product_name": product.product_name,
                        "error_type": type(exc).__name__,
                    },
                )
                raise
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

            try:
                normalized_assessment = parse_assessment_response(
                    response_text=response,
                    max_reason_words=self._max_reason_words,
                )
            except ParsingError as exc:
                logger.warning(
                    "assessment.parsing.failed",
                    extra={
                        "event": "assessment.parsing.failed",
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
                        assessment_status="parse_error",
                        raw_response=response,
                        assessment_hint=str(exc),
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
                    normalized_assessment=normalized_assessment,
                )
            )

        return results

def _determine_skip_reason(product: ExtractedProduct) -> str | None:
    if product.extraction_status != "confirmed":
        return "UNCONFIRMED_EXTRACTION"

    if _is_missing(product.product_name):
        return "MISSING_PRODUCT_NAME"
    if _is_missing(product.supplier):
        return "MISSING_SUPPLIER"
    if _is_missing(product.quantity):
        return "MISSING_QUANTITY"
    return None


def _is_missing(value: str) -> bool:
    normalized = value.strip().upper()
    return normalized in {"", "UNKNOWN", "N/A", "-"}


__all__ = ["AssessmentService", "ProductAssessmentResult", "LlmClientError"]
