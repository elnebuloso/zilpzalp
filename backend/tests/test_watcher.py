import time
from pathlib import Path

from watchdog.events import DirCreatedEvent, FileCreatedEvent, FileMovedEvent

from zilpzalp.watcher import Watcher, _PdfEventHandler, scan_folder


def test_scan_folder_yields_only_pdf_files(tmp_path):
    (tmp_path / "a.pdf").write_bytes(b"%PDF-1.4")
    (tmp_path / "b.PDF").write_bytes(b"%PDF-1.4")
    (tmp_path / "note.txt").write_text("x")
    (tmp_path / "sub").mkdir()

    found = sorted(p.name for p in scan_folder(tmp_path))

    assert found == ["a.pdf", "b.PDF"]


def test_handler_reports_created_pdf():
    seen: list[Path] = []
    handler = _PdfEventHandler(seen.append)

    handler.on_created(FileCreatedEvent("/inbox/new.pdf"))

    assert seen == [Path("/inbox/new.pdf")]


def test_handler_ignores_non_pdf_created():
    seen: list[Path] = []
    handler = _PdfEventHandler(seen.append)

    handler.on_created(FileCreatedEvent("/inbox/note.txt"))

    assert seen == []


def test_handler_ignores_directory_created():
    seen: list[Path] = []
    handler = _PdfEventHandler(seen.append)

    handler.on_created(DirCreatedEvent("/inbox/sub"))

    assert seen == []


def test_handler_reports_moved_pdf_destination():
    seen: list[Path] = []
    handler = _PdfEventHandler(seen.append)

    handler.on_moved(FileMovedEvent("/inbox/.part", "/inbox/final.pdf"))

    assert seen == [Path("/inbox/final.pdf")]


def _wait_for(predicate, timeout=5.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(0.05)
    return predicate()


def test_watcher_reports_existing_and_live_pdfs(tmp_path):
    existing = tmp_path / "old.pdf"
    existing.write_bytes(b"%PDF-1.4")
    seen: list[Path] = []

    watcher = Watcher(tmp_path, seen.append)
    watcher.start()
    try:
        assert _wait_for(
            lambda: existing.resolve() in [p.resolve() for p in seen]
        )

        fresh = tmp_path / "fresh.pdf"
        fresh.write_bytes(b"%PDF-1.4")
        assert _wait_for(
            lambda: fresh.resolve() in [p.resolve() for p in seen]
        )
    finally:
        watcher.stop()
