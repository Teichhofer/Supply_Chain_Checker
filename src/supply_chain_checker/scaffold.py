"""Repository and runtime scaffold helpers."""

from __future__ import annotations

from pathlib import Path
from typing import Final

REQUIRED_DIRECTORIES: Final[tuple[str, ...]] = (
    "src",
    "tests",
    "tests/unit",
    "tests/integration",
    "tests/fixtures",
    "config",
    "data",
    "data/input",
    "data/output",
    "data/state",
    "logs",
    "sample_data",
)

GITKEEP_DIRECTORIES: Final[tuple[str, ...]] = (
    "tests/unit",
    "tests/integration",
    "tests/fixtures",
    "data/input",
    "data/output",
    "data/state",
    "logs",
    "sample_data",
)


def ensure_repository_layout(base_dir: Path | None = None) -> None:
    """Create required project directories if they are missing.

    The command is idempotent and keeps the repository layout consistent for
    local CLI runs.
    """

    project_root = (base_dir or Path.cwd()).resolve()

    for relative_dir in REQUIRED_DIRECTORIES:
        (project_root / relative_dir).mkdir(parents=True, exist_ok=True)

    for relative_dir in GITKEEP_DIRECTORIES:
        gitkeep_path = project_root / relative_dir / ".gitkeep"
        gitkeep_path.touch(exist_ok=True)
