from __future__ import annotations

import datetime
import re
from dataclasses import dataclass, field

from zilpzalp.config import Config
from zilpzalp.document import Document


@dataclass(frozen=True)
class DateCandidate:
    normalized: str            # date_format-konform (z. B. 2026-01-15)
    raw: str                   # roher Treffer-Text aus dem PDF
    label: str | None = None   # strukturgestuetzter Kontext (z. B. "Rechnungsdatum")


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


def analyze(document: Document, config: Config) -> Analysis:
    full_text = "\n".join(b.text for b in document.blocks)
    candidates: list[DateCandidate] = []
    for block in document.blocks:
        for _start, _end, hit, d in _find_dates_in_text(block.text):
            candidates.append(
                DateCandidate(normalized=d.strftime(config.date_format), raw=hit, label=None)
            )
    return Analysis(date_candidates=candidates, full_text=full_text)
