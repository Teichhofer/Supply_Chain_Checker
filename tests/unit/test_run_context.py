"""Tests for run context creation."""

from __future__ import annotations

from datetime import UTC

from supply_chain_checker.run_context import create_run_context


def test_create_run_context_generates_utc_timestamp_and_id() -> None:
    context = create_run_context()

    assert len(context.run_id) == 12
    assert context.started_at_utc.tzinfo == UTC
    assert context.started_at_iso.endswith("Z")
    assert context.artifact_suffix.endswith(context.run_id)
