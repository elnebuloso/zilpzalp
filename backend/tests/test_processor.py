from pathlib import Path

import pytest

from zilpzalp.config import load_config
from zilpzalp.processor import FileConflictError, ProcessorError, process, remove


def _config(tmp_path: Path, when_filed: str = "delete", when_removed: str = "trash", extra: str = ""):
    """Build a validated Config; paths come from env (env_paths fixture)."""
    cfg = tmp_path / "config.yaml"
    cfg.write_text(
        f"""
originals:
  when_filed: {when_filed}
  when_removed: {when_removed}
summary_mode: never
default_pattern: standard
date_format: "%Y-%m-%d"
patterns:
  standard:
    template: "{{date}}__{{sender}}_{{doctype}}_{{description}}"
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


def test_delete_removes_original_after_copy(tmp_path):
    config = _config(tmp_path, when_filed="delete")
    source = _source(tmp_path)
    target = _target(tmp_path, "finanzen")

    result = process(source, "doc.pdf", [target], config)

    assert (target / "doc.pdf").read_bytes() == b"%PDF-1.4 hello"
    assert not source.exists()
    assert result.original_action == "deleted"
    assert result.original_destination is None


def test_trash_moves_original_after_copy(tmp_path):
    config = _config(tmp_path, when_filed="trash")
    source = _source(tmp_path, "orig.pdf")
    target = _target(tmp_path, "finanzen")

    result = process(source, "doc.pdf", [target], config)

    assert (target / "doc.pdf").exists()
    assert not source.exists()
    trashed = Path(config.paths.trash) / "orig.pdf"
    assert trashed.read_bytes() == b"%PDF-1.4 hello"
    assert result.original_action == "trashed"
    assert result.original_destination == trashed


def test_trash_uses_unique_name_on_collision(tmp_path):
    config = _config(tmp_path, when_filed="trash")
    source = _source(tmp_path, "orig.pdf")
    target = _target(tmp_path, "finanzen")
    (Path(config.paths.trash) / "orig.pdf").write_bytes(b"old")

    result = process(source, "doc.pdf", [target], config)

    assert (Path(config.paths.trash) / "orig.pdf").read_bytes() == b"old"  # untouched
    assert result.original_destination == Path(config.paths.trash) / "orig (1).pdf"
    assert result.original_destination.read_bytes() == b"%PDF-1.4 hello"


def test_remove_deletes_without_copy(tmp_path):
    config = _config(tmp_path, when_removed="delete")
    source = _source(tmp_path)

    result = remove(source, config)

    assert not source.exists()
    assert result.copied == []
    assert result.original_action == "deleted"


def test_remove_trashes_without_copy(tmp_path):
    config = _config(tmp_path, when_removed="trash")
    source = _source(tmp_path, "orig.pdf")

    result = remove(source, config)

    assert not source.exists()
    assert (Path(config.paths.trash) / "orig.pdf").exists()
    assert result.original_action == "trashed"


def test_remove_uses_when_removed_not_when_filed(tmp_path):
    # when_filed=delete must NOT affect removal; when_removed=trash wins.
    config = _config(tmp_path, when_filed="delete", when_removed="trash")
    source = _source(tmp_path, "orig.pdf")

    remove(source, config)

    assert (Path(config.paths.trash) / "orig.pdf").exists()


def test_remove_tolerates_missing_original(tmp_path):
    # e.g. an error entry whose file was already moved to error/.
    config = _config(tmp_path, when_removed="trash")
    missing = tmp_path / "inbox" / "gone.pdf"

    result = remove(missing, config)  # must not raise

    assert result.copied == []
    assert result.original_action == "deleted"
    assert result.original_destination is None


def test_copies_to_multiple_targets(tmp_path):
    config = _config(tmp_path, when_filed="delete")
    source = _source(tmp_path)
    t1 = _target(tmp_path, "finanzen")
    t2 = _target(tmp_path, "versicherungen")

    result = process(source, "doc.pdf", [t1, t2], config)

    assert (t1 / "doc.pdf").read_bytes() == b"%PDF-1.4 hello"
    assert (t2 / "doc.pdf").read_bytes() == b"%PDF-1.4 hello"
    assert result.copied == [t1 / "doc.pdf", t2 / "doc.pdf"]


def test_conflict_at_target_raises_and_leaves_original(tmp_path):
    config = _config(tmp_path, when_filed="delete")
    source = _source(tmp_path)
    target = _target(tmp_path, "finanzen")
    existing = target / "doc.pdf"
    existing.write_bytes(b"already here")

    with pytest.raises(FileConflictError):
        process(source, "doc.pdf", [target], config)

    assert existing.read_bytes() == b"already here"   # not overwritten (no auto-suffix)
    assert source.exists()                            # delete did not run


def test_conflict_preflight_prevents_partial_copy(tmp_path):
    config = _config(tmp_path, when_filed="delete")
    source = _source(tmp_path)
    t1 = _target(tmp_path, "finanzen")
    t2 = _target(tmp_path, "versicherungen")
    (t2 / "doc.pdf").write_bytes(b"already here")      # conflict in the SECOND target

    with pytest.raises(FileConflictError):
        process(source, "doc.pdf", [t1, t2], config)

    assert not (t1 / "doc.pdf").exists()               # first target NOT written either
    assert source.exists()


def test_empty_targets_raises_and_keeps_original(tmp_path):
    config = _config(tmp_path, when_filed="delete")
    source = _source(tmp_path)

    with pytest.raises(ProcessorError):
        process(source, "doc.pdf", [], config)

    assert source.exists()        # no copy => never delete the original


def test_missing_target_dir_raises_and_leaves_original(tmp_path):
    config = _config(tmp_path, when_filed="delete")
    source = _source(tmp_path)
    missing = tmp_path / "nope"   # never created

    with pytest.raises(ProcessorError):
        process(source, "doc.pdf", [missing], config)

    assert source.exists()        # original untouched
