# Aktionsmodell-Überarbeitung Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Trennt die Disposition des Inbox-Originals in zwei Settings (`originals.when_filed` / `when_removed`), macht „Überspringen" rein navigatorisch und führt eine bewusste „Entfernen"-Aktion mit htmx-Inline-Bestätigung (Ja/Nein, kein `hx-confirm`) ein.

**Architecture:** Config bekommt eine verschachtelte `originals`-Gruppe statt `original_handling`. Der Processor trennt Disposition (`process` → `when_filed`) von der neuen, fehlertoleranten `remove`-Operation (`when_removed`). Die Web-Schicht erhält drei klar getrennte Aktionen: Bestätigen (Review), Überspringen (nur Navigation), Entfernen (Queue · Übersicht · Review, Inline-Confirm-Toggle per htmx-Partial).

**Tech Stack:** Python 3 · FastAPI · Jinja2 · htmx · pydantic · pytest · uv

**Spec:** [docs/superpowers/specs/2026-06-17-1716-action-model-rework-design.md](../specs/2026-06-17-1716-action-model-rework-design.md)

## Global Constraints

- Python-Projektwurzel ist `backend/` (keine Root-`pyproject`). **Alle** Test-/Tool-Befehle aus `backend/`: `cd backend && uv run pytest …`.
- `uv run` schreibt gelegentlich `backend/uv.lock` ohne Dependency-Änderung neu — vor jedem Commit prüfen und ggf. zurücksetzen: `git checkout backend/uv.lock`.
- Commits: Conventional Commits, englischer Subject. `docs/backlog.md` ist deutsch.
- **Breaking Change ist erlaubt** (Projekt bleibt auf Major 1): bestehende `config.yaml` mit `original_handling` schlägt nach Task 1 bewusst fehl.
- Startwerte in den ausgelieferten Config-Dateien: `when_filed: delete`, `when_removed: trash`. Im Pydantic-Schema **keine** Defaults — beide Felder sind Pflicht.
- Werte beider Felder ausschließlich `delete | trash`.
- Lint muss grün bleiben: `cd backend && uv run ruff check .`.

---

### Task 1: Config — `originals`-Gruppe ersetzt `original_handling`

**Files:**
- Modify: `backend/src/zilpzalp/config.py` (neues `Originals`-Model, `Config.originals`, `original_handling` entfernen)
- Modify: `backend/config.default.yaml`
- Modify: `backend/config.example.yaml`
- Modify: `backend/tests/conftest.py:22-39` (`valid_config`-Fixture)
- Test: `backend/tests/test_config.py`
- Modify: `backend/tests/test_routes.py:193-221` (zwei config-bezogene Tests)
- Modify: `docs/backlog.md` (Idee in die Umsetzung-Tabelle holen, Status 🚧)

**Interfaces:**
- Produces: `Config.originals: Originals` mit `Originals.when_filed: Literal["delete","trash"]` und `Originals.when_removed: Literal["delete","trash"]`. `Config.original_handling` existiert nicht mehr.

- [ ] **Step 1: Backlog-Bookkeeping (Umsetzung-Tabelle)**

In [docs/backlog.md](../../backlog.md) die Idee „Aktionsmodell überarbeiten — Skip ≠ Löschen, eigener Entfernen-Button" aus „## Ideen / später" entfernen und als neue Zeile ans Ende der Tabelle „## Umsetzung" setzen:

```markdown
| 8 | Feature | **Aktionsmodell-Überarbeitung** — `originals.when_filed`/`when_removed` statt `original_handling`, Überspringen rein navigatorisch, eigener Entfernen-Button mit htmx-Inline-Bestätigung (Details: [superpowers/specs/2026-06-17-1716-action-model-rework-design.md](superpowers/specs/2026-06-17-1716-action-model-rework-design.md)) | 🚧 | — |
```

- [ ] **Step 2: Failing tests für das neue Schema schreiben**

In `backend/tests/test_config.py` die drei Tests, die `original_handling` referenzieren, ersetzen und einen Test für die verschachtelte Gruppe ergänzen. Ersetze `test_load_valid_config`, `test_invalid_enum_raises_config_error`, `test_missing_required_field_raises_config_error` durch:

