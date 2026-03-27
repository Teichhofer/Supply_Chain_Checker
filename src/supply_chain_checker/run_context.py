"""Run context utilities for correlating logs and output artefacts."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime


@dataclass(frozen=True)
class RunContext:
    """Immutable context metadata for one CLI run."""

    run_id: str
    started_at_utc: datetime

    @property
    def timestamp_compact(self) -> str:
        """Return a filesystem-safe UTC timestamp."""

        return self.started_at_utc.strftime("%Y%m%dT%H%M%SZ")


def create_run_context() -> RunContext:
    """Create a new run context with unique run id and UTC timestamp."""

    return RunContext(
        run_id=uuid.uuid4().hex[:12],
        started_at_utc=datetime.now(UTC),
    )
