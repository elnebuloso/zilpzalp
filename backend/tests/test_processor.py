from pathlib import Path

import pytest

from zilpzalp.config import load_config
from zilpzalp.processor import FileConflictError, process


def _config(tmp_path: Path, original_handling: str = "keep", extra: str = ""):
    """Build a validated Config whose paths point at real temp dirs."""
    for sub in ("inbox", "error", "processed"):
        (tmp_path / sub).mkdir(exist_ok=True)
    cfg = tmp_path / "config.yaml"
    cfg.write_text(
        f"""
paths:
  watchfolder: {tmp_path / "inbox"}
  error_folder: {tmp_path / "error"}
  processed_folder: {tmp_path / "processed"}
original_handling: {original_handling}
summary_mode: never
default_pattern: "{{date}}__{{sender}}_{{doctype}}_{{description}}"
date_format: "%Y-%m-%d"
{extra}
""",
        encoding="utf-8",
    )
    return load_config(cfg)


def _source(tmp_path: Path, name: str = "orig.pdf", content: bytes = b"%PDF-1.4 hello") -> Path:
    p = tmp_path / "inbox" / name
    p.write_bytes(content)
    return p


def _target(tmp_path: Path, name: str) -> Path:
    d = tmp_path / name
    d.mkdir(exist_ok=True)
    return d


def test_copies_to_single_target_and_keeps_original(tmp_path):
    config = _config(tmp_path, "keep")
    source = _source(tmp_path)
    target = _target(tmp_path, "finanzen")

    result = process(source, "2026-01-15__Acme.pdf", [target], config)

    dest = target / "2026-01-15__Acme.pdf"
    assert dest.read_bytes() == b"%PDF-1.4 hello"   # copy created with confirmed name
    assert source.exists()                          # keep: original untouched
    assert result.copied == [dest]
    assert result.original_action == "kept"
    assert result.original_destination is None


def test_copies_to_multiple_targets(tmp_path):
    config = _config(tmp_path, "keep")
    source = _source(tmp_path)
    t1 = _target(tmp_path, "finanzen")
    t2 = _target(tmp_path, "versicherungen")

    result = process(source, "doc.pdf", [t1, t2], config)

    assert (t1 / "doc.pdf").read_bytes() == b"%PDF-1.4 hello"
    assert (t2 / "doc.pdf").read_bytes() == b"%PDF-1.4 hello"
    assert result.copied == [t1 / "doc.pdf", t2 / "doc.pdf"]


def test_move_relocates_original_to_processed(tmp_path):
    config = _config(tmp_path, "move")
    source = _source(tmp_path, "orig.pdf")
    target = _target(tmp_path, "finanzen")

    result = process(source, "doc.pdf", [target], config)

    assert (target / "doc.pdf").exists()                      # copy made
    assert not source.exists()                                # original moved away
    processed = tmp_path / "processed" / "orig.pdf"           # keeps original name
    assert processed.read_bytes() == b"%PDF-1.4 hello"
    assert result.original_action == "moved"
    assert result.original_destination == processed


def test_delete_removes_original(tmp_path):
    config = _config(tmp_path, "delete")
    source = _source(tmp_path)
    target = _target(tmp_path, "finanzen")

    result = process(source, "doc.pdf", [target], config)

    assert (target / "doc.pdf").exists()                      # copy made
    assert not source.exists()                                # original deleted
    assert result.original_action == "deleted"
    assert result.original_destination is None


def test_conflict_at_target_raises_and_leaves_original(tmp_path):
    config = _config(tmp_path, "delete")
    source = _source(tmp_path)
    target = _target(tmp_path, "finanzen")
    existing = target / "doc.pdf"
    existing.write_bytes(b"already here")

    with pytest.raises(FileConflictError):
        process(source, "doc.pdf", [target], config)

    assert existing.read_bytes() == b"already here"   # not overwritten (no auto-suffix)
    assert source.exists()                            # delete did not run


def test_conflict_preflight_prevents_partial_copy(tmp_path):
    config = _config(tmp_path, "keep")
    source = _source(tmp_path)
    t1 = _target(tmp_path, "finanzen")
    t2 = _target(tmp_path, "versicherungen")
    (t2 / "doc.pdf").write_bytes(b"already here")      # conflict in the SECOND target

    with pytest.raises(FileConflictError):
        process(source, "doc.pdf", [t1, t2], config)

    assert not (t1 / "doc.pdf").exists()               # first target NOT written either
    assert source.exists()
