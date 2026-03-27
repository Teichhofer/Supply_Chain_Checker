"""Parser for LLM extraction responses."""

from __future__ import annotations

import json
import logging
from typing import Any, cast

from supply_chain_checker.models import ExtractedProduct, ExtractionStatus

logger = logging.getLogger(__name__)


class ParsingError(Exception):
    """Raised when structured extraction data cannot be parsed safely."""


_REQUIRED_FIELDS = ("product_name", "quantity", "supplier")


def parse_extraction_response(*, response_text: str, document_name: str) -> list[ExtractedProduct]:
    """Parse LLM JSON response into normalized extracted product records."""

    try:
        payload = json.loads(response_text)
    except json.JSONDecodeError as exc:
        raise ParsingError("LLM extraction response is not valid JSON.") from exc

    raw_products = _extract_products(payload)
    parsed_products: list[ExtractedProduct] = []
    for index, raw_product in enumerate(raw_products):
        if not isinstance(raw_product, dict):
            raise ParsingError(f"Product entry at index {index} must be an object.")
        parsed_products.append(_parse_product(raw_product=raw_product, document_name=document_name))

    return parsed_products


def _extract_products(payload: Any) -> list[Any]:
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict) and isinstance(payload.get("products"), list):
        return cast(list[Any], payload["products"])
    raise ParsingError("LLM extraction response must be a list or an object containing 'products'.")


def _parse_product(*, raw_product: dict[str, Any], document_name: str) -> ExtractedProduct:
    missing_fields = [
        field for field in _REQUIRED_FIELDS if not _normalized_text(raw_product.get(field))
    ]
    status = _normalized_status(raw_product.get("extraction_status"))
    hint = _optional_text(raw_product.get("extraction_hint"))

    if missing_fields:
        status = "uncertain"
        if hint is None:
            hint = f"Missing required fields: {', '.join(missing_fields)}"

    product_name = _normalized_text(raw_product.get("product_name")) or "UNKNOWN"
    quantity = _normalized_text(raw_product.get("quantity")) or "UNKNOWN"
    supplier = _normalized_text(raw_product.get("supplier")) or "UNKNOWN"

    return ExtractedProduct(
        document_name=document_name,
        product_name=product_name,
        quantity=quantity,
        supplier=supplier,
        manufacturer=_optional_text(raw_product.get("manufacturer")),
        article_number=_optional_text(raw_product.get("article_number")),
        extraction_status=status,
        extraction_hint=hint,
    )


def _normalized_status(value: Any) -> ExtractionStatus:
    normalized = _normalized_text(value)
    if normalized is None:
        return "confirmed"
    lowered = normalized.lower()
    if lowered == "confirmed":
        return "confirmed"
    if lowered == "uncertain":
        return "uncertain"
    raise ParsingError("Field 'extraction_status' must be either 'confirmed' or 'uncertain'.")


def _normalized_text(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        text = value.strip()
        return text if text else None
    if isinstance(value, (int, float)):
        return str(value)
    raise ParsingError("Expected text-like value in extraction response.")


def _optional_text(value: Any) -> str | None:
    return _normalized_text(value)
