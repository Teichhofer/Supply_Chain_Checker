"""Run context helpers for correlating logs and artifacts."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import uuid


@dataclass(frozen=True)
class RunContext:
    """Immutable metadata for one CLI run."""

    run_id: str
    started_at_utc: datetime

    @property
    def started_at_iso(self) -> str:
        """Return UTC timestamp in ISO-8601 format."""

        return self.started_at_utc.isoformat().replace("+00:00", "Z")

    @property
    def artifact_timestamp(self) -> str:
        """Return compact UTC timestamp for file names."""

        return self.started_at_utc.strftime("%Y%m%dT%H%M%SZ")

    @property
    def artifact_suffix(self) -> str:
        """Return unique, sortable suffix for run artifacts."""

        return f"{self.artifact_timestamp}_{self.run_id}"


def create_run_context() -> RunContext:
    """Create a new run context with unique ID and UTC timestamp."""

    return RunContext(
        run_id=uuid.uuid4().hex[:12],
        started_at_utc=datetime.now(timezone.utc),
    )