```python
def test_load_valid_config(valid_config, write_config):
    path = write_config(valid_config)

    cfg = load_config(path)

    assert isinstance(cfg, Config)
    assert cfg.originals.when_filed == "delete"
    assert cfg.originals.when_removed == "trash"
    assert cfg.summary_mode == "on_conflict"
    assert cfg.date_format == "%Y-%m-%d"
    assert cfg.paths.watchfolder.name == "inbox"
    assert cfg.targets[0].name == "Finanzen"
    assert cfg.patterns["standard"].template == "{date}__{sender}_{doctype}_{description}"


def test_invalid_originals_enum_raises_config_error(valid_config, write_config):
    valid_config["originals"]["when_removed"] = "bogus"
    path = write_config(valid_config)

    with pytest.raises(ConfigError) as exc:
        load_config(path)
    assert "when_removed" in str(exc.value)


def test_missing_originals_raises_config_error(valid_config, write_config):
    del valid_config["originals"]
    path = write_config(valid_config)

    with pytest.raises(ConfigError) as exc:
        load_config(path)
    assert "originals" in str(exc.value)


def test_missing_one_originals_field_raises_config_error(valid_config, write_config):
    del valid_config["originals"]["when_filed"]
    path = write_config(valid_config)

    with pytest.raises(ConfigError) as exc:
        load_config(path)
    assert "when_filed" in str(exc.value)
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `cd backend && uv run pytest tests/test_config.py -q`
Expected: FAIL — die `valid_config`-Fixture liefert noch `original_handling`; `cfg.originals` existiert nicht.

- [ ] **Step 4: `valid_config`-Fixture umstellen**

In `backend/tests/conftest.py` in der `valid_config`-Fixture die Zeile `"original_handling": "delete",` ersetzen durch:

```python
        "originals": {"when_filed": "delete", "when_removed": "trash"},
```

- [ ] **Step 5: Config-Schema implementieren**

In `backend/src/zilpzalp/config.py` vor der `Config`-Klasse ein neues Model ergänzen:

```python
class Originals(BaseModel):
    when_filed: Literal["delete", "trash"]
    when_removed: Literal["delete", "trash"]
```

In `Config` die Zeile `original_handling: Literal["delete", "trash"]` ersetzen durch:

```python
    originals: Originals
```

- [ ] **Step 6: Ausgelieferte Config-Dateien umstellen**

In `backend/config.default.yaml` die Zeile `original_handling: delete` ersetzen durch:

```yaml
originals:
  when_filed: delete
  when_removed: trash
```

In `backend/config.example.yaml` die Zeile `original_handling: delete        # delete | trash` ersetzen durch:

```yaml
originals:
  when_filed: delete    # delete | trash — Original nach erfolgreichem Ablegen
  when_removed: trash   # delete | trash — Original beim bewussten Entfernen
```

- [ ] **Step 7: Config-bezogene Route-Tests anpassen**

In `backend/tests/test_routes.py`:

`test_config_page_shows_current_yaml` — letzte Assertion ändern:

```python
    assert "originals" in response.text    # current file content shown
```

`test_config_save_invalid_shows_errors_and_keeps_config` — den ungültigen Text ändern:

```python
    response = client.post("/config", data={"text": "originals:\n  when_filed: bogus\n  when_removed: trash"})
```

- [ ] **Step 8: Tests grün**

Run: `cd backend && uv run pytest tests/test_config.py -q`
Expected: PASS

> Hinweis: `tests/test_processor.py` und `tests/test_routes.py` sind nach diesem Task vorübergehend rot (sie referenzieren noch `original_handling`) — Tasks 2 und 3 reparieren sie. `app` importiert weiterhin fehlerfrei.

- [ ] **Step 9: Lint + uv.lock prüfen**

Run: `cd backend && uv run ruff check . && git checkout uv.lock 2>/dev/null; true`

- [ ] **Step 10: Commit**

```bash
git add backend/src/zilpzalp/config.py backend/config.default.yaml backend/config.example.yaml backend/tests/conftest.py backend/tests/test_config.py backend/tests/test_routes.py docs/backlog.md
git commit -m "feat(config): replace original_handling with nested originals group

BREAKING CHANGE: original_handling is removed; config.yaml must now provide
originals.when_filed and originals.when_removed (delete|trash)."
```

---

### Task 2: Processor — Disposition trennen, `remove` statt `skip`

**Files:**
- Modify: `backend/src/zilpzalp/processor.py` (`_dispose`-Signatur, `process` → `when_filed`, `skip` → `remove`)
- Modify: `backend/src/zilpzalp/web/routes.py:15` (Import) und `:391` (Aufrufstelle) — mechanische Anpassung, damit `app` importierbar bleibt
- Test: `backend/tests/test_processor.py`

**Interfaces:**
- Consumes: `Config.originals.when_filed` / `when_removed` (Task 1).
- Produces: `processor.process(source, filename, targets, config)` disponiert per `when_filed`; `processor.remove(source, config) -> ProcessResult` disponiert per `when_removed`, tolerant gegenüber fehlendem `source`. `processor.skip` existiert nicht mehr. `_dispose(source: Path, trash: Path, mode: str) -> tuple[str, Path | None]`.

- [ ] **Step 1: Processor-Tests umschreiben**

In `backend/tests/test_processor.py` den Import-Zeile und die `_config`-Helper anpassen und die `skip`-Tests durch `remove`-Tests ersetzen.

Import (Zeile 6):

```python
from zilpzalp.processor import FileConflictError, ProcessorError, process, remove
```

`_config`-Helper (Zeilen 9-25) ersetzen durch:

```python
def _config(tmp_path: Path, when_filed: str = "delete", when_removed: str = "trash", extra: str = ""):
    """Build a validated Config; paths come from env (env_paths fixture)."""
    cfg = tmp_path / "config.yaml"
    cfg.write_text(
        f"""
originals:
  when_filed: {when_filed}
  when_removed: {when_removed}
summary_mode: never
default_pattern: standard
date_format: "%Y-%m-%d"
patterns:
  standard:
    template: "{{date}}__{{sender}}_{{doctype}}_{{description}}"
{extra}
""",
        encoding="utf-8",
    )
    return load_config(cfg)
```

