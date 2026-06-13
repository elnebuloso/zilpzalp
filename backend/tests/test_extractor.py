import json
from pathlib import Path

from zilpzalp.extractor import document_from_odl

FIXTURES = Path(__file__).parent / "fixtures"


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
