from __future__ import annotations

import logging
import queue as _queue
import shutil
import threading
from collections.abc import Callable
from pathlib import Path

from zilpzalp.analyzer import analyze, file_dates
from zilpzalp.config import Config
from zilpzalp.extractor import ExtractionError, extract
from zilpzalp.queue import Queue
from zilpzalp.suggestion import suggest

logger = logging.getLogger(__name__)

_SHUTDOWN = object()


class Worker:
    """Single background thread that runs extract → analyze → suggest per PDF.

    The JVM-bound extraction blocks ~1–2 s per document; a single serial worker
    fits the 1-user tool (Design-Spec §2.4). Results are cached as the entry's
    Suggestion in the in-memory register; nothing is written to disk except the
    move to error/ for unreadable PDFs.
    """

    def __init__(
        self,
        register: Queue,
        config_provider: Callable[[], Config],
        cache,
    ) -> None:
        self._register = register
        self._config_provider = config_provider
        self._cache = cache
        self._work: _queue.Queue = _queue.Queue()
        self._thread = threading.Thread(
            target=self._run, name="zilpzalp-worker", daemon=True
        )

    def submit(self, path: Path) -> None:
        """Watcher callback: register (dedup) and enqueue a fresh extraction."""
        if self._register.add(path):
            self._work.put(("extract", Path(path)))

    def reanalyze_all(self) -> None:
        """Re-run analyze+suggest for every entry that has a cached extraction,
        using the current config. Cheap: extraction is skipped."""
        for entry in self._register.list():
            if self._cache.load_document(entry.path) is not None:
                self._work.put(("reanalyze", entry.path))

    def start(self) -> None:
        self._thread.start()

    def stop(self) -> None:
        self._work.put(_SHUTDOWN)
        self._thread.join(timeout=5)

    def is_alive(self) -> bool:
        return self._thread.is_alive()

    def _run(self) -> None:
        while True:
            item = self._work.get()
            if item is _SHUTDOWN:
                return
            action, path = item
            try:
                self._process(path, reuse=(action == "reanalyze"))
            except Exception:  # never let the worker thread die
                logger.exception("Unerwarteter Fehler im Worker bei %s", item)

    def _process(self, path: Path, reuse: bool = False) -> None:
        self._register.mark_analyzing(path)
        config = self._config_provider()
        document = self._cache.load_document(path) if reuse else None
        if document is None:
            try:
                document = extract(path, config.paths.cache)
            except ExtractionError as exc:
                self._move_to_error(path, config)
                self._register.mark_error(path, str(exc))
                return
            except Exception:
                logger.exception("Extraktionsfehler bei %s", path)
                self._register.mark_error(path, "technischer Fehler bei der Analyse")
                return
        try:
            analysis = analyze(document, config, file_dates=file_dates(path, config))
            suggestion = suggest(analysis, config)
        except Exception:
            logger.exception("Analysefehler bei %s", path)
            self._register.mark_error(path, "technischer Fehler bei der Analyse")
            return
        self._register.set_ready(path, suggestion)

    @staticmethod
    def _move_to_error(path: Path, config: Config) -> None:
        try:
            destination = config.paths.error_folder / Path(path).name
            shutil.move(str(path), str(destination))
        except OSError:
            logger.exception("Konnte %s nicht nach error/ verschieben", path)
