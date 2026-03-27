"""Tests for structured assessment response parsing."""

from __future__ import annotations

import pytest

from supply_chain_checker.parsers import ParsingError, parse_assessment_response


def test_parse_assessment_response_validates_and_normalizes_required_fields() -> None:
    parsed = parse_assessment_response(
        response_text='{"risikostufe": "8", "preisänderung_prozent": "-12,5%", "begründung": "  Lieferant   meldet    knappe  Verfügbarkeit. "}'
    )

    assert parsed.risk_level == 8
    assert parsed.price_change_percent == -12.5
    assert parsed.reason == "Lieferant meldet knappe Verfügbarkeit."


@pytest.mark.parametrize(
    ("response_text", "message"),
    [
        ('{"preisänderung_prozent": 1.5, "begründung": "ok"}', "risikostufe"),
        ('{"risikostufe": 11, "preisänderung_prozent": 1.5, "begründung": "ok"}', "between 1 and 10"),
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
            response_text=f'{{"risikostufe": 3, "preisänderung_prozent": 1.5, "begründung": "{reason}"}}'
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
