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


def test_structural_labels_for_multiple_dates(tmp_path):
    doc = Document(blocks=[
        Block(kind="heading", text="Rechnung", page=1, bbox=(0, 800, 500, 820), level=1),
        Block(kind="paragraph", text="Rechnungsdatum: 15.01.2026", page=1, bbox=(0, 700, 500, 720)),
        Block(
            kind="table",
            text="Faellig am 01.02.2026",
            page=1,
            bbox=(0, 600, 500, 660),
            cells=[["Faellig am", "01.02.2026"]],
        ),
        Block(kind="paragraph", text="31.12.2025", page=1, bbox=(0, 500, 500, 520)),
    ])
    analysis = analyze(doc, _config(tmp_path))
    by_date = {c.normalized: c.label for c in analysis.date_candidates}

    assert by_date["2026-01-15"] == "Rechnungsdatum"      # Inline-Text vor dem Treffer
    assert by_date["2026-02-01"] == "Faellig am"          # Nachbarzelle in der Tabellenzeile
    assert by_date["2025-12-31"] == "Rechnung"            # Fallback: zugehoerige Ueberschrift
    # §4.3: nichts entfernt, alle drei Kandidaten vorhanden.
    assert len(analysis.date_candidates) == 3


def test_sender_and_doctype_heuristics(tmp_path):
    doc = Document(blocks=[
        Block(kind="paragraph", text="Stadtwerke Musterstadt GmbH", page=1, bbox=(0, 805, 500, 825)),
        Block(kind="heading", text="Rechnung", page=1, bbox=(0, 760, 200, 780), level=1),
        Block(kind="paragraph", text="Rechnungsdatum: 15.01.2026", page=1, bbox=(0, 700, 500, 720)),
    ])
    analysis = analyze(doc, _config(tmp_path))

    assert analysis.sender == "Stadtwerke Musterstadt GmbH"   # oberster Block auf Seite 1
    assert analysis.doctype == "Rechnung"                      # Heading aus Doctype-Vokabular
    assert "Rechnungsdatum: 15.01.2026" in analysis.full_text


def test_inline_candidate_carries_context_snippet(tmp_path):
    doc = Document(blocks=[
        Block(
            kind="paragraph",
            text="Bitte zahlbar bis zum 02.06.2026 ohne Abzug.",
            page=1,
            bbox=(0, 0, 0, 0),
        ),
    ])
    analysis = analyze(doc, _config(tmp_path))
    c = analysis.date_candidates[0]

    assert c.raw == "02.06.2026"
    assert c.snippet == "Bitte zahlbar bis zum 02.06.2026 ohne Abzug."
    assert c.raw in c.snippet


def test_snippet_is_only_the_hit_line_within_a_block(tmp_path):
    doc = Document(blocks=[
        Block(
            kind="paragraph",
            text="Zeile eins\nRechnungsdatum: 15.01.2026\nZeile drei",
            page=1,
            bbox=(0, 0, 0, 0),
        ),
    ])
    analysis = analyze(doc, _config(tmp_path))
    c = analysis.date_candidates[0]

    assert c.snippet == "Rechnungsdatum: 15.01.2026"


def test_table_candidate_snippet_contains_hit(tmp_path):
    doc = Document(blocks=[
        Block(
            kind="table",
            text="Faellig am 01.02.2026",
            page=1,
            bbox=(0, 0, 0, 0),
            cells=[["Faellig am", "01.02.2026"]],
        ),
    ])
    analysis = analyze(doc, _config(tmp_path))
    c = analysis.date_candidates[0]

    assert c.raw == "01.02.2026"
    assert "01.02.2026" in c.snippet


def test_date_candidate_carries_label_key():
    from zilpzalp.analyzer import DateCandidate

    c = DateCandidate(normalized="2026-01-15", raw="", label_key="pdf_created")
    assert c.label_key == "pdf_created"
    assert c.label is None


