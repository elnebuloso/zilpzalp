from pathlib import Path

import pytest

from zilpzalp import worker as worker_mod
from zilpzalp.config import load_config
from zilpzalp.document import Block, Document
from zilpzalp.extractor import ExtractionError
from zilpzalp.queue import Queue
from zilpzalp.worker import Worker


@pytest.fixture
def config(valid_config, write_config):
    return load_config(write_config(valid_config))


def _make_worker(config):
    register = Queue()
    return register, Worker(register, lambda: config)


def test_process_marks_ready_with_suggestion(tmp_path, config, monkeypatch):
    pdf = Path(config.paths.watchfolder) / "doc.pdf"
    pdf.write_bytes(b"%PDF-1.4")
    doc = Document(blocks=[
        Block(kind="paragraph", text="Rechnungsdatum: 15.01.2026", page=1, bbox=(0, 0, 0, 0)),
    ])
    monkeypatch.setattr(worker_mod, "extract", lambda p: doc)

    register, worker = _make_worker(config)
    register.add(pdf)
    worker._process(pdf)

    entry = register.get(pdf)
    assert entry.status == "ready"
    assert entry.suggestion is not None
    assert entry.suggestion.date_candidates[0].normalized == "2026-01-15"


def test_process_moves_file_to_error_on_extraction_error(tmp_path, config, monkeypatch):
    pdf = Path(config.paths.watchfolder) / "scan.pdf"
    pdf.write_bytes(b"%PDF-1.4")

    def boom(p):
        raise ExtractionError("Kein Text im PDF 'scan.pdf' gefunden")

    monkeypatch.setattr(worker_mod, "extract", boom)

    register, worker = _make_worker(config)
    register.add(pdf)
    worker._process(pdf)

    entry = register.get(pdf)
    assert entry.status == "error"
    assert "Kein Text" in entry.error_reason
    assert not pdf.exists()
    assert (Path(config.paths.error_folder) / "scan.pdf").exists()


def test_process_marks_transient_error_without_moving_on_unexpected_exception(
    tmp_path, config, monkeypatch
):
    pdf = Path(config.paths.watchfolder) / "weird.pdf"
    pdf.write_bytes(b"%PDF-1.4")

    def boom(p):
        raise RuntimeError("JVM exploded")

    monkeypatch.setattr(worker_mod, "extract", boom)

    register, worker = _make_worker(config)
    register.add(pdf)
    worker._process(pdf)

    entry = register.get(pdf)
    assert entry.status == "error"
    assert "technischer Fehler" in entry.error_reason
    assert pdf.exists()  # not moved: this is a transient runtime error


def test_submit_dedupes_paths(tmp_path, config):
    pdf = Path(config.paths.watchfolder) / "doc.pdf"
    pdf.write_bytes(b"%PDF-1.4")
    register, worker = _make_worker(config)

    worker.submit(pdf)
    worker.submit(pdf)

    assert len(register.list()) == 1
