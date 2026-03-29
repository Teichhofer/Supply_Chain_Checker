"""Tests for structured assessment response parsing."""

from __future__ import annotations

import pytest

from supply_chain_checker.parsers import ParsingError, parse_assessment_response
from supply_chain_checker.parsers.assessment_response_parser import _parse_price_change_percent


def test_parse_assessment_response_validates_and_normalizes_required_fields() -> None:
    parsed = parse_assessment_response(
        response_text=(
            '{"risikostufe": "8", "preisänderung_prozent": "-12,5%", '
            '"begründung": "  Lieferant   meldet    knappe  Verfügbarkeit. "}'
        )
    )

    assert parsed.risk_level == 8
    assert parsed.price_change_percent == -12.5
    assert parsed.reason == "Lieferant meldet knappe Verfügbarkeit."


@pytest.mark.parametrize(
    ("response_text", "message"),
    [
        ('{"preisänderung_prozent": 1.5, "begründung": "ok"}', "risikostufe"),
        (
            '{"risikostufe": 11, "preisänderung_prozent": 1.5, "begründung": "ok"}',
            "between 1 and 10",
        ),
        ('{"risikostufe": 3, "begründung": "ok"}', "preisänderung_prozent"),
        ('{"risikostufe": 3, "preisänderung_prozent": "abc", "begründung": "ok"}', "numeric"),
        ('{"risikostufe": 3, "preisänderung_prozent": 1.5}', "begründung"),
    ],
)
def test_parse_assessment_response_rejects_invalid_required_fields(
    response_text: str,
    message: str,
) -> None:
    with pytest.raises(ParsingError, match=message):
        parse_assessment_response(response_text=response_text)


def test_parse_assessment_response_rejects_overlong_reason() -> None:
    reason = " ".join(["wort"] * 101)

    with pytest.raises(ParsingError, match="at most 100 words"):
        parse_assessment_response(
            response_text=(
                '{"risikostufe": 3, "preisänderung_prozent": 1.5, ' f'"begründung": "{reason}"' "}"
            )
        )


@pytest.mark.parametrize("price_change", ['"NaN"', '"Infinity"', '"-Infinity"'])
def test_parse_assessment_response_rejects_non_finite_price_change(price_change: str) -> None:
    with pytest.raises(ParsingError, match="must be finite"):
        parse_assessment_response(
            response_text=(
                '{"risikostufe": 3, '
                f'"preisänderung_prozent": {price_change}, '
                '"begründung": "ok"}'
            )
        )


def test_parse_assessment_response_rejects_invalid_json() -> None:
    with pytest.raises(ParsingError, match="not valid JSON"):
        parse_assessment_response(response_text="{invalid")


def test_parse_assessment_response_rejects_non_object_payload() -> None:
    with pytest.raises(ParsingError, match="must be an object"):
        parse_assessment_response(response_text='["not-an-object"]')


def test_parse_assessment_response_supports_nested_bewertung_payload() -> None:
    parsed = parse_assessment_response(
        response_text=(
            '{"bewertung":{"risikostufe":"6","preisänderung_prozent":"2,0","begründung":"passt"}}'
        )
    )

    assert parsed.risk_level == 6
    assert parsed.price_change_percent == 2.0
    assert parsed.reason == "passt"


def test_parse_assessment_response_supports_markdown_fenced_json_payload() -> None:
    parsed = parse_assessment_response(
        response_text=(
            "```json\n"
            "{\n"
            '  "risikostufe": "5",\n'
            '  "preisänderung_prozent": 8,\n'
            '  "begründung": "Moderates Risiko."\n'
            "}\n"
            "```"
        )
    )

    assert parsed.risk_level == 5
    assert parsed.price_change_percent == 8.0
    assert parsed.reason == "Moderates Risiko."


def test_parse_assessment_response_supports_json_with_leading_and_trailing_text() -> None:
    parsed = parse_assessment_response(
        response_text=(
            "Hier ist die Bewertung:\n"
            '{"risikostufe":3,"preisänderung_prozent":"1,25","begründung":"Stabile Lage."}\n'
            "Danke."
        )
    )

    assert parsed.risk_level == 3
    assert parsed.price_change_percent == 1.25
    assert parsed.reason == "Stabile Lage."


@pytest.mark.parametrize(
    ("risk_label", "expected"),
    [
        ("hoch", 8),
        ("mittel", 6),
        ("niedrig", 3),
        ("very high", 10),
    ],
)
def test_parse_assessment_response_supports_qualitative_risk_labels(
    risk_label: str,
    expected: int,
) -> None:
    parsed = parse_assessment_response(
        response_text=(
            "{"
            f'"risikostufe": "{risk_label}", '
            '"preisänderung_prozent": 3, '
            '"begründung": "Qualitative Einstufung."'
            "}"
        )
    )

    assert parsed.risk_level == expected


@pytest.mark.parametrize(
    "risk_value",
    ['""', '"abc"', "2.5", "true", "{}", "2.5e1"],
)
def test_parse_assessment_response_rejects_invalid_risk_types(risk_value: str) -> None:
    with pytest.raises(ParsingError, match="risikostufe"):
        parse_assessment_response(
            response_text=(
                "{"
                f'"risikostufe": {risk_value}, '
                '"preisänderung_prozent": 1.5, '
                '"begründung": "ok"'
                "}"
            )
        )


def test_parse_assessment_response_rejects_blank_price_change_string() -> None:
    with pytest.raises(ParsingError, match="preisänderung_prozent"):
        parse_assessment_response(
            response_text='{"risikostufe": 3, "preisänderung_prozent": "   ", "begründung": "ok"}'
        )


def test_parse_assessment_response_rejects_boolean_price_change() -> None:
    with pytest.raises(ParsingError, match="must be numeric"):
        parse_assessment_response(
            response_text='{"risikostufe": 3, "preisänderung_prozent": true, "begründung": "ok"}'
        )


def test_parse_assessment_response_rejects_non_finite_numeric_price_change() -> None:
    with pytest.raises(ParsingError, match="must be finite"):
        _parse_price_change_percent(float("nan"))


def test_parse_assessment_response_rejects_non_numeric_price_change_type() -> None:
    with pytest.raises(ParsingError, match="must be numeric"):
        parse_assessment_response(
            response_text='{"risikostufe": 3, "preisänderung_prozent": {}, "begründung": "ok"}'
        )


def test_parse_assessment_response_rejects_blank_reason() -> None:
    with pytest.raises(ParsingError, match="non-empty string"):
        parse_assessment_response(
            response_text='{"risikostufe": 3, "preisänderung_prozent": 1.5, "begründung": "   "}'
        )
