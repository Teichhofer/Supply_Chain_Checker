"""Prompt builders for LLM extraction and assessment workflows."""

from __future__ import annotations

from supply_chain_checker.models import ExtractedProduct


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
        rendered_template = template.format(**format_values).strip()
    except KeyError as exc:
        missing = str(exc).strip("'")
        raise ValueError(f"Unknown placeholder in extraction prompt template: {missing}") from exc

    sections: list[str] = [rendered_template]

    if "{document_name}" not in template:
        sections.append(f"Dokumentname: {document_name}")
    if "{max_products_per_document}" not in template:
        sections.append(f"Maximale Produktanzahl: {max_products_per_document}")
    if "{document_text}" not in template:
        sections.append("Dokumenttext:")
        sections.append(document_text)

    sections.append(
        (
            "Antwortformat (nur JSON, keine Markdown-Blöcke): "
            '[{"product_name":"...","quantity":"...","supplier":"...",'
            '"manufacturer":"...","article_number":"...","extraction_status":"...",'
            '"extraction_hint":"..."}]'
        )
    )

    return "\n\n".join(section for section in sections if section)


def build_assessment_prompt(*, template: str, product: ExtractedProduct) -> str:
    """Build assessment prompt from a configurable template."""

    format_values = {
        "product_name": product.product_name,
        "supplier": product.supplier,
        "quantity": product.quantity,
        "manufacturer": product.manufacturer or "",
        "article_number": product.article_number or "",
        "document_name": product.document_name,
        "extraction_status": product.extraction_status,
        "extraction_hint": product.extraction_hint or "",
    }
    try:
        return template.format(**format_values)
    except KeyError as exc:
        missing = str(exc).strip("'")
        raise ValueError(f"Unknown placeholder in assessment prompt template: {missing}") from exc
