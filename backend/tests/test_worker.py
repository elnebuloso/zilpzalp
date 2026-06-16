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
    from zilpzalp.cache import DocumentCache

    register = Queue()
    cache = DocumentCache(config.paths.cache)
    return register, Worker(register, lambda: config, cache)


def test_process_marks_ready_with_suggestion(tmp_path, config, monkeypatch):
    pdf = Path(config.paths.watchfolder) / "doc.pdf"
    pdf.write_bytes(b"%PDF-1.4")
    doc = Document(blocks=[
        Block(kind="paragraph", text="Rechnungsdatum: 15.01.2026", page=1, bbox=(0, 0, 0, 0)),
    ])
    monkeypatch.setattr(worker_mod, "extract", lambda p, c: doc)

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

    def boom(p, c):
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

    def boom(p, c):
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


def test_process_supplies_fallback_date_when_no_text_date(tmp_path, config, monkeypatch):
    pdf = Path(config.paths.watchfolder) / "nodate.pdf"
    pdf.write_bytes(b"%PDF-1.4")  # invalid PDF -> pypdf falls back to mtime
    doc = Document(blocks=[
        Block(kind="paragraph", text="Kein Datum hier drin.", page=1, bbox=(0, 0, 0, 0)),
    ])
    monkeypatch.setattr(worker_mod, "extract", lambda p, c: doc)

    register, worker = _make_worker(config)
    register.add(pdf)
    worker._process(pdf)

    entry = register.get(pdf)
    assert entry.status == "ready"
    candidates = entry.suggestion.date_candidates
    assert candidates, "expected a fallback candidate when no text date is found"
    assert candidates[0].label_key == "file_modified"
    assert entry.suggestion.preselected_date_index == 0
    assert not entry.suggestion.filename.startswith("__")  # date segment is filled


def test_is_alive_reflects_thread_state(tmp_path):
    from zilpzalp.cache import DocumentCache
    from zilpzalp.queue import Queue
    from zilpzalp.worker import Worker

    worker = Worker(Queue(), lambda: None, DocumentCache(tmp_path))
    assert worker.is_alive() is False  # not started yet
    worker.start()
    assert worker.is_alive() is True
    worker.stop()
    assert worker.is_alive() is False


def test_reanalyze_all_uses_cache_and_skips_extract(tmp_path, config, monkeypatch):
    import json as _json

    pdf = Path(config.paths.watchfolder) / "doc.pdf"
    pdf.write_bytes(b"%PDF-1.4")
    # seed the cache so reanalyze can read it
    Path(config.paths.cache).joinpath("doc.json").write_text(
        _json.dumps({"type": "paragraph", "content": "Rechnungsdatum: 15.01.2026",
                     "page number": 1}),
        encoding="utf-8",
    )

    def boom(p, c):
        raise AssertionError("extract must not be called during reanalyze")

    monkeypatch.setattr(worker_mod, "extract", boom)

    register, worker = _make_worker(config)
    register.add(pdf)
    worker.reanalyze_all()
    # drain the single queued job synchronously
    action, path = worker._work.get_nowait()
    assert action == "reanalyze"
    worker._process(path, reuse=True)

    entry = register.get(pdf)
    assert entry.status == "ready"
    assert entry.suggestion.date_candidates[0].normalized == "2026-01-15"