In allen `process`-Tests die Aufrufe `_config(tmp_path, "delete")` → `_config(tmp_path, when_filed="delete")` und `_config(tmp_path, "trash")` → `_config(tmp_path, when_filed="trash")` umstellen (Zeilen 41, 54, 69, 105, 117, 131, 145, 155).

Die beiden `skip`-Tests (Zeilen 81-100) ersetzen durch:

```python
def test_remove_deletes_without_copy(tmp_path):
    config = _config(tmp_path, when_removed="delete")
    source = _source(tmp_path)

    result = remove(source, config)

    assert not source.exists()
    assert result.copied == []
    assert result.original_action == "deleted"


def test_remove_trashes_without_copy(tmp_path):
    config = _config(tmp_path, when_removed="trash")
    source = _source(tmp_path, "orig.pdf")

    result = remove(source, config)

    assert not source.exists()
    assert (Path(config.paths.trash) / "orig.pdf").exists()
    assert result.original_action == "trashed"


def test_remove_uses_when_removed_not_when_filed(tmp_path):
    # when_filed=delete must NOT affect removal; when_removed=trash wins.
    config = _config(tmp_path, when_filed="delete", when_removed="trash")
    source = _source(tmp_path, "orig.pdf")

    remove(source, config)

    assert (Path(config.paths.trash) / "orig.pdf").exists()


def test_remove_tolerates_missing_original(tmp_path):
    # e.g. an error entry whose file was already moved to error/.
    config = _config(tmp_path, when_removed="trash")
    missing = tmp_path / "inbox" / "gone.pdf"

    result = remove(missing, config)  # must not raise

    assert result.copied == []
    assert result.original_action == "deleted"
    assert result.original_destination is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && uv run pytest tests/test_processor.py -q`
Expected: FAIL — `remove` ist noch nicht importierbar.

- [ ] **Step 3: Processor implementieren**

In `backend/src/zilpzalp/processor.py` `_dispose` (Zeilen 42-50) ersetzen durch:

```python
def _dispose(source: Path, trash: Path, mode: str) -> tuple[str, Path | None]:
    """Remove the inbox original. *mode* is "delete" or "trash"; the caller
    chooses it per situation (when_filed for filing, when_removed for removal)."""
    if mode == "trash":
        dest = _unique_name(trash, source.name)
        shutil.move(str(source), str(dest))
        return "trashed", dest
    source.unlink(missing_ok=True)
    return "deleted", None
```

In `process` die Dispositions-Zeile (Zeile 80) ersetzen durch:

```python
    action, dest = _dispose(source, config.paths.trash, config.originals.when_filed)
```

Die Funktion `skip` (Zeilen 84-87) ersetzen durch:

```python
def remove(source: Path, config: Config) -> ProcessResult:
    """Discard an inbox original on explicit removal, per
    config.originals.when_removed. Tolerant of an already-missing original
    (e.g. an error entry whose file was moved to error/): no disposition, no
    error — the caller still drops the queue entry."""
    if not source.exists():
        return ProcessResult(copied=[], original_action="deleted", original_destination=None)
    action, dest = _dispose(source, config.paths.trash, config.originals.when_removed)
    return ProcessResult(copied=[], original_action=action, original_destination=dest)
```

- [ ] **Step 4: Routes importierbar halten (mechanische Anpassung)**

In `backend/src/zilpzalp/web/routes.py` den Import (Zeile 15) ändern:

```python
from zilpzalp.processor import FileConflictError, ProcessorError, process, remove
```

In `skip_document` (Zeile ~391) den Aufruf `skip(entry.path, config)` ersetzen durch `remove(entry.path, config)`. (Die vollständige Umschreibung der Route folgt in Task 3; hier nur, damit `app` importiert.)

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd backend && uv run pytest tests/test_processor.py -q`
Expected: PASS

- [ ] **Step 6: Lint + uv.lock prüfen**

Run: `cd backend && uv run ruff check . && git checkout uv.lock 2>/dev/null; true`

- [ ] **Step 7: Commit**

```bash
git add backend/src/zilpzalp/processor.py backend/src/zilpzalp/web/routes.py backend/tests/test_processor.py
git commit -m "feat(processor): split disposition into when_filed/when_removed, add remove()"
```

---

### Task 3: Routes — Überspringen navigatorisch, Entfernen + Inline-Confirm

**Files:**
- Modify: `backend/src/zilpzalp/web/routes.py` (Import `Query`; `_base_context` um `when_removed`; Helper `_next_ready_after`; `skip_document` neu; `remove_document` + `remove_control` neu; `original_label` aus `when_filed`; `_execute` no-next → `/`)
- Create: `backend/src/zilpzalp/web/templates/_remove_control.html`
- Modify: `backend/src/zilpzalp/web/locales/de.json` (neue Keys)
- Modify: `backend/src/zilpzalp/web/locales/en.json` (neue Keys)
- Test: `backend/tests/test_routes.py`

**Interfaces:**
- Consumes: `processor.remove` (Task 2), `Config.originals.*` (Task 1).
- Produces: Routen `POST /documents/{id}/skip` (nur Navigation), `POST /documents/{id}/remove?from=review|queue|overview`, `GET /documents/{id}/remove-control?from=…&confirm=0|1` (rendert `_remove_control.html`). Partial-Kontext: `entry`, `from_view` (str), `confirm` (bool), `when_removed` (str), `t`. Base-Context-Global `when_removed`.

- [ ] **Step 1: Neue i18n-Keys ergänzen**

In `backend/src/zilpzalp/web/locales/de.json` ergänzen (z. B. direkt nach `"action.skip"` bzw. bei den toasts/overview-Keys):

```json
  "action.remove": "Entfernen",
  "action.yes": "Ja",
  "action.no": "Nein",
  "confirm.remove": "Entfernen? Original → {target}",
  "toast.removed": "„{filename}“ wurde entfernt.",
  "overview.original_when_filed": "Original beim Ablegen",
  "overview.original_when_removed": "Original beim Entfernen",
