from __future__ import annotations

import re
from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates

from zilpzalp.queue import Queue

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


def _counts(queue: Queue) -> dict[str, int]:
    entries = queue.list()
    return {
        "ready": sum(e.status == "ready" for e in entries),
        "analyzing": sum(e.status == "analyzing" for e in entries),
        "pending": sum(e.status == "pending" for e in entries),
        "error": sum(e.status == "error" for e in entries),
    }


def _preselected_date(suggestion) -> str | None:
    if suggestion is None or not suggestion.date_candidates:
        return None
    idx = suggestion.preselected_date_index or 0
    return suggestion.date_candidates[idx].normalized


def _recent(queue: Queue, limit: int = 6):
    return queue.list()[:limit]


def _base_context(request: Request, active: str) -> dict:
    queue: Queue = request.app.state.queue
    counts = _counts(queue)
    return {
        "active": active,
        "open_count": counts["ready"],
        "counts": counts,
    }


@router.get("/")
def overview(request: Request):
    queue: Queue = request.app.state.queue
    config = request.app.state.config
    context = _base_context(request, "overview")
    context.update(
        {
            "recent": _recent(queue),
            "config": config,
            "config_path": str(request.app.state.config_path),
            "original_label": ORIGINAL_LABEL[config.original_handling],
            "summary_label": SUMMARY_LABEL[config.summary_mode],
            "preselected_date": _preselected_date,
        }
    )
    return templates.TemplateResponse(request, "overview.html", context)


@router.get("/partials/overview")
def overview_partial(request: Request):
    queue: Queue = request.app.state.queue
    context = _base_context(request, "overview")
    context.update({"recent": _recent(queue), "preselected_date": _preselected_date})
    return templates.TemplateResponse(request, "_overview.html", context)


@router.get("/queue")
def queue_page(request: Request):
    queue: Queue = request.app.state.queue
    context = _base_context(request, "queue")
    context.update({"entries": queue.list(), "preselected_date": _preselected_date})
    return templates.TemplateResponse(request, "queue.html", context)


@router.get("/partials/queue")
def queue_partial(request: Request):
    queue: Queue = request.app.state.queue
    context = _base_context(request, "queue")
    context.update({"entries": queue.list(), "preselected_date": _preselected_date})
    return templates.TemplateResponse(request, "_queue_list.html", context)
