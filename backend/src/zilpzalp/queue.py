from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Literal

from zilpzalp.suggestion import Suggestion

QueueStatus = Literal["pending", "analyzing", "ready", "error"]


@dataclass(frozen=True)
class QueueEntry:
    id: str
    path: Path
    status: QueueStatus = "pending"
    suggestion: Suggestion | None = None
    error_reason: str | None = None


class Queue:
    """In-memory register of documents awaiting review.

    The watchfolder is the source of truth (Design-Spec §4.2); this register
    holds the current pending/analyzing/ready/error set and persists nothing.
    Entries are keyed by the resolved path so that the initial scan and live
    watchdog events for the same file never create doubles (§4.2 Idempotenz).
    Each entry carries a stable ``id`` used by the Web-UI routes; the id is
    minted once on first ``add`` and carried through every status transition.
    Thread-safe: the worker transitions entries on a background thread while
    request handlers read on others.
    """

    def __init__(self) -> None:
        self._entries: dict[Path, QueueEntry] = {}
        self._lock = threading.Lock()

    @staticmethod
    def _key(path: Path) -> Path:
        return Path(path).resolve()

    def add(self, path: Path) -> bool:
        """Register *path* as pending. Returns True if newly added, False if a
        deduplicated path was already present."""
        key = self._key(path)
        with self._lock:
            if key in self._entries:
                return False
            self._entries[key] = QueueEntry(id=uuid.uuid4().hex, path=key)
            return True

    def mark_analyzing(self, path: Path) -> None:
        key = self._key(path)
        with self._lock:
            entry = self._entries.get(key)
            if entry is not None:
                self._entries[key] = replace(
                    entry, status="analyzing", error_reason=None
                )

    def set_ready(self, path: Path, suggestion: Suggestion) -> None:
        key = self._key(path)
        with self._lock:
            entry = self._entries.get(key)
            if entry is not None:
                self._entries[key] = replace(
                    entry, status="ready", suggestion=suggestion, error_reason=None
                )

    def mark_error(self, path: Path, reason: str) -> None:
        key = self._key(path)
        with self._lock:
            entry = self._entries.get(key)
            entry_id = entry.id if entry is not None else uuid.uuid4().hex
            self._entries[key] = QueueEntry(
                id=entry_id, path=key, status="error", error_reason=reason
            )

    def remove(self, path: Path) -> None:
        key = self._key(path)
        with self._lock:
            self._entries.pop(key, None)

    def get(self, path: Path) -> QueueEntry | None:
        with self._lock:
            return self._entries.get(self._key(path))

    def get_by_id(self, entry_id: str) -> QueueEntry | None:
        with self._lock:
            for entry in self._entries.values():
                if entry.id == entry_id:
                    return entry
            return None

    def list(self) -> list[QueueEntry]:
        with self._lock:
            return list(self._entries.values())