```

In `backend/src/zilpzalp/web/locales/en.json` ergänzen:

```json
  "action.remove": "Remove",
  "action.yes": "Yes",
  "action.no": "No",
  "confirm.remove": "Remove? Original → {target}",
  "toast.removed": "“{filename}” was removed.",
  "overview.original_when_filed": "Original when filed",
  "overview.original_when_removed": "Original when removed",
```

(JSON-Syntax beachten: trailing-Komma vermeiden — jeweils in die bestehende Objektliste einreihen.)

- [ ] **Step 2: Failing tests für die Routen schreiben**

In `backend/tests/test_routes.py` die bestehenden Skip-Tests ersetzen/ergänzen. Ersetze `test_skip_deletes_file_and_removes_entry_and_cache` (Zeilen 429-440) und `test_queue_list_shows_skip_button` (Zeilen 449-453) durch die folgenden Tests, und füge die Remove-Tests hinzu:

```python
def test_skip_is_navigation_only_and_keeps_document(client):
    cfg = app.state.config
    entry = _add_ready(client, "keepme.pdf")
    Path(cfg.paths.cache).joinpath("keepme.json").write_text("{}", encoding="utf-8")

    response = client.post(f"/documents/{entry.id}/skip", follow_redirects=False)

    assert response.status_code == 200
    # nothing disposed, nothing dropped — skip is pure navigation
    assert app.state.queue.get_by_id(entry.id) is not None
    assert (Path(cfg.paths.watchfolder) / "keepme.pdf").exists()
    assert Path(cfg.paths.cache).joinpath("keepme.json").exists()


def test_skip_last_ready_goes_to_start_page(client):
    only = _add_ready(client, "only.pdf")

    response = client.post(f"/documents/{only.id}/skip", follow_redirects=False)

    assert response.headers.get("HX-Redirect") == "/"


def test_remove_from_queue_disposes_and_redirects_to_queue(client):
    cfg = app.state.config
    cfg.__dict__["originals"].__dict__["when_removed"] = "delete"
    entry = _add_ready(client, "drop.pdf")
    Path(cfg.paths.cache).joinpath("drop.json").write_text("{}", encoding="utf-8")

    response = client.post(
        f"/documents/{entry.id}/remove?from=queue", follow_redirects=False
    )

    assert response.status_code == 200
    redirect = response.headers.get("HX-Redirect", "")
    assert redirect.startswith("/queue")
    assert "flash=" in redirect
    assert app.state.queue.get_by_id(entry.id) is None
    assert not (Path(cfg.paths.watchfolder) / "drop.pdf").exists()
    assert not Path(cfg.paths.cache).joinpath("drop.json").exists()


def test_remove_from_overview_redirects_to_start(client):
    entry = _add_ready(client, "drop.pdf")
    response = client.post(
        f"/documents/{entry.id}/remove?from=overview", follow_redirects=False
    )
    assert response.headers.get("HX-Redirect", "").startswith("/")
    assert app.state.queue.get_by_id(entry.id) is None


def test_remove_from_review_advances_to_next_ready(client):
    first = _add_ready(client, "first.pdf")
    second = _add_ready(client, "second.pdf")

    response = client.post(
        f"/documents/{first.id}/remove?from=review", follow_redirects=False
    )

    redirect = response.headers.get("HX-Redirect", "")
    assert redirect.startswith(f"/review/{second.id}")


def test_remove_trashes_when_configured(client):
    cfg = app.state.config
    cfg.__dict__["originals"].__dict__["when_removed"] = "trash"
    entry = _add_ready(client, "trashme.pdf")

    client.post(f"/documents/{entry.id}/remove?from=queue", follow_redirects=False)

    assert (Path(cfg.paths.trash) / "trashme.pdf").exists()


