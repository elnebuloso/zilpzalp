from zilpzalp.web.naming import render_filename, slug


def test_slug_collapses_whitespace_to_dash():
    assert slug("Stadtwerke  Aurich") == "Stadtwerke-Aurich"
    assert slug("a\tb c") == "a-b-c"


def test_slug_strips_illegal_filename_chars_and_keeps_umlauts():
    assert slug('a/b\\c:d*e?f"g<h>i|j') == "abcdefghij"
    assert slug("Behörden Bescheid") == "Behörden-Bescheid"


def test_render_filename_fills_template_and_slugs_parts():
    name = render_filename(
        "{date}__{sender}_{doctype}_{description}",
        date="2026-01-15",
        sender="Stadtwerke Aurich",
        doctype="Rechnung",
        description="Strom 2025",
        ext=".pdf",
    )
    assert name == "2026-01-15__Stadtwerke-Aurich_Rechnung_Strom-2025.pdf"


def test_render_filename_uses_fallbacks_for_empty_sender_and_doctype():
    name = render_filename(
        "{date}__{sender}_{doctype}_{description}",
        date="2026-01-15",
        sender="",
        doctype="",
        description="",
        ext=".pdf",
    )
    assert name == "2026-01-15__Unbekannt_Dokument_.pdf"
