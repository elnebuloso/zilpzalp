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