def test_remove_tolerates_missing_original(client):
    # error-style entry: queue knows it, file already gone from the watchfolder
    cfg = app.state.config
    entry = _add_ready(client, "ghost.pdf")
    (Path(cfg.paths.watchfolder) / "ghost.pdf").unlink()

    response = client.post(
        f"/documents/{entry.id}/remove?from=queue", follow_redirects=False
    )

    assert response.status_code == 200
    assert app.state.queue.get_by_id(entry.id) is None


def test_remove_unknown_entry_redirects(client):
    response = client.post("/documents/deadbeef/remove?from=queue", follow_redirects=False)
    assert response.status_code == 200
    assert response.headers.get("HX-Redirect") == "/queue"


def test_remove_control_renders_idle_then_confirm(client):
    entry = _add_ready(client, "rechnung.pdf")

    idle = client.get(f"/documents/{entry.id}/remove-control?from=queue&confirm=0").text
    assert "Entfernen" in idle
    assert "confirm=1" in idle
    assert f"rm-{entry.id}" in idle

    confirm = client.get(f"/documents/{entry.id}/remove-control?from=queue&confirm=1").text
    assert "Ja" in confirm
    assert "Nein" in confirm
    assert f"/documents/{entry.id}/remove?from=queue" in confirm
    assert "Original" in confirm  # the hint
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `cd backend && uv run pytest tests/test_routes.py -q -k "skip or remove"`
Expected: FAIL — `remove`/`remove-control`-Routen fehlen, skip ist noch destruktiv.

- [ ] **Step 4: Imports + Base-Context erweitern**

In `backend/src/zilpzalp/web/routes.py` die FastAPI-Import-Zeile (Zeile 10) erweitern um `Query`:

```python
from fastapi import APIRouter, File, Form, Query, Request, UploadFile
```

In `_base_context` (Zeilen 91-103) am Anfang die Config holen und `when_removed` ins Dict aufnehmen:

```python
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
        "when_removed": request.app.state.config.originals.when_removed,
        "t": lambda key, **kw: translate(key, lang, **kw),
    }
```

- [ ] **Step 5: Helper `_next_ready_after` ergänzen**

In `backend/src/zilpzalp/web/routes.py` direkt nach `_next_ready` (nach Zeile 88) einfügen:

```python
def _next_ready_after(queue: Queue, current_id: str):
    """First ready, reviewable entry AFTER *current_id* in newest-first order,
    or None. Drives the forward sweep of 'skip' so it never bounces back."""
    ready = [
        e for e in _by_mtime_desc(queue.list())
        if e.status == "ready" and e.suggestion is not None
    ]
    seen = False
    for entry in ready:
        if seen:
            return entry
        if entry.id == current_id:
            seen = True
    return None
```

- [ ] **Step 6: `original_label` auf `when_filed` umstellen**

In `review_page` (Zeile 183) und `_summary_response` (Zeile 272) jeweils:

```python
            "original_label": translate("original." + config.originals.when_filed, lang),
```

- [ ] **Step 7: `_execute` no-next → `/`**

In `_execute` (Zeile 288) die Zielzeile ändern:

```python
    target = f"/review/{nxt.id}" if nxt else "/"
```

- [ ] **Step 8: `skip_document` zu reiner Navigation umschreiben**

In `backend/src/zilpzalp/web/routes.py` die gesamte `skip_document`-Funktion (Zeilen 382-404) ersetzen durch:

```python
@router.post("/documents/{entry_id}/skip")
def skip_document(request: Request, entry_id: str):
    """Navigation only: jump to the next ready document after this one; leave
    the document untouched in the queue. No file operation, no flash."""
    queue: Queue = request.app.state.queue
    nxt = _next_ready_after(queue, entry_id)
    target = f"/review/{nxt.id}" if nxt else "/"
    return Response(status_code=200, headers={"HX-Redirect": target})
```

- [ ] **Step 9: `remove_document` + `remove_control` ergänzen**

Direkt nach `skip_document` einfügen:

```python
_REMOVE_FROM = {"review", "queue", "overview"}


@router.post("/documents/{entry_id}/remove")
def remove_document(
    request: Request,
    entry_id: str,
    origin: str = Query("queue", alias="from"),
):
    queue: Queue = request.app.state.queue
    lang = resolve_language(request)
    if origin not in _REMOVE_FROM:
        origin = "queue"
    entry = queue.get_by_id(entry_id)
    if entry is None:
        target = "/" if origin in ("review", "overview") else "/queue"
        return Response(status_code=200, headers={"HX-Redirect": target})
    config: Config = request.app.state.config
    try:
        remove(entry.path, config)
    except ProcessorError as exc:
        message = translate("toast.file_error", lang, error=str(exc))
        return Response(status_code=200, headers={
            "HX-Redirect": "/queue?flash=" + quote(message) + "&kind=err"
        })
    queue.remove(entry.path)
    request.app.state.cache.remove(entry.path)
    message = translate("toast.removed", lang, filename=entry.path.name)
    if origin == "review":
        nxt = _next_ready(queue)
        target = f"/review/{nxt.id}" if nxt else "/"
    elif origin == "overview":
        target = "/"
    else:
        target = "/queue"
    return Response(status_code=200, headers={
        "HX-Redirect": target + "?flash=" + quote(message) + "&kind=ok"
    })


@router.get("/documents/{entry_id}/remove-control")
def remove_control(
    request: Request,
    entry_id: str,
    origin: str = Query("queue", alias="from"),
    confirm: int = 0,
):
    queue: Queue = request.app.state.queue
    entry = queue.get_by_id(entry_id)
    if entry is None:
        return Response(status_code=200)  # gone; nothing to render
    if origin not in _REMOVE_FROM:
        origin = "queue"
    config: Config = request.app.state.config
    lang = resolve_language(request)
    context = {
        "entry": entry,
        "from_view": origin,
        "confirm": bool(confirm),
        "when_removed": config.originals.when_removed,
        "lang": lang,
        "t": lambda key, **kw: translate(key, lang, **kw),
    }
    return templates.TemplateResponse(request, "_remove_control.html", context)
```

