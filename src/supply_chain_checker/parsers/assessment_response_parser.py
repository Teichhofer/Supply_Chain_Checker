"""Parser for structured LLM assessment responses."""

from __future__ import annotations

import json
import logging
import math
import re
from dataclasses import dataclass
from typing import Any, cast

from supply_chain_checker.parsers.product_extraction_parser import ParsingError

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ParsedAssessment:
    """Validated and normalized assessment payload."""

    risk_level: int
    price_change_percent: float
    reason: str


def parse_assessment_response(
    *,
    response_text: str,
    max_reason_words: int = 100,
) -> ParsedAssessment:
    """Parse and validate one LLM assessment response."""

    logger.debug(
        "assessment.parsing.started",
        extra={
            "event": "assessment.parsing.started",
        },
    )

    normalized_response_text = _normalize_json_payload_text(response_text)
    try:
        payload = json.loads(normalized_response_text)
    except json.JSONDecodeError as exc:
        _log_parsing_failure(message="LLM assessment response is not valid JSON.")
        raise ParsingError("LLM assessment response is not valid JSON.") from exc

    try:
        raw_assessment = _extract_assessment_payload(payload)
        risk_level = _parse_risk_level(raw_assessment.get("risikostufe"))
        price_change_percent = _parse_price_change_percent(
            raw_assessment.get("preisänderung_prozent")
        )
        reason = _parse_reason(raw_assessment.get("begründung"), max_reason_words=max_reason_words)
    except ParsingError as exc:
        _log_parsing_failure(message=str(exc))
        raise

    logger.debug(
        "assessment.parsing.succeeded",
        extra={
            "event": "assessment.parsing.succeeded",
            "risk_level": risk_level,
        },
    )

    return ParsedAssessment(
        risk_level=risk_level,
        price_change_percent=price_change_percent,
        reason=reason,
    )


def _normalize_json_payload_text(response_text: str) -> str:
    normalized = response_text.strip()
    if not normalized:
        return normalized

    fence_match = re.search(
        r"```(?:json)?\s*(.*?)\s*```", normalized, flags=re.IGNORECASE | re.DOTALL
    )
    if fence_match is not None:
        fenced_payload = fence_match.group(1).strip()
        if fenced_payload:
            return fenced_payload

    json_start = min(
        [index for index in (normalized.find("{"), normalized.find("[")) if index != -1],
        default=-1,
    )
    if json_start == -1:
        return normalized

    json_end = max(normalized.rfind("}"), normalized.rfind("]"))
    if json_end == -1 or json_end < json_start:
        return normalized

    return normalized[json_start : json_end + 1]


def _extract_assessment_payload(payload: Any) -> dict[str, object]:
    if isinstance(payload, dict):
        if isinstance(payload.get("bewertung"), dict):
            return cast(dict[str, object], payload["bewertung"])
        return cast(dict[str, object], payload)

    raise ParsingError("LLM assessment response must be an object.")


def _parse_risk_level(value: object) -> int:
    if value is None:
        raise ParsingError("Field 'risikostufe' is required.")

    if isinstance(value, bool):
        raise ParsingError("Field 'risikostufe' must be an integer between 1 and 10.")

    if isinstance(value, str):
        normalized = value.strip()
        if not normalized:
            raise ParsingError("Field 'risikostufe' is required.")
        qualitative_mapping = {
            "niedrig": 3,
            "low": 3,
            "mittel": 6,
            "medium": 6,
            "moderat": 6,
            "hoch": 8,
            "high": 8,
            "sehr hoch": 10,
            "very high": 10,
        }
        qualitative_risk_level = qualitative_mapping.get(normalized.lower())
        if qualitative_risk_level is not None:
            return qualitative_risk_level
        if not re.fullmatch(r"[+-]?\d+", normalized):
            raise ParsingError("Field 'risikostufe' must be an integer between 1 and 10.")
        parsed = int(normalized)
    elif isinstance(value, int):
        parsed = value
    elif isinstance(value, float):
        if not value.is_integer():
            raise ParsingError("Field 'risikostufe' must be an integer between 1 and 10.")
        parsed = int(value)
    else:
        raise ParsingError("Field 'risikostufe' must be an integer between 1 and 10.")

    if parsed < 1 or parsed > 10:
        raise ParsingError("Field 'risikostufe' must be between 1 and 10.")
    return parsed


