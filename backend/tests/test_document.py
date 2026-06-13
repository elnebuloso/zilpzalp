from zilpzalp.document import Block, Document


def test_block_and_document_construct():
    heading = Block(kind="heading", text="Rechnung", page=1, bbox=(72, 800, 520, 820), level=1)
    table = Block(
        kind="table",
        text="Rechnungsdatum 15.01.2026",
        page=1,
        bbox=(72, 600, 520, 700),
        cells=[["Feld", "Wert"], ["Rechnungsdatum", "15.01.2026"]],
    )
    doc = Document(blocks=[heading, table])

    assert doc.blocks[0].level == 1
    assert doc.blocks[1].cells[1][1] == "15.01.2026"
    assert doc.blocks[0].cells is None
