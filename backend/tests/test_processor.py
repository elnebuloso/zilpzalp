from pathlib import Path

import pytest

from zilpzalp.config import load_config
from zilpzalp.processor import FileConflictError, ProcessorError, process


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
