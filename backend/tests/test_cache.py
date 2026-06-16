import json
from pathlib import Path

from zilpzalp.cache import DocumentCache


def _odl_json(text):
    return json.dumps({"type": "paragraph", "content": text, "page number": 1})


def test_load_document_returns_none_without_file(tmp_path):
    cache = DocumentCache(tmp_path)
    assert cache.load_document(tmp_path / "missing.pdf") is None


def test_load_document_parses_cached_json(tmp_path):
    (tmp_path / "doc.json").write_text(_odl_json("Hallo Welt"), encoding="utf-8")
    cache = DocumentCache(tmp_path)

    doc = cache.load_document(Path("/inbox/doc.pdf"))

    assert doc is not None
    assert any("Hallo Welt" in b.text for b in doc.blocks)


def test_remove_deletes_both_artifacts(tmp_path):
    (tmp_path / "doc.json").write_text("{}", encoding="utf-8")
    (tmp_path / "doc.md").write_text("# x", encoding="utf-8")
    cache = DocumentCache(tmp_path)

    cache.remove(Path("/inbox/doc.pdf"))

    assert not (tmp_path / "doc.json").exists()
    assert not (tmp_path / "doc.md").exists()


def test_remove_is_idempotent(tmp_path):
    DocumentCache(tmp_path).remove(Path("/inbox/never.pdf"))  # no raise


def test_prune_removes_orphans_keeps_valid(tmp_path):
    for stem in ("keep", "orphan"):
        (tmp_path / f"{stem}.json").write_text("{}", encoding="utf-8")
        (tmp_path / f"{stem}.md").write_text("x", encoding="utf-8")
    cache = DocumentCache(tmp_path)

    cache.prune(["keep.pdf"])

    assert (tmp_path / "keep.json").exists()
    assert not (tmp_path / "orphan.json").exists()
    assert not (tmp_path / "orphan.md").exists()
