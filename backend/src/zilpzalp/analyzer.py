from __future__ import annotations

import datetime
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path

from pypdf import PdfReader

from zilpzalp.config import Config
from zilpzalp.document import Document

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class DateCandidate:
    normalized: str            # date_format-konform (z. B. 2026-01-15)
    raw: str                   # roher Treffer-Text aus dem PDF (zu markierende Teilzeichenkette)
    label: str | None = None   # strukturgestuetzter Kontext (z. B. "Rechnungsdatum")
    snippet: str | None = None # umgebende Zeile aus dem Block; enthaelt raw
    label_key: str | None = None  # i18n-Schluessel fuer app-erzeugte Labels (z. B. "pdf_created")


@dataclass(frozen=True)
class Analysis:
    date_candidates: list[DateCandidate] = field(default_factory=list)
    sender: str | None = None
    doctype: str | None = None
    description: str | None = None
    full_text: str = ""


# --- Eingebaute Datumsformate (laufen immer, ohne Config) ---
_NUMERIC = re.compile(r"\b(\d{1,2})\.(\d{1,2})\.(\d{2,4})\b")
_ISO = re.compile(r"\b(\d{4})-(\d{1,2})-(\d{1,2})\b")
_MONTHS_DE = {
    "januar": 1, "februar": 2, "maerz": 3, "märz": 3, "april": 4, "mai": 5,
    "juni": 6, "juli": 7, "august": 8, "september": 9, "oktober": 10,
    "november": 11, "dezember": 12,
}
_LONG_DE = re.compile(r"\b(\d{1,2})\.?\s+([A-Za-zäöüÄÖÜ]+)\s+(\d{4})\b")


def _two_digit_year(value: int) -> int:
    return 2000 + value if value <= 69 else 1900 + value


def _valid_date(year: int, month: int, day: int) -> datetime.date | None:
    try:
        return datetime.date(year, month, day)
    except ValueError:
        return None


def _numeric_matches(text: str) -> list[tuple[int, int, str, datetime.date]]:
    out: list[tuple[int, int, str, datetime.date]] = []
    for m in _NUMERIC.finditer(text):
        day, month, year = int(m.group(1)), int(m.group(2)), int(m.group(3))
        if year < 100:
            year = _two_digit_year(year)
        d = _valid_date(year, month, day)
        if d is not None:
            out.append((m.start(), m.end(), m.group(0), d))
    for m in _ISO.finditer(text):
        d = _valid_date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        if d is not None:
            out.append((m.start(), m.end(), m.group(0), d))
    for m in _LONG_DE.finditer(text):
        month = _MONTHS_DE.get(m.group(2).lower())
        if month is None:
            continue
        d = _valid_date(int(m.group(3)), month, int(m.group(1)))
        if d is not None:
            out.append((m.start(), m.end(), m.group(0), d))
    return out


def _find_dates_in_text(text: str) -> list[tuple[int, int, str, datetime.date]]:
    """Alle eingebauten Formate; ueberlappende Treffer werden dedupliziert (erster gewinnt)."""
    raw = sorted(_numeric_matches(text), key=lambda t: (t[0], -(t[1] - t[0])))
    kept: list[tuple[int, int, str, datetime.date]] = []
    for start, end, hit, d in raw:
        if any(start < k_end and end > k_start for k_start, k_end, _, _ in kept):
            continue
        kept.append((start, end, hit, d))
    return kept


def _pdf_metadata_dates(path: Path) -> list[tuple[str, datetime.date]]:
    """(label_key, date) for the PDF's CreationDate/ModDate. [] on any read error."""
    try:
        meta = PdfReader(str(path)).metadata
        out: list[tuple[str, datetime.date]] = []
        if meta is not None:
            if meta.creation_date is not None:
                out.append(("pdf_created", meta.creation_date.date()))
            if meta.modification_date is not None:
                out.append(("pdf_modified", meta.modification_date.date()))
        return out
    except Exception:
        logger.debug("PDF-Metadaten von %s nicht lesbar", path, exc_info=True)
        return []


