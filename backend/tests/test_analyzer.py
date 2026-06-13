from pathlib import Path

from zilpzalp.config import load_config
from zilpzalp.document import Block, Document
from zilpzalp.analyzer import analyze


def _config(tmp_path: Path):
    # Minimal-Config mit existierenden Pflichtpfaden; original_handling=keep -> kein processed.
    (tmp_path / "inbox").mkdir()
    (tmp_path / "error").mkdir()
    cfg = tmp_path / "config.yaml"
    cfg.write_text(
        f"""
paths:
  watchfolder: {tmp_path / "inbox"}
  error_folder: {tmp_path / "error"}
original_handling: keep
summary_mode: never
default_pattern: "{{date}}__{{sender}}_{{doctype}}_{{description}}"
date_format: "%Y-%m-%d"
""",
        encoding="utf-8",
    )
    return load_config(cfg)


def test_numeric_dates_are_collected_and_normalized(tmp_path):
    doc = Document(blocks=[
        Block(kind="paragraph", text="Rechnungsdatum: 15.01.2026", page=1, bbox=(0, 0, 0, 0)),
        Block(kind="paragraph", text="Erstellt am 2025-12-31", page=1, bbox=(0, 0, 0, 0)),
        Block(kind="paragraph", text="Unsinn 32.13.2020 ignorieren", page=1, bbox=(0, 0, 0, 0)),
    ])
    analysis = analyze(doc, _config(tmp_path))
    normalized = [c.normalized for c in analysis.date_candidates]

    assert "2026-01-15" in normalized
    assert "2025-12-31" in normalized
    assert "2020-13-32" not in normalized            # ungueltiges Datum verworfen
    assert all(c.raw for c in analysis.date_candidates)  # roher Treffer-Text erhalten


def test_long_form_german_and_two_digit_year(tmp_path):
    doc = Document(blocks=[
        Block(kind="paragraph", text="Berlin, 5. Maerz 2026", page=1, bbox=(0, 0, 0, 0)),
        Block(kind="paragraph", text="Vertragsbeginn 01.07.99", page=1, bbox=(0, 0, 0, 0)),
    ])
    analysis = analyze(doc, _config(tmp_path))
    normalized = [c.normalized for c in analysis.date_candidates]

    assert "2026-03-05" in normalized            # "5. Maerz 2026"
    assert "1999-07-01" in normalized            # 99 -> 1999 (Pivot 69)


def test_config_date_patterns_add_labeled_candidates(tmp_path):
    (tmp_path / "inbox").mkdir(exist_ok=True)
    (tmp_path / "error").mkdir(exist_ok=True)
    cfg_file = tmp_path / "config.yaml"
    cfg_file.write_text(
        f"""
paths:
  watchfolder: {tmp_path / "inbox"}
  error_folder: {tmp_path / "error"}
original_handling: keep
summary_mode: never
default_pattern: "{{date}}__{{sender}}_{{doctype}}_{{description}}"
date_format: "%Y-%m-%d"
date_patterns:
  - label: leistungsdatum
    regex: 'Leistungszeitraum bis (\\d{{2}}\\.\\d{{2}}\\.\\d{{4}})'
""",
        encoding="utf-8",
    )
    from zilpzalp.config import load_config

    doc = Document(blocks=[
        Block(kind="paragraph", text="Leistungszeitraum bis 31.12.2025", page=1, bbox=(0, 0, 0, 0)),
    ])
    analysis = analyze(doc, load_config(cfg_file))

    leistung = [c for c in analysis.date_candidates if c.label == "leistungsdatum"]
    assert len(leistung) == 1
    assert leistung[0].normalized == "2025-12-31"
