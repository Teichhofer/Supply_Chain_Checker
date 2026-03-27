"""Prompt builders for LLM extraction and assessment workflows."""

from __future__ import annotations


def build_extraction_prompt(
    *,
    template: str,
    document_text: str,
    document_name: str,
    max_products_per_document: int,
) -> str:
    """Build extraction prompt from a configurable template."""

    format_values = {
        "document_text": document_text,
        "document_name": document_name,
        "max_products_per_document": max_products_per_document,
    }
    try:
        return template.format(**format_values)
    except KeyError as exc:
        missing = str(exc).strip("'")
        raise ValueError(f"Unknown placeholder in extraction prompt template: {missing}") from exc
