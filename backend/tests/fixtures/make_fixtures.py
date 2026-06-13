"""Erzeugt deterministische Test-PDFs. Einmalig per `uv run python` ausführen.

`pypdf` (6.x) hat kein `page.add_text` mehr, daher bauen wir die Seite mit
reportlab und betten echten, extrahierbaren Text ein. Die Datumswerte
erscheinen sowohl als inline-Paragraphen (z.B. `Rechnungsdatum: 15.01.2026`)
als auch in einer echten reportlab-`Table` (mit Gitterlinien), damit
OpenDataLoader die Paragraphen als `paragraph` und die Tabelle als `table`
erkennt. `empty.pdf` enthaelt bewusst keinen Text (simuliert reinen Scan /
unlesbar).
"""
from pathlib import Path

from pypdf import PdfWriter
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

HERE = Path(__file__).parent


def _invoice_pdf(path: Path) -> None:
    styles = getSampleStyleSheet()
    doc = SimpleDocTemplate(str(path), pagesize=A4)
    story = [
        Paragraph("Stadtwerke Musterstadt GmbH", styles["Normal"]),
        Paragraph("Rechnung", styles["Heading1"]),
        Paragraph("Rechnungsdatum: 15.01.2026", styles["Normal"]),
        Spacer(1, 40),
        Paragraph("Leistungsdatum: 31.12.2025", styles["Normal"]),
        Spacer(1, 40),
        Paragraph("Faellig am: 01.02.2026", styles["Normal"]),
        Spacer(1, 40),
        Table(
            [
                ["Rechnungsdatum", "15.01.2026"],
                ["Faellig am", "01.02.2026"],
            ],
            colWidths=[200, 120],
            style=TableStyle(
                [
                    ("GRID", (0, 0), (-1, -1), 1, colors.black),
                    ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
                    ("FONTSIZE", (0, 0), (-1, -1), 11),
                ]
            ),
        ),
        Spacer(1, 12),
        Paragraph("Stromabschlag Januar", styles["Normal"]),
    ]
    doc.build(story)


def main() -> None:
    _invoice_pdf(HERE / "invoice.pdf")
    # PDF ohne jeden eingebetteten Text (simuliert reinen Scan / unlesbar):
    writer = PdfWriter()
    writer.add_blank_page(width=595, height=842)  # A4 in PDF-Punkten
    with (HERE / "empty.pdf").open("wb") as fh:
        writer.write(fh)


if __name__ == "__main__":
    main()