def _pdf_with_metadata(path, *, created=None, modified=None):
    """Write a minimal PDF carrying the given PDF-date strings (D:YYYYMMDDHHmmSS)."""
    from pypdf import PdfWriter

    writer = PdfWriter()
    writer.add_blank_page(width=595, height=842)
    meta = {}
    if created is not None:
        meta["/CreationDate"] = created
    if modified is not None:
        meta["/ModDate"] = modified
    if meta:
        writer.add_metadata(meta)
    with open(path, "wb") as fh:
        writer.write(fh)


def test_file_dates_reads_pdf_metadata_in_priority_order(tmp_path):
    from zilpzalp.analyzer import file_dates

    pdf = tmp_path / "doc.pdf"
    _pdf_with_metadata(pdf, created="D:20260115120000", modified="D:20260201120000")

    result = file_dates(pdf, _config(tmp_path))
    by_key = [(c.label_key, c.normalized) for c in result]

    assert by_key[0] == ("pdf_created", "2026-01-15")
    assert by_key[1] == ("pdf_modified", "2026-02-01")
    assert by_key[2][0] == "file_modified"
    assert all(c.raw == "" and c.snippet is None and c.label is None for c in result)


def test_file_dates_falls_back_to_mtime_when_no_metadata(tmp_path):
    from zilpzalp.analyzer import file_dates

    pdf = tmp_path / "nometa.pdf"
    _pdf_with_metadata(pdf)  # blank PDF, no /CreationDate or /ModDate

    result = file_dates(pdf, _config(tmp_path))
    keys = [c.label_key for c in result]

    assert keys == ["file_modified"]


def test_file_dates_falls_back_to_mtime_when_pdf_unreadable(tmp_path):
    from zilpzalp.analyzer import file_dates

    junk = tmp_path / "broken.pdf"
    junk.write_bytes(b"%PDF-1.4 not a real pdf")

    result = file_dates(junk, _config(tmp_path))
    keys = [c.label_key for c in result]

    assert keys == ["file_modified"]


def test_file_dates_returns_only_metadata_when_file_vanishes(tmp_path):
    from zilpzalp.analyzer import file_dates

    pdf = tmp_path / "gone.pdf"
    _pdf_with_metadata(pdf, created="D:20260115120000")
    # read metadata-bearing copy into memory is not needed; PdfReader runs first,
    # then stat() — simulate the file vanishing by deleting before the call.
    pdf.unlink()
    result = file_dates(pdf, _config(tmp_path))
    assert [c.label_key for c in result] == []  # both PDF read and stat fail -> empty


def test_analyze_appends_file_dates_after_text_dates(tmp_path):
    from zilpzalp.analyzer import DateCandidate, analyze

    doc = Document(blocks=[
        Block(kind="paragraph", text="Rechnungsdatum: 15.01.2026", page=1, bbox=(0, 0, 0, 0)),
    ])
    extra = [DateCandidate(normalized="2020-07-09", raw="", label_key="file_modified")]

    analysis = analyze(doc, _config(tmp_path), file_dates=extra)
    normalized = [c.normalized for c in analysis.date_candidates]

    assert normalized == ["2026-01-15", "2020-07-09"]   # text first, file date appended


def test_analyze_dedups_file_date_equal_to_text_date(tmp_path):
    from zilpzalp.analyzer import DateCandidate, analyze

    doc = Document(blocks=[
        Block(kind="paragraph", text="Rechnungsdatum: 15.01.2026", page=1, bbox=(0, 0, 0, 0)),
    ])
    extra = [DateCandidate(normalized="2026-01-15", raw="", label_key="pdf_created")]

    analysis = analyze(doc, _config(tmp_path), file_dates=extra)

    assert [c.normalized for c in analysis.date_candidates] == ["2026-01-15"]  # no duplicate


def test_analyze_without_file_dates_is_unchanged(tmp_path):
    from zilpzalp.analyzer import analyze

    doc = Document(blocks=[
        Block(kind="paragraph", text="Rechnungsdatum: 15.01.2026", page=1, bbox=(0, 0, 0, 0)),
    ])
    analysis = analyze(doc, _config(tmp_path))

    assert [c.normalized for c in analysis.date_candidates] == ["2026-01-15"]
