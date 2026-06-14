from __future__ import annotations

import re

_ILLEGAL = re.compile(r'[/\\:*?"<>|]')
_WHITESPACE = re.compile(r"\s+")


def slug(value: str) -> str:
    """Filename-safe part: collapse whitespace to '-', drop path-illegal
    characters, keep umlauts. Mirrors the 5a mockup's slug() so the client-side
    live preview and the server-rendered name agree."""
    collapsed = _WHITESPACE.sub("-", (value or "").strip())
    return _ILLEGAL.sub("", collapsed)


def render_filename(
    template: str,
    *,
    date: str,
    sender: str,
    doctype: str,
    description: str,
    ext: str,
) -> str:
    """Render the final filename from the pattern template and the user's
    chosen fields. Empty sender/doctype fall back to Unbekannt/Dokument."""
    stem = template.format(
        date=date,
        sender=slug(sender) or "Unbekannt",
        doctype=slug(doctype) or "Dokument",
        description=slug(description),
    )
    return stem + ext
