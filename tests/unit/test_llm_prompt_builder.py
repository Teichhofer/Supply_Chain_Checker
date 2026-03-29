"""Tests for extraction prompt building."""

from __future__ import annotations

import pytest

from supply_chain_checker.models import ExtractedProduct
from supply_chain_checker.services.llm.prompts import (
    build_assessment_prompt,
    build_extraction_prompt,
)


def test_build_extraction_prompt_renders_template_with_expected_fields() -> None:
    prompt = build_extraction_prompt(
        template=(
            "Doc={document_name}; Limit={max_products_per_document}; Content={document_text}"
        ),
        document_text="Widget A x 10",
        document_name="invoice_42.pdf",
        max_products_per_document=5,
    )

    assert "Doc=invoice_42.pdf" in prompt
    assert "Limit=5" in prompt
    assert "Content=Widget A x 10" in prompt


def test_build_extraction_prompt_raises_for_unknown_placeholders() -> None:
    with pytest.raises(ValueError, match="Unknown placeholder"):
        build_extraction_prompt(
            template="{missing_placeholder}",
            document_text="text",
            document_name="doc.pdf",
            max_products_per_document=1,
        )


def test_build_extraction_prompt_appends_context_if_template_has_no_placeholders() -> None:
    prompt = build_extraction_prompt(
        template="Extrahiere Produkte.",
        document_text="Widget A x 10",
        document_name="invoice_42.pdf",
        max_products_per_document=5,
    )

    assert "Extrahiere Produkte." in prompt
    assert "Dokumentname: invoice_42.pdf" in prompt
    assert "Maximale Produktanzahl: 5" in prompt
    assert "Dokumenttext:" in prompt
    assert "Widget A x 10" in prompt
    assert "Antwortformat (nur JSON, keine Markdown-Blöcke):" in prompt


def test_build_assessment_prompt_renders_template_with_expected_fields() -> None:
    prompt = build_assessment_prompt(
        template=(
            "Product={product_name}; Supplier={supplier}; Quantity={quantity}; "
            "Manufacturer={manufacturer}; Article={article_number}; "
            "Doc={document_name}; Status={extraction_status}; Hint={extraction_hint}"
        ),
        product=ExtractedProduct(
            document_name="invoice_42.pdf",
            product_name="Widget A",
            quantity="10",
            supplier="ACME",
            manufacturer="Globex",
            article_number="A-42",
            extraction_status="confirmed",
            extraction_hint="from line item",
        ),
    )

    assert "Product=Widget A" in prompt
    assert "Supplier=ACME" in prompt
    assert "Quantity=10" in prompt
    assert "Manufacturer=Globex" in prompt
    assert "Article=A-42" in prompt
    assert "Doc=invoice_42.pdf" in prompt
    assert "Status=confirmed" in prompt
    assert "Hint=from line item" in prompt


def test_build_assessment_prompt_defaults_optional_fields_to_empty_string() -> None:
    prompt = build_assessment_prompt(
        template="Manufacturer={manufacturer}; Article={article_number}; Hint={extraction_hint}",
        product=ExtractedProduct(
            document_name="invoice_42.pdf",
            product_name="Widget A",
            quantity="10",
            supplier="ACME",
        ),
    )

    assert prompt == "Manufacturer=; Article=; Hint="


def test_build_assessment_prompt_raises_for_unknown_placeholders() -> None:
    with pytest.raises(ValueError, match="Unknown placeholder"):
        build_assessment_prompt(
            template="{missing_placeholder}",
            product=ExtractedProduct(
                document_name="doc.pdf",
                product_name="Widget A",
                quantity="10",
                supplier="ACME",
            ),
        )
