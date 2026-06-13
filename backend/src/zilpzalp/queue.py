from __future__ import annotations

import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

QueueStatus = Literal["pending", "error"]


@dataclass(frozen=True)
class QueueEntry:
    path: Path
    status: QueueStatus = "pending"
    error_reason: str | None = None


class Queue:
    """In-memory register of documents awaiting review.

    The watchfolder is the source of truth (Design-Spec §4.2); this register
    holds no more than the current pending/error set and persists nothing.
    Entries are keyed by the resolved path so that the initial scan and live
    watchdog events for the same file never create doubles (§4.2 Idempotenz).
    Thread-safe: watchdog delivers events on a background thread while the
    initial scan and request handlers run on others.
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
            self._entries[key] = QueueEntry(path=key)
            return True

    def mark_error(self, path: Path, reason: str) -> None:
        key = self._key(path)
        with self._lock:
            self._entries[key] = QueueEntry(
                path=key, status="error", error_reason=reason
            )

    def remove(self, path: Path) -> None:
        key = self._key(path)
        with self._lock:
            self._entries.pop(key, None)

    def get(self, path: Path) -> QueueEntry | None:
        with self._lock:
            return self._entries.get(self._key(path))

    def list(self) -> list[QueueEntry]:
        with self._lock:
            return list(self._entries.values())
