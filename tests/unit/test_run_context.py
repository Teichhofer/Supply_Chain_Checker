"""Tests for run context generation."""

from __future__ import annotations

from datetime import UTC

from supply_chain_checker.run_context import create_run_context


def test_create_run_context_sets_unique_id_and_utc_timestamp() -> None:
    first = create_run_context()
    second = create_run_context()

    assert first.run_id != second.run_id
    assert len(first.run_id) == 12
    assert first.started_at_utc.tzinfo is UTC
    assert first.timestamp_compact.endswith("Z")