- [ ] **Step 10: Partial `_remove_control.html` anlegen**

Create `backend/src/zilpzalp/web/templates/_remove_control.html`:

```html
<span id="rm-{{ entry.id }}" class="rm-control">
  {% if confirm %}
    <span class="rm-hint">{{ t('confirm.remove', target=t('original.' ~ when_removed)) }}</span>
    <button type="button" class="btn sm danger"
            hx-post="/documents/{{ entry.id }}/remove?from={{ from_view }}">{{ t('action.yes') }}</button>
    <button type="button" class="btn sm ghost"
            hx-get="/documents/{{ entry.id }}/remove-control?from={{ from_view }}&confirm=0"
            hx-target="#rm-{{ entry.id }}" hx-swap="outerHTML">{{ t('action.no') }}</button>
  {% else %}
    <button type="button" class="btn sm ghost"
            hx-get="/documents/{{ entry.id }}/remove-control?from={{ from_view }}&confirm=1"
            hx-target="#rm-{{ entry.id }}" hx-swap="outerHTML">{{ t('action.remove') }}</button>
  {% endif %}
</span>
```

- [ ] **Step 11: Run tests to verify they pass**

Run: `cd backend && uv run pytest tests/test_routes.py -q -k "skip or remove"`
Expected: PASS

- [ ] **Step 12: Lint + uv.lock prüfen**

Run: `cd backend && uv run ruff check . && git checkout uv.lock 2>/dev/null; true`

- [ ] **Step 13: Commit**

```bash
git add backend/src/zilpzalp/web/routes.py backend/src/zilpzalp/web/templates/_remove_control.html backend/src/zilpzalp/web/locales/de.json backend/src/zilpzalp/web/locales/en.json backend/tests/test_routes.py
git commit -m "feat(web): skip becomes navigation-only, add remove action with inline confirm"
```

---

### Task 4: Templates — Buttons verdrahten, Info-Panel, CSS, alte Keys entfernen

**Files:**
- Modify: `backend/src/zilpzalp/web/templates/_queue_list.html:24-34`
- Modify: `backend/src/zilpzalp/web/templates/_overview.html:39-44`
- Modify: `backend/src/zilpzalp/web/templates/review.html:123-128`
- Modify: `backend/src/zilpzalp/web/templates/overview.html:33`
- Modify: `backend/src/zilpzalp/web/static/styles.css` (Layout-Regel `.rm-control` / `.rm-hint`)
- Modify: `backend/src/zilpzalp/web/locales/de.json` (obsolet entfernen)
- Modify: `backend/src/zilpzalp/web/locales/en.json` (obsolet entfernen)
- Test: `backend/tests/test_routes.py` (Template-Inhalts-Assertions)

**Interfaces:**
- Consumes: `_remove_control.html`, Base-Context-Global `when_removed`, `config.originals.*` (Tasks 1, 3).

- [ ] **Step 1: Failing tests für die Template-Verdrahtung schreiben**

In `backend/tests/test_routes.py` ergänzen:

```python
def test_queue_list_shows_remove_control_not_skip(client):
    _add_ready(client, "rechnung.pdf")
    body = client.get("/partials/queue").text
    assert "Entfernen" in body
    assert "remove-control?from=queue" in body
    assert "/skip" not in body          # skip button gone from the queue list
    assert "Überspringen" not in body


def test_overview_recent_shows_remove_control(client):
    _add_ready(client, "rechnung.pdf")
    body = client.get("/partials/overview").text
    assert "remove-control?from=overview" in body


def test_review_has_skip_and_remove_controls(client):
    entry = _add_ready(client, "rechnung.pdf")
    body = client.get(f"/review/{entry.id}").text
    assert f"/documents/{entry.id}/skip" in body          # navigation skip
    assert "remove-control?from=review" in body           # inline remove
    assert "hx-confirm" not in body                        # no browser confirm dialog


def test_overview_info_panel_shows_both_original_settings(client):
    body = client.get("/").text
    assert "Original beim Ablegen" in body
    assert "Original beim Entfernen" in body
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && uv run pytest tests/test_routes.py -q -k "remove_control or info_panel or skip_and_remove"`
Expected: FAIL — Templates noch nicht verdrahtet.

