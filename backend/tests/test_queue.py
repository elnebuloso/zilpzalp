from zilpzalp.analyzer import DateCandidate
from zilpzalp.queue import Queue
from zilpzalp.suggestion import Suggestion


def test_add_registers_pending_entry_with_id(tmp_path):
    pdf = tmp_path / "a.pdf"
    q = Queue()

    assert q.add(pdf) is True

    entry = q.get(pdf)
    assert entry.path == pdf.resolve()
    assert entry.status == "pending"
    assert entry.suggestion is None
    assert entry.error_reason is None
    assert entry.id  # non-empty


def test_add_is_deduplicated_by_path(tmp_path):
    pdf = tmp_path / "a.pdf"
    q = Queue()

    assert q.add(pdf) is True
    assert q.add(pdf) is False
    assert len(q.list()) == 1


def test_add_dedupes_different_spelling_of_same_path(tmp_path):
    (tmp_path / "sub").mkdir()
    pdf = tmp_path / "sub" / "a.pdf"
    alias = tmp_path / "sub" / "." / "a.pdf"
    q = Queue()

    assert q.add(pdf) is True
    assert q.add(alias) is False
    assert len(q.list()) == 1


def test_id_is_stable_across_transitions(tmp_path):
    pdf = tmp_path / "a.pdf"
    q = Queue()
    q.add(pdf)
    original_id = q.get(pdf).id

    q.mark_analyzing(pdf)
    assert q.get(pdf).id == original_id
    assert q.get(pdf).status == "analyzing"

    q.set_ready(pdf, Suggestion(filename="x.pdf"))
    assert q.get(pdf).id == original_id
    assert q.get(pdf).status == "ready"


def test_set_ready_caches_suggestion(tmp_path):
    pdf = tmp_path / "a.pdf"
    q = Queue()
    q.add(pdf)
    sug = Suggestion(
        filename="2026-01-15__X.pdf",
        date_candidates=[DateCandidate(normalized="2026-01-15", raw="15.01.2026")],
        sender="X",
    )

    q.set_ready(pdf, sug)

    entry = q.get(pdf)
    assert entry.status == "ready"
    assert entry.suggestion is sug


def test_get_by_id_finds_entry(tmp_path):
    pdf = tmp_path / "a.pdf"
    q = Queue()
    q.add(pdf)
    entry_id = q.get(pdf).id

    assert q.get_by_id(entry_id).path == pdf.resolve()
    assert q.get_by_id("does-not-exist") is None


def test_mark_error_sets_status_and_keeps_id(tmp_path):
    pdf = tmp_path / "a.pdf"
    q = Queue()
    q.add(pdf)
    entry_id = q.get(pdf).id

    q.mark_error(pdf, "kein Text-Element")

    entry = q.get(pdf)
    assert entry.status == "error"
    assert entry.error_reason == "kein Text-Element"
    assert entry.id == entry_id


def test_remove_deletes_entry(tmp_path):
    pdf = tmp_path / "a.pdf"
    q = Queue()
    q.add(pdf)

    q.remove(pdf)

    assert q.get(pdf) is None
    assert q.list() == []
