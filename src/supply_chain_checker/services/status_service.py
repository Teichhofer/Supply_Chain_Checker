"""State tracking for already processed PDFs."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

logger = logging.getLogger(__name__)


class StatusTrackingError(Exception):
    """Raised when status tracking data cannot be read or persisted."""


@dataclass(frozen=True)
class ProcessedFileStatus:
    """Persisted status entry for a processed file."""

    file_name: str
    processed_at_utc: str
    file_hash: str | None = None


class StatusService:
    """Load and persist file-processing status between runs."""

    def __init__(self, status_file_path: Path) -> None:
        self._status_file_path = status_file_path
        self._entries_by_file: dict[str, ProcessedFileStatus] = {}

    def load(
        self,
        *,
        on_corrupt_file: Literal["abort", "fallback_empty"] = "abort",
    ) -> dict[str, ProcessedFileStatus]:
        """Load status entries from disk and cache them in memory."""

        if not self._status_file_path.exists():
            logger.info(
                "status.load.empty",
                extra={
                    "event": "status.load.empty",
                    "status_file_path": str(self._status_file_path),
                },
            )
            self._entries_by_file = {}
            return dict(self._entries_by_file)

        try:
            loaded_entries = self._read_entries_from_status_file()
        except StatusTrackingError as exc:
            should_fallback = on_corrupt_file == "fallback_empty"
            logger.log(
                logging.WARNING if should_fallback else logging.ERROR,
                "status.load.corrupt",
                extra={
                    "event": "status.load.corrupt",
                    "status_file_path": str(self._status_file_path),
                    "error_type": type(exc.__cause__ or exc).__name__,
                    "error_domain": "status",
                    "fallback_applied": should_fallback,
                    "on_corrupt_file": on_corrupt_file,
                },
            )
            if should_fallback:
                self._entries_by_file = {}
                return dict(self._entries_by_file)
            raise

        self._entries_by_file = loaded_entries
        logger.info(
            "status.load.succeeded",
            extra={
                "event": "status.load.succeeded",
                "status_file_path": str(self._status_file_path),
                "processed_files_count": len(self._entries_by_file),
            },
        )
        return dict(self._entries_by_file)

    def _read_entries_from_status_file(self) -> dict[str, ProcessedFileStatus]:
        try:
            raw_payload = json.loads(self._status_file_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise StatusTrackingError("Could not read status file.") from exc

        if not isinstance(raw_payload, dict):
            raise StatusTrackingError("Status file format is invalid.")

        entries = raw_payload.get("processed_files", [])
        if not isinstance(entries, list):
            raise StatusTrackingError("Status file format is invalid.")

        loaded_entries: dict[str, ProcessedFileStatus] = {}
        for item in entries:
            if not isinstance(item, dict):
                raise StatusTrackingError("Status entry must be a mapping.")

            file_name = item.get("file_name")
            processed_at_utc = item.get("processed_at_utc")
            file_hash = item.get("file_hash")

            if not isinstance(file_name, str) or not file_name.strip():
                raise StatusTrackingError("Status entry has an invalid file_name.")
            if not isinstance(processed_at_utc, str) or not processed_at_utc.strip():
                raise StatusTrackingError("Status entry has an invalid processed_at_utc.")
            if file_hash is not None and not isinstance(file_hash, str):
                raise StatusTrackingError("Status entry has an invalid file_hash.")

            loaded_entries[file_name] = ProcessedFileStatus(
                file_name=file_name,
                processed_at_utc=processed_at_utc,
                file_hash=file_hash,
            )
        return loaded_entries

    def mark_processed(self, file_name: str, *, file_hash: str | None = None) -> None:
        """Upsert an entry for a processed file."""

        if not file_name.strip():
            raise StatusTrackingError("file_name must be a non-empty string.")

        timestamp = datetime.now(tz=UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
        self._entries_by_file[file_name] = ProcessedFileStatus(
            file_name=file_name,
            processed_at_utc=timestamp,
            file_hash=file_hash,
        )

    def persist(self) -> None:
        """Write the in-memory status entries to disk."""

        payload = {
            "processed_files": [
                {
                    "file_name": entry.file_name,
                    "processed_at_utc": entry.processed_at_utc,
                    "file_hash": entry.file_hash,
                }
                for entry in sorted(
                    self._entries_by_file.values(),
                    key=lambda value: value.file_name,
                )
            ]
        }

        self._status_file_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            self._status_file_path.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
        except OSError as exc:
            logger.error(
                "status.persist.failed",
                extra={
                    "event": "status.persist.failed",
                    "status_file_path": str(self._status_file_path),
                    "error_type": type(exc).__name__,
                },
            )
            raise StatusTrackingError("Could not persist status file.") from exc

        logger.info(
            "status.persist.succeeded",
            extra={
                "event": "status.persist.succeeded",
                "status_file_path": str(self._status_file_path),
                "processed_files_count": len(self._entries_by_file),
            },
        )
