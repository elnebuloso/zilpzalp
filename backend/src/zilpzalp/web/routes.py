from __future__ import annotations

import re
from pathlib import Path

from fastapi import APIRouter
from fastapi.templating import Jinja2Templates

router = APIRouter()
templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))

# status key → (German label, badge css class)
STATUS_META = {
    "pending": ("wartet", "b-wait"),
    "analyzing": ("Analyse", "b-ana"),
    "ready": ("bereit", "b-ready"),
    "error": ("Fehler", "b-err"),
}

ORIGINAL_LABEL = {"move": "verschieben", "delete": "löschen", "keep": "behalten"}
SUMMARY_LABEL = {"always": "immer", "on_conflict": "bei Konflikt", "never": "nie"}

_ISO_DATE = re.compile(r"^(\d{4})-(\d{2})-(\d{2})$")


def german_date(value: str | None) -> str:
    if not value:
        return "—"
    m = _ISO_DATE.match(value)
    if not m:
        return value
    return f"{m.group(3)}.{m.group(2)}.{m.group(1)}"


templates.env.filters["german_date"] = german_date
templates.env.globals["STATUS_META"] = STATUS_META