def _parse_price_change_percent(value: object) -> float:
    if value is None:
        raise ParsingError("Field 'preisänderung_prozent' is required.")

    if isinstance(value, bool):
        raise ParsingError("Field 'preisänderung_prozent' must be numeric.")

    if isinstance(value, str):
        normalized = value.strip().replace("%", "")
        if not normalized:
            raise ParsingError("Field 'preisänderung_prozent' is required.")
        normalized = normalized.replace(",", ".")
        range_match = re.fullmatch(
            r"\s*([+-]?\d+(?:\.\d+)?)\s*[-–]\s*([+-]?\d+(?:\.\d+)?)\s*",
            normalized,
        )
        if range_match is not None:
            lower_bound = float(range_match.group(1))
            upper_bound = float(range_match.group(2))
            if not (math.isfinite(lower_bound) and math.isfinite(upper_bound)):
                raise ParsingError("Field 'preisänderung_prozent' must be finite.")
            return (lower_bound + upper_bound) / 2.0
        try:
            parsed = float(normalized)
        except ValueError as exc:
            raise ParsingError("Field 'preisänderung_prozent' must be numeric.") from exc
        if not math.isfinite(parsed):
            raise ParsingError("Field 'preisänderung_prozent' must be finite.")
        return parsed

    if isinstance(value, (int, float)):
        parsed = float(value)
        if not math.isfinite(parsed):
            raise ParsingError("Field 'preisänderung_prozent' must be finite.")
        return parsed

    if isinstance(value, dict):
        parsed_from_object = _parse_price_change_from_object(value)
        if parsed_from_object is None:
            raise ParsingError("Field 'preisänderung_prozent' must be numeric.")
        return parsed_from_object

    raise ParsingError("Field 'preisänderung_prozent' must be numeric.")


def _parse_reason(value: object, *, max_reason_words: int) -> str:
    if isinstance(value, str):
        normalized = " ".join(value.split())
    elif isinstance(value, list):
        normalized = " ".join(
            " ".join(str(item).split())
            for item in value
            if isinstance(item, str) and item.strip()
        )
    else:
        raise ParsingError("Field 'begründung' must be a non-empty string.")

    if not normalized:
        raise ParsingError("Field 'begründung' must be a non-empty string.")

    words = normalized.split()
    if len(words) > max_reason_words:
        logger.info(
            "assessment.parsing.reason.truncated",
            extra={
                "event": "assessment.parsing.reason.truncated",
                "max_reason_words": max_reason_words,
                "word_count": len(words),
            },
        )
        return " ".join(words[:max_reason_words])

    return normalized


def _parse_price_change_from_object(value: dict[object, object]) -> float | None:
    preferred_keys = (
        "mittelfristig_3_12_monate",
        "mittelfristig",
        "mittelfristig",
        "kurzfristig_0_3_monate",
        "kurzfristig",
        "min",
        "minimum",
        "max",
        "maximum",
        "stressszenario_spitzenwert",
        "spitzenwert",
        "peak",
    )
    lowered_key_map = {
        str(key).strip().lower(): entry for key, entry in value.items() if isinstance(key, str)
    }
    for key in preferred_keys:
        candidate = lowered_key_map.get(key)
        if candidate is None:
            continue
        try:
            return _parse_price_change_percent(candidate)
        except ParsingError:
            continue

    numeric_values: list[float] = []
    for candidate in value.values():
        try:
            numeric_values.append(_parse_price_change_percent(candidate))
        except ParsingError:
            continue

    if not numeric_values:
        return None

    return sum(numeric_values) / len(numeric_values)


def _log_parsing_failure(*, message: str) -> None:
    logger.warning(
        "assessment.parsing.failed",
        extra={
            "event": "assessment.parsing.failed",
            "error_type": ParsingError.__name__,
            "error_message": message,
        },
    )


__all__ = ["ParsedAssessment", "parse_assessment_response", "ParsingError"]
