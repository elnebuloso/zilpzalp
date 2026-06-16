from __future__ import annotations

import datetime
import os
import tempfile
from pathlib import Path
from urllib.parse import quote

from fastapi import APIRouter, File, Form, Request, UploadFile
from fastapi.responses import JSONResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates

from zilpzalp.config import Config, ConfigError, save_config
from zilpzalp.processor import FileConflictError, ProcessorError, process
from zilpzalp.queue import Queue
from zilpzalp.web.i18n import SUPPORTED, resolve_language, translate
from zilpzalp.web.naming import render_filename

router = APIRouter()
templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))

# status key → badge css class (labels live in the i18n catalogs as status.<key>)
STATUS_BADGE = {
    "pending": "b-wait",
    "analyzing": "b-ana",
    "ready": "b-ready",
    "error": "b-err",
}

templates.env.globals["STATUS_BADGE"] = STATUS_BADGE

PDF_MAGIC = b"%PDF"
_UPLOAD_CHUNK = 1024 * 1024


def _unique_pdf_name(folder: Path, name: str) -> Path:
    """Return a non-existing path in *folder* for *name*, appending ' (n)' to
    the stem on collision so an upload never overwrites an existing inbox file."""
    candidate = folder / name
    if not candidate.exists():
        return candidate
    stem, suffix = candidate.stem, candidate.suffix
    counter = 1
    while True:
        candidate = folder / f"{stem} ({counter}){suffix}"
        if not candidate.exists():
            return candidate
        counter += 1


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
    lang = resolve_language(request)
    return {
        "active": active,
        "open_count": counts["ready"],
        "counts": counts,
        "flash": request.query_params.get("flash"),
        "flash_kind": request.query_params.get("kind", "ok"),
        "lang": lang,
        "t": lambda key, **kw: translate(key, lang, **kw),
    }


def _safe_next(next: str) -> str:
    # Only allow same-site absolute paths; reject protocol-relative ("//host")
    # and backslash-escaped ("/\\host") URLs that browsers treat as external.
    if next.startswith("/") and not next.startswith(("//", "/\\")):
        return next
    return "/"


@router.get("/lang/{code}")
def set_language(code: str, next: str = "/"):
    target = _safe_next(next)
    response = RedirectResponse(target, status_code=303)
    if code in SUPPORTED:
        response.set_cookie("lang", code, max_age=31_536_000, samesite="lax")
    return response


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


@router.get("/review/{entry_id}")
def review_page(request: Request, entry_id: str):
    queue: Queue = request.app.state.queue
    entry = queue.get_by_id(entry_id)
    if entry is None or entry.status != "ready" or entry.suggestion is None:
        return RedirectResponse("/queue", status_code=303)
    config = request.app.state.config
    suggestion = entry.suggestion
    recommended = {str(p) for p in suggestion.target_paths}
    context = _base_context(request, "queue")
    lang = context["lang"]
    context.update(
        {
            "entry": entry,
            "suggestion": suggestion,
            "config": config,
            "recommended": recommended,
            "ext": entry.path.suffix or ".pdf",
            "preselected_index": suggestion.preselected_date_index or 0,
            "original_label": translate("original." + config.original_handling, lang),
        }
    )
    return templates.TemplateResponse(request, "review.html", context)


def _resolve_template(config: Config, pattern_name: str) -> str:
    for pattern in config.patterns:
        if pattern.name == pattern_name:
            return pattern.template
    return config.default_pattern


def _normalize_date(date_value: str, config: Config) -> str:
    # Both candidate and manual dates arrive as ISO (YYYY-MM-DD); the rename
    # format always comes from config.date_format.
    try:
        parsed = datetime.datetime.strptime(date_value, "%Y-%m-%d").date()
    except ValueError:
        return ""
    return parsed.strftime(config.date_format)


def _build_request_state(request, entry, date_kind, date_value, sender, doctype,
                         description, pattern, targets):
    # date_kind is kept for form round-trip (stored in form_values) but is not
    # used for normalization — both candidate and manual dates arrive as ISO.
    config: Config = request.app.state.config
    date = _normalize_date(date_value, config)
    template = _resolve_template(config, pattern)
    ext = entry.path.suffix or ".pdf"
    filename = render_filename(
        template, date=date, sender=sender, doctype=doctype,
        description=description, ext=ext,
    )
    target_paths = [Path(t) for t in targets]
    conflicts = [t for t in target_paths if (t / filename).exists()]
    return config, filename, target_paths, conflicts


def _summary_response(request, entry, filename, target_paths, conflicts,
                      config, form_values):
    lang = resolve_language(request)
    selected = [target for target in config.targets if target.path in target_paths]
    conflict_set = {str(p) for p in conflicts}
    context = {
        "entry": entry,
        "filename": filename,
        "selected": selected,
        "conflict_set": conflict_set,
        "has_conflict": bool(conflicts),
        "original_label": translate("original." + config.original_handling, lang),
        "form_values": form_values,
        "lang": lang,
        "t": lambda key, **kw: translate(key, lang, **kw),
    }
    return templates.TemplateResponse(request, "_summary_modal.html", context)