- [ ] **Step 3: Queue-Liste verdrahten**

In `backend/src/zilpzalp/web/templates/_queue_list.html` den Aktionsblock (Zeilen 24-34) ersetzen durch:

```html
      <div style="display:flex;gap:8px;justify-content:flex-end;align-items:center">
        {% if entry.status == 'ready' %}
          <a class="btn sm primary" href="/review/{{ entry.id }}">{{ t('action.review') }}
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="width:14px;height:14px"><path d="M5 12h14M13 6l6 6-6 6"/></svg>
          </a>
        {% endif %}
        {% with from_view='queue', confirm=False %}{% include "_remove_control.html" %}{% endwith %}
      </div>
```

- [ ] **Step 4: Übersicht (recent list) verdrahten**

In `backend/src/zilpzalp/web/templates/_overview.html` den Aktionsblock (Zeilen 39-44) ersetzen durch:

```html
          <div style="display:flex;gap:8px;align-items:center">
            <span class="badge {{ STATUS_BADGE[entry.status] }}"><span class="dot"></span>{{ t('status.' ~ entry.status) }}</span>
            {% if entry.status == 'ready' %}
            <a class="btn sm primary" href="/review/{{ entry.id }}">{{ t('action.review') }}</a>
            {% endif %}
            {% with from_view='overview', confirm=False %}{% include "_remove_control.html" %}{% endwith %}
          </div>
```

- [ ] **Step 5: Review-Aktionen verdrahten**

In `backend/src/zilpzalp/web/templates/review.html` den Skip-Button (Zeilen 125-128) ersetzen durch (Skip ohne `hx-confirm`, Remove-Control daneben):

```html
            <button type="button" class="btn ghost" hx-post="/documents/{{ entry.id }}/skip">
              {{ t('action.skip') }}
            </button>
            {% with from_view='review', confirm=False %}{% include "_remove_control.html" %}{% endwith %}
```

- [ ] **Step 6: Info-Panel zweizeilig**

