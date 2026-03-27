"""Product-related domain models."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

ExtractionStatus = Literal["confirmed", "uncertain"]


@dataclass(frozen=True)
class ExtractedProduct:
    """Structured product extracted from one source document."""

    document_name: str
    product_name: str
    quantity: str
    supplier: str
    manufacturer: str | None = None
    article_number: str | None = None
    extraction_status: ExtractionStatus = "confirmed"
    extraction_hint: str | None = None
