from zilpzalp.queue import Queue, QueueEntry


def test_add_registers_pending_entry(tmp_path):
    pdf = tmp_path / "a.pdf"
    q = Queue()

    assert q.add(pdf) is True

    assert q.get(pdf) == QueueEntry(
        path=pdf.resolve(), status="pending", error_reason=None
    )


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


def test_mark_error_sets_status_and_reason(tmp_path):
    pdf = tmp_path / "a.pdf"
    q = Queue()
    q.add(pdf)

    q.mark_error(pdf, "kein Text-Element")

    entry = q.get(pdf)
    assert entry.status == "error"
    assert entry.error_reason == "kein Text-Element"


def test_remove_deletes_entry(tmp_path):
    pdf = tmp_path / "a.pdf"
    q = Queue()
    q.add(pdf)

    q.remove(pdf)

    assert q.get(pdf) is None
    assert q.list() == []
