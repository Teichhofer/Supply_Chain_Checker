"""Tests for parsing and normalization of LLM extraction output."""

from __future__ import annotations

import pytest

from supply_chain_checker.parsers import ParsingError, parse_extraction_response


def test_parser_normalizes_products_and_keeps_optional_fields() -> None:
    response = (
        '{"products": ['
        '{"product_name": "Copper Wire", "quantity": "20m", "supplier": "ACME", '
        '"manufacturer": "MFG", "article_number": "A-1"}'
        "]}"
    )

    products = parse_extraction_response(response_text=response, document_name="doc.pdf")

    assert len(products) == 1
    assert products[0].product_name == "Copper Wire"
    assert products[0].manufacturer == "MFG"
    assert products[0].article_number == "A-1"
    assert products[0].extraction_status == "confirmed"


def test_parser_marks_incomplete_product_as_uncertain_instead_of_dropping() -> None:
    response = '{"products": [{"product_name": "Bolt", "supplier": "FastCo"}]}'

    products = parse_extraction_response(response_text=response, document_name="invoice.pdf")

    assert len(products) == 1
    assert products[0].quantity == "UNKNOWN"
    assert products[0].extraction_status == "uncertain"
    assert "Missing required fields" in (products[0].extraction_hint or "")


def test_parser_raises_controlled_error_for_invalid_json() -> None:
    with pytest.raises(ParsingError, match="not valid JSON"):
        parse_extraction_response(response_text="not json", document_name="doc.pdf")


def test_parser_raises_controlled_error_for_invalid_status_value() -> None:
    response = (
        '{"products": [{"product_name": "Bolt", "quantity": "1", "supplier": "FastCo", '
        '"extraction_status": "maybe"}]}'
    )

    with pytest.raises(ParsingError, match="extraction_status"):
        parse_extraction_response(response_text=response, document_name="doc.pdf")
