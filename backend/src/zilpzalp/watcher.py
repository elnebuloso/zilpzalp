from __future__ import annotations

from collections.abc import Callable, Iterator
from pathlib import Path

from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer

PdfCallback = Callable[[Path], None]


def _is_pdf(path: Path) -> bool:
    return path.suffix.lower() == ".pdf"


def scan_folder(folder: Path) -> Iterator[Path]:
    """Yield every existing *.pdf file directly in *folder* (non-recursive).

    This is the start-up rebuild case (Design-Spec §4.2): whatever already lay
    in the watchfolder before the process started (incl. unconfirmed PDFs left
    over from a previous run).
    """
    for entry in sorted(Path(folder).iterdir()):
        if entry.is_file() and _is_pdf(entry):
            yield entry


class _PdfEventHandler(FileSystemEventHandler):
    """Translates watchdog events into PDF-path callbacks. New files arrive as
    created events; downloads and atomic writes often land as a move into
    place, so the move destination is treated the same way."""

    def __init__(self, on_pdf: PdfCallback) -> None:
        self._on_pdf = on_pdf

    def on_created(self, event: FileSystemEvent) -> None:
        if event.is_directory:
            return
        path = Path(event.src_path)
        if _is_pdf(path):
            self._on_pdf(path)

    def on_moved(self, event: FileSystemEvent) -> None:
        if event.is_directory:
            return
        path = Path(event.dest_path)
        if _is_pdf(path):
            self._on_pdf(path)


class Watcher:
    """Watches the watchfolder live (watchdog) and performs the initial scan.

    Both feed the same callback; de-duplication is the queue's job (§4.2). The
    observer is started *before* the scan so a file appearing during start-up
    is never missed — the resulting scan/event overlap is absorbed by the
    queue's path dedup.
    """

    def __init__(self, watchfolder: Path, on_pdf: PdfCallback) -> None:
        self._watchfolder = Path(watchfolder)
        self._on_pdf = on_pdf
        self._observer = Observer()
        self._observer.schedule(
            _PdfEventHandler(on_pdf), str(self._watchfolder), recursive=False
        )

    def start(self) -> None:
        self._observer.start()
        for path in scan_folder(self._watchfolder):
            self._on_pdf(path)

    def stop(self) -> None:
        self._observer.stop()
        self._observer.join()