def file_dates(path: Path, config: Config) -> list[DateCandidate]:
    """File-level fallback dates, always appended after text candidates.

    Priority: PDF CreationDate, PDF ModDate, then filesystem mtime. Each entry
    is skipped when unavailable; never raises (the worker must not lose a
    document over a metadata hiccup)."""
    entries = list(_pdf_metadata_dates(Path(path)))
    mtime = datetime.date.fromtimestamp(Path(path).stat().st_mtime)
    entries.append(("file_modified", mtime))
    return [
        DateCandidate(
            normalized=d.strftime(config.date_format),
            raw="",
            label=None,
            snippet=None,
            label_key=key,
        )
        for key, d in entries
    ]


_INLINE_LABEL = re.compile(r"([A-Za-zäöüÄÖÜ][A-Za-zäöüÄÖÜ ]{1,39}?)[:\s]*$")


def _inline_label(text_before: str) -> str | None:
    snippet = text_before.splitlines()[-1] if text_before.splitlines() else text_before
    m = _INLINE_LABEL.search(snippet.strip())
    return m.group(1).strip() if m else None


def _cell_label(cells: list[list[str]], hit: str) -> str | None:
    for r, row in enumerate(cells):
        for c, cell in enumerate(row):
            if hit in cell:
                if c > 0 and row[c - 1].strip():
                    return row[c - 1].strip()          # Nachbarzelle links
                if r > 0 and cells[0][c].strip():
                    return cells[0][c].strip()          # Kopfzelle der Spalte
    return None


_DOCTYPES = {
    "rechnung": "Rechnung", "mahnung": "Mahnung", "vertrag": "Vertrag",
    "bescheid": "Bescheid", "mitteilung": "Mitteilung", "kontoauszug": "Kontoauszug",
    "angebot": "Angebot", "kuendigung": "Kündigung", "kündigung": "Kündigung",
}


def _detect_sender(document: Document) -> str | None:
    page1 = [b for b in document.blocks if b.page == 1 and b.text.strip()]
    if not page1:
        return None
    top = max(page1, key=lambda b: b.bbox[3])     # groesster top-Wert = oberster Block
    return top.text.strip().splitlines()[0].strip()


def _detect_doctype(document: Document) -> str | None:
    headings = [b for b in document.blocks if b.kind == "heading"]
    for block in headings + document.blocks:       # zuerst Ueberschriften, dann beliebig
        low = block.text.lower()
        for key, canonical in _DOCTYPES.items():
            if key in low:
                return canonical
    return None


def _snippet_for(text: str, start: int) -> str:
    """Die Zeile des Blocks, in der der Treffer an Position *start* liegt."""
    line_start = text.rfind("\n", 0, start) + 1
    line_end = text.find("\n", start)
    if line_end == -1:
        line_end = len(text)
    return text[line_start:line_end].strip()


def analyze(document: Document, config: Config) -> Analysis:
    full_text = "\n".join(b.text for b in document.blocks)
    candidates: list[DateCandidate] = []
    last_heading: str | None = None
    for block in document.blocks:
        if block.kind == "heading":
            last_heading = block.text.strip() or last_heading
        for start, _end, hit, d in _find_dates_in_text(block.text):
            if block.kind == "table" and block.cells:
                label = _cell_label(block.cells, hit)
            else:
                label = _inline_label(block.text[:start])
            label = label or last_heading
            candidates.append(
                DateCandidate(
                    normalized=d.strftime(config.date_format),
                    raw=hit,
                    label=label,
                    snippet=_snippet_for(block.text, start),
                )
            )
        for dp in config.date_patterns:
            for m in re.finditer(dp.regex, block.text):
                value = m.group(1) if m.groups() else m.group(0)
                parsed = _find_dates_in_text(value)
                if parsed:
                    _s, _e, hit, d = parsed[0]
                    candidates.append(
                        DateCandidate(
                            normalized=d.strftime(config.date_format),
                            raw=value,
                            label=dp.label,
                            snippet=_snippet_for(block.text, m.start()),
                        )
                    )
    return Analysis(
        date_candidates=candidates,
        sender=_detect_sender(document),
        doctype=_detect_doctype(document),
        full_text=full_text,
    )
