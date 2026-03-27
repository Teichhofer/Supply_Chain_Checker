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


def test_parser_accepts_top_level_product_list() -> None:
    response = '[{"product_name":"Screw","quantity":"10","supplier":"FastCo"}]'

    products = parse_extraction_response(response_text=response, document_name="doc.pdf")

    assert len(products) == 1
    assert products[0].product_name == "Screw"


def test_parser_raises_for_non_object_product_entry() -> None:
    response = '{"products": ["invalid"]}'

    with pytest.raises(ParsingError, match="must be an object"):
        parse_extraction_response(response_text=response, document_name="doc.pdf")


def test_parser_normalizes_numeric_fields() -> None:
    response = (
        '{"products": [{"product_name": "Copper", "quantity": 12, "supplier": "ACME", '
        '"manufacturer": 42, "article_number": 12.5}]}'
    )

    products = parse_extraction_response(response_text=response, document_name="doc.pdf")

    assert products[0].quantity == "12"
    assert products[0].manufacturer == "42"
    assert products[0].article_number == "12.5"


def test_parser_raises_for_invalid_payload_shape() -> None:
    with pytest.raises(ParsingError, match="must be a list or an object"):
        parse_extraction_response(response_text='"unexpected"', document_name="doc.pdf")


def test_parser_accepts_explicit_confirmed_and_uncertain_status_values() -> None:
    response = (
        '{"products": ['
        '{"product_name":"A","quantity":"1","supplier":"S","extraction_status":"confirmed"},'
        '{"product_name":"B","quantity":"2","supplier":"S","extraction_status":"uncertain"}'
        "]}"
    )

    products = parse_extraction_response(response_text=response, document_name="doc.pdf")

    assert products[0].extraction_status == "confirmed"
    assert products[1].extraction_status == "uncertain"


def test_parser_raises_for_non_text_like_field_values() -> None:
    response = '{"products": [{"product_name": [], "quantity": "1", "supplier": "S"}]}'

    with pytest.raises(ParsingError, match="Expected text-like value"):
        parse_extraction_response(response_text=response, document_name="doc.pdf")
