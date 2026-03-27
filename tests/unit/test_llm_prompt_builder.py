"""Tests for extraction prompt building."""

from __future__ import annotations

import pytest

from supply_chain_checker.services.llm.prompts import build_extraction_prompt


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