In `backend/src/zilpzalp/web/templates/overview.html` die Zeile 33 (`info-cell` „Umgang mit Original") ersetzen durch:

```html
          <div class="info-cell"><div class="info-k">{{ t('overview.original_when_filed') }}</div><div class="info-v">{{ t('original.' ~ config.originals.when_filed) }}</div></div>
          <div class="info-cell"><div class="info-k">{{ t('overview.original_when_removed') }}</div><div class="info-v">{{ t('original.' ~ config.originals.when_removed) }}</div></div>
```

- [ ] **Step 7: Layout-Regel für die Inline-Bestätigung**

In `backend/src/zilpzalp/web/static/styles.css` nach der `.btn`-Gruppe (nach Zeile 283) ergänzen:

```css
.rm-control { display: inline-flex; align-items: center; gap: 8px; }
.rm-hint { font-size: 12.5px; color: var(--text-3); }
```

- [ ] **Step 8: Obsolete i18n-Keys entfernen**

In `backend/src/zilpzalp/web/locales/de.json` und `backend/src/zilpzalp/web/locales/en.json` jeweils die Keys `"confirm.skip"`, `"toast.skipped"` und `"overview.original_handling"` entfernen (auf gültige JSON-Syntax achten — kein hängendes Komma).

- [ ] **Step 9: Run tests to verify they pass**

Run: `cd backend && uv run pytest tests/test_routes.py -q`
Expected: PASS

- [ ] **Step 10: Volle Suite + Lint + uv.lock**

Run: `cd backend && uv run pytest -q && uv run ruff check . && git checkout uv.lock 2>/dev/null; true`
Expected: gesamte Suite PASS, ruff grün.

- [ ] **Step 11: Commit**

```bash
git add backend/src/zilpzalp/web/templates/_queue_list.html backend/src/zilpzalp/web/templates/_overview.html backend/src/zilpzalp/web/templates/review.html backend/src/zilpzalp/web/templates/overview.html backend/src/zilpzalp/web/static/styles.css backend/src/zilpzalp/web/locales/de.json backend/src/zilpzalp/web/locales/en.json backend/tests/test_routes.py
git commit -m "feat(web): wire remove control into queue, overview and review; drop skip-as-delete"
```

---

### Task 5: Dokumentation + CHANGELOG

**Files:**
- Modify: `backend/CHANGELOG.md` (Migrationshinweis)
- Modify: `mkdocs/docs/configuration.md`
- Modify: `mkdocs/docs/usage.md`
- Modify: `mkdocs/docs/installation.md`

**Interfaces:** keine (reine Doku).

- [ ] **Step 1: Bestehende Doku-Stellen sichten**

Run: `cd /workspace/github.com/elnebuloso/zilpzalp && grep -rn "original_handling\|Überspringen\|skip\|Umgang mit Original" mkdocs/docs backend/CHANGELOG.md`
Zweck: alle Fundstellen kennen, die auf das alte Modell verweisen.

- [ ] **Step 2: CHANGELOG-Migrationshinweis ergänzen**

In `backend/CHANGELOG.md` unter dem obersten „Unreleased"- bzw. neuen Eintrag (dem dort etablierten Format folgend) einen Hinweis aufnehmen, sinngemäß:

```markdown
### Breaking
- `config.yaml`: `original_handling` entfällt. Stattdessen:
  ```yaml
  originals:
    when_filed: delete    # Original nach erfolgreichem Ablegen
    when_removed: trash   # Original beim bewussten Entfernen
  ```
  Bestehende Configs müssen migriert werden.

### Changed
- „Überspringen" in der Review springt nur noch zum nächsten Dokument und löscht
  nichts mehr. Zum Verwerfen gibt es eine eigene „Entfernen"-Aktion (Warteschlange,
  Übersicht, Review) mit Inline-Bestätigung.
```

(Exaktes Format/Position an die bestehende Struktur in `backend/CHANGELOG.md` anpassen.)

- [ ] **Step 3: mkdocs configuration.md aktualisieren**

In `mkdocs/docs/configuration.md` die `original_handling`-Beschreibung durch die `originals`-Gruppe ersetzen: zwei Felder `when_filed` / `when_removed` (jeweils `delete | trash`), mit der Erklärung der Asymmetrie (nach Ablegen existiert eine Kopie → `delete` verlustfrei; beim Entfernen keine Kopie → `trash` sicher). YAML-Beispiel auf die verschachtelte Form bringen.

- [ ] **Step 4: mkdocs usage.md aktualisieren**

In `mkdocs/docs/usage.md` die Beschreibung der Aktionen angleichen: Bestätigen (legt ab, disponiert per `when_filed`), Überspringen (nur Navigation, lässt das Dokument in der Warteschlange), Entfernen (verwirft bewusst, disponiert per `when_removed`, Inline-Bestätigung Ja/Nein). Falls Fundstellen aus Step 1 das alte Skip-löscht-Verhalten beschreiben, korrigieren.

- [ ] **Step 5: mkdocs installation.md prüfen/anpassen**

In `mkdocs/docs/installation.md` das gezeigte Config-Beispiel (falls es `original_handling` enthält) auf die `originals`-Gruppe umstellen.

- [ ] **Step 6: Doku-Konsistenz prüfen**

Run: `cd /workspace/github.com/elnebuloso/zilpzalp && grep -rn "original_handling" mkdocs/docs backend/CHANGELOG.md`
Expected: keine Treffer mehr (außer bewusst als „entfällt/migriert" markierter Migrationshinweis).

- [ ] **Step 7: Commit**

```bash
git add backend/CHANGELOG.md mkdocs/docs/configuration.md mkdocs/docs/usage.md mkdocs/docs/installation.md
git commit -m "docs: document originals.when_filed/when_removed and the new action model"
```

> Hinweis: Backlog-Status (Zeile #8) bleibt auf 🚧; der finale Merge-Commit-SHA wird beim Abschluss/Merge der Arbeit in der `Commit`-Spalte eingetragen (Backlog-Pflegeregel, Punkt 4).

---

## Self-Review

**Spec-Coverage:**
- Spec §1 (Config `originals`) → Task 1. ✓
- Spec §2 (Processor: `_dispose`-Modus, `process`→`when_filed`, `skip` raus, `remove` tolerant) → Task 2. ✓
- Spec §3 (Routes: `_next_ready_after`, skip-Navigation, remove + `from`, remove-control, `original_label` aus `when_filed`, `_execute` no-next → `/`) → Task 3. ✓
- Spec §4 (Inline-Confirm-Partial, htmx-Toggle) → Task 3 (Route + Partial) + Task 4 (Einbindung). ✓
- Spec §5 (Templates: queue/overview/review/info-panel, danger-Button) → Task 4. `.btn.danger` existiert bereits; nur Layout-Regel ergänzt. ✓
- Spec §6 (i18n: neue Keys, entfallene Keys) → Task 3 (neu) + Task 4 (entfallen). ✓
- Spec §7 (Tests) → in jedem Task TDD-first; volle Suite grün in Task 4 Step 10. ✓
- Spec „Gelöste Backlog-Offene-Frage" (skip re-enqueued nichts) → durch navigatorisches skip in Task 3 strukturell erfüllt; `test_skip_is_navigation_only_and_keeps_document` belegt, dass der Eintrag bleibt. ✓

**Placeholder-Scan:** keine TBD/TODO; jeder Code-Step enthält vollständigen Code, jeder Test-Step vollständige Tests. ✓

**Typ-Konsistenz:** `remove(source, config)`, `_dispose(source, trash, mode)`, `_next_ready_after(queue, current_id)`, Partial-Vars `from_view`/`confirm`/`when_removed`, Query-Alias `from`→`origin` durchgängig identisch über Tasks 2-4 verwendet. `Originals.when_filed`/`when_removed` einheitlich. ✓

**Hinweis zu Test-Overrides:** In-Memory-Override des verschachtelten Settings via `cfg.__dict__["originals"].__dict__["when_removed"] = …` (analog zum bestehenden Muster `cfg.__dict__["summary_mode"] = …`), da pydantic-Modelle hier ohne Validierungs-Roundtrip gepatcht werden.
