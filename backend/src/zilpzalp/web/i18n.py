from __future__ import annotations

import json
from pathlib import Path

SUPPORTED: tuple[str, ...] = ("de", "en")
DEFAULT = "de"

_LOCALES_DIR = Path(__file__).parent / "locales"
_CATALOGS: dict[str, dict[str, str]] = {
    lang: json.loads((_LOCALES_DIR / f"{lang}.json").read_text(encoding="utf-8"))
    for lang in SUPPORTED
}


def translate(key: str, lang: str, **vars: object) -> str:
    """Look up ``key`` in ``lang``; fall back to DEFAULT, then to the key itself."""
    catalog = _CATALOGS.get(lang) or _CATALOGS[DEFAULT]
    text = catalog.get(key)
    if text is None:
        text = _CATALOGS[DEFAULT].get(key, key)
    if vars:
        return text.format(**vars)
    return text


def resolve_language(request) -> str:
    """Pick the UI language: cookie ``lang`` wins, else Accept-Language, else DEFAULT."""
    cookie = request.cookies.get("lang")
    if cookie in SUPPORTED:
        return cookie
    header = request.headers.get("accept-language", "")
    for part in header.split(","):
        code = part.split(";")[0].strip().lower()[:2]
        if code in SUPPORTED:
            return code
    return DEFAULT
