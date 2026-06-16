import json
from pathlib import Path

import pytest

from zilpzalp.extractor import ExtractionError, document_from_odl, extract

FIXTURES = Path(__file__).parent / "fixtures"


def test_extract_writes_cache_and_returns_document(tmp_path, monkeypatch):
    import zilpzalp.extractor as extractor_mod

    pdf = tmp_path / "rechnung.pdf"
    pdf.write_bytes(b"%PDF-1.4")
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir(exist_ok=True)

    def fake_convert(*, input_path, output_dir, format):
        out = Path(output_dir)
        (out / "rechnung.json").write_text(
            json.dumps({"type": "paragraph", "content": "Datum 15.01.2026",
                        "page number": 1}),
            encoding="utf-8",
        )
        (out / "rechnung.md").write_text("# Rechnung\n15.01.2026", encoding="utf-8")

    monkeypatch.setattr(extractor_mod.opendataloader_pdf, "convert", fake_convert)

    doc = extract(pdf, cache_dir)

    assert any("15.01.2026" in b.text for b in doc.blocks)
    assert (cache_dir / "rechnung.json").exists()
    assert (cache_dir / "rechnung.md").read_text(encoding="utf-8").startswith("# Rechnung")


def test_document_from_odl_simple_elements():
    data = json.loads((FIXTURES / "invoice.odl.json").read_text(encoding="utf-8"))
    doc = document_from_odl(data)

    # Alle Block-Texte zusammengezogen müssen die eingebetteten Zeilen enthalten.
    full = "\n".join(b.text for b in doc.blocks)
    assert "Rechnungsdatum: 15.01.2026" in full
    assert "Leistungsdatum: 31.12.2025" in full
    assert "Stadtwerke" in full
    # Mindestens eine Überschrift ("Rechnung") wurde als heading erkannt.
    assert any(b.kind == "heading" for b in doc.blocks)
    # Blocks tragen 1-indizierte Seitenzahlen.
    assert all(b.page >= 1 for b in doc.blocks)


def test_document_from_odl_table_cells_when_present():
    data = json.loads((FIXTURES / "invoice.odl.json").read_text(encoding="utf-8"))
    doc = document_from_odl(data)

    tables = [b for b in doc.blocks if b.kind == "table"]
    if not tables:  # Fixture enthält (noch) keine Tabelle -> Test ist dann nicht aussagekräftig.
        import pytest

        pytest.skip("Fixture enthaelt keine Tabelle; siehe make_fixtures.py")

    table = tables[0]
    assert table.cells is not None
    # Jede Zeile ist eine Liste von Zell-Strings; mindestens eine Zelle traegt ein Datum.
    flat = [cell for row in table.cells for cell in row]
    assert any("15.01.2026" in cell for cell in flat)
    # Der Block-Text enthaelt die Zell-Inhalte (fuer die Volltextsuche spaeter).
    assert "15.01.2026" in table.text


@pytest.mark.integration
def test_extract_real_pdf_returns_document(tmp_path):
    doc = extract(FIXTURES / "invoice.pdf", tmp_path)
    full = "\n".join(b.text for b in doc.blocks)
    assert "15.01.2026" in full


@pytest.mark.integration
def test_extract_pdf_without_text_raises(tmp_path):
    with pytest.raises(ExtractionError):
        extract(FIXTURES / "empty.pdf", tmp_path)