def _execute(request, entry, filename, target_paths, config):
    queue: Queue = request.app.state.queue
    lang = resolve_language(request)
    process(entry.path, filename, target_paths, config)
    queue.remove(entry.path)
    message = translate("toast.filed", lang, filename=filename)
    resp = Response(status_code=200)
    resp.headers["HX-Redirect"] = "/queue?flash=" + quote(message) + "&kind=ok"
    return resp


def _execute_guarded(request, entry, filename, target_paths, conflicts, config,
                     form_values):
    if conflicts:
        return _summary_response(
            request, entry, filename, target_paths, conflicts, config, form_values
        )
    try:
        return _execute(request, entry, filename, target_paths, config)
    except FileConflictError as exc:
        # a conflicting file appeared between check and copy; mark its target dir
        return _summary_response(
            request, entry, filename, target_paths, [exc.destination.parent],
            config, form_values
        )
    except ProcessorError as exc:
        message = translate("toast.file_error", resolve_language(request), error=str(exc))
        return Response(
            status_code=200,
            headers={
                "HX-Redirect": f"/review/{entry.id}?flash="
                + quote(message) + "&kind=err"
            },
        )


@router.post("/documents/{entry_id}/confirm")
def confirm(
    request: Request,
    entry_id: str,
    date_kind: str = Form("candidate"),
    date_value: str = Form(""),
    sender: str = Form(""),
    doctype: str = Form(""),
    description: str = Form(""),
    pattern: str = Form(""),
    targets: list[str] = Form(default=[]),
):
    queue: Queue = request.app.state.queue
    entry = queue.get_by_id(entry_id)
    if entry is None or entry.status != "ready":
        return Response(status_code=200, headers={"HX-Redirect": "/queue"})
    form_values = {
        "date_kind": date_kind, "date_value": date_value, "sender": sender,
        "doctype": doctype, "description": description, "pattern": pattern,
        "targets": targets,
    }
    config, filename, target_paths, conflicts = _build_request_state(
        request, entry, date_kind, date_value, sender, doctype, description,
        pattern, targets,
    )
    need_summary = config.summary_mode == "always" or bool(conflicts)
    if need_summary:
        return _summary_response(
            request, entry, filename, target_paths, conflicts, config, form_values
        )
    return _execute_guarded(request, entry, filename, target_paths, conflicts,
                            config, form_values)


@router.post("/documents/{entry_id}/execute")
def execute(
    request: Request,
    entry_id: str,
    date_kind: str = Form("candidate"),
    date_value: str = Form(""),
    sender: str = Form(""),
    doctype: str = Form(""),
    description: str = Form(""),
    pattern: str = Form(""),
    targets: list[str] = Form(default=[]),
):
    queue: Queue = request.app.state.queue
    entry = queue.get_by_id(entry_id)
    if entry is None or entry.status != "ready":
        return Response(status_code=200, headers={"HX-Redirect": "/queue"})
    form_values = {
        "date_kind": date_kind, "date_value": date_value, "sender": sender,
        "doctype": doctype, "description": description, "pattern": pattern,
        "targets": targets,
    }
    config, filename, target_paths, conflicts = _build_request_state(
        request, entry, date_kind, date_value, sender, doctype, description,
        pattern, targets,
    )
    return _execute_guarded(request, entry, filename, target_paths, conflicts,
                            config, form_values)


def _config_context(request: Request, text: str, errors: list[str], saved: bool):
    context = _base_context(request, "config")
    context.update({"config_text": text, "errors": errors, "saved": saved})
    return context


@router.get("/config")
def config_page(request: Request):
    path = Path(request.app.state.config_path)
    text = path.read_text(encoding="utf-8")
    return templates.TemplateResponse(
        request, "config.html", _config_context(request, text, [], False)
    )


@router.post("/config")
def config_save(request: Request, text: str = Form(...)):
    path = Path(request.app.state.config_path)
    try:
        config = save_config(path, text)
    except ConfigError as exc:
        errors = str(exc).splitlines()
        return templates.TemplateResponse(
            request, "config.html", _config_context(request, text, errors, False)
        )
    request.app.state.config = config
    return templates.TemplateResponse(
        request, "config.html", _config_context(request, text, [], True)
    )


@router.post("/upload")
async def upload(request: Request, file: UploadFile = File(...)):
    config: Config = request.app.state.config
    lang = resolve_language(request)
    name = Path(file.filename or "").name  # strip any path components
    if not name.lower().endswith(".pdf"):
        return JSONResponse(
            {"error": translate("upload.err_not_pdf", lang)}, status_code=400
        )
    head = await file.read(len(PDF_MAGIC))
    if head != PDF_MAGIC:
        return JSONResponse(
            {"error": translate("upload.err_not_pdf", lang)}, status_code=400
        )
    folder = Path(config.paths.watchfolder)
    target = _unique_pdf_name(folder, name)
    fd, tmp = tempfile.mkstemp(dir=str(folder), prefix=".upload-", suffix=".part")
    try:
        with os.fdopen(fd, "wb") as out:
            out.write(head)
            while chunk := await file.read(_UPLOAD_CHUNK):
                out.write(chunk)
        os.replace(tmp, target)
    except OSError:
        Path(tmp).unlink(missing_ok=True)
        return JSONResponse(
            {"error": translate("upload.err_write", lang)}, status_code=500
        )
    return JSONResponse({"filename": target.name})
