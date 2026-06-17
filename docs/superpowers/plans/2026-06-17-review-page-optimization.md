# Review Page Optimization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Optimize the review page — chain straight to the next ready document, force an explicit date choice, highlight + open the original PDF, and expose the cached extraction (Markdown / HTML / JSON) in a side drawer.

**Architecture:** Server-rendered Jinja + HTMX. Backend changes live in `extractor.py`, `cache.py`, and `web/routes.py`; the UI changes live in `web/templates/review.html`, a new partial, `web/static/styles.css`, and `web/static/app.js`. The extraction drawer lazy-loads each tab via HTMX from a new `/extract/{kind}` route; the HTML tab is isolated in a sandboxed `<iframe srcdoc>`.

**Tech Stack:** Python 3.12, FastAPI, Jinja2, HTMX, pytest, `opendataloader-pdf` v2.

## Global Constraints

- Documentation/UI copy in `README.md` and `mkdocs/` is English; UI strings live in `web/locales/{de,en}.json` and must be added to **both** catalogs.
- Conventional Commits, English commit messages.
- Tests use `pytest`; run from the repo root with `uv run pytest`.
- `uv run` may rewrite `backend/uv.lock` without dependency changes — if it does and you added no dependency, restore it before committing (`git checkout backend/uv.lock`).
- No new Python dependency is introduced by this plan. `opendataloader-pdf` HTML output is **assumed supported**; tests mock `convert`, so they do not prove it. Verify against a real PDF during manual review (Task 2, Step 6).
- The `cache` instance is `request.app.state.cache` (a `DocumentCache`); the queue is `request.app.state.queue`.

---

### Task 1: Cache — HTML artifact + raw-text read helpers

**Files:**
- Modify: `backend/src/zilpzalp/cache.py`
- Test: `backend/tests/test_cache.py`

**Interfaces:**
- Produces:
  - `DocumentCache.read_markdown(path: Path | str) -> str | None`
  - `DocumentCache.read_html(path: Path | str) -> str | None`
  - `DocumentCache.read_json_text(path: Path | str) -> str | None`
  - `DocumentCache._html(name: str) -> Path` (internal)
  - `remove()` and `prune()` now also delete `<stem>.html`

- [ ] **Step 1: Write the failing tests**

Add to `backend/tests/test_cache.py`:

```python
def test_read_helpers_return_text_or_none(tmp_path):
    (tmp_path / "doc.md").write_text("# Title", encoding="utf-8")
    (tmp_path / "doc.html").write_text("<h1>Title</h1>", encoding="utf-8")
    (tmp_path / "doc.json").write_text('{"a": 1}', encoding="utf-8")
    cache = DocumentCache(tmp_path)

    assert cache.read_markdown(Path("/inbox/doc.pdf")) == "# Title"
    assert cache.read_html(Path("/inbox/doc.pdf")) == "<h1>Title</h1>"
    assert cache.read_json_text(Path("/inbox/doc.pdf")) == '{"a": 1}'
    assert cache.read_markdown(Path("/inbox/missing.pdf")) is None
    assert cache.read_html(Path("/inbox/missing.pdf")) is None
    assert cache.read_json_text(Path("/inbox/missing.pdf")) is None


def test_remove_deletes_html_too(tmp_path):
    (tmp_path / "doc.json").write_text("{}", encoding="utf-8")
    (tmp_path / "doc.md").write_text("x", encoding="utf-8")
    (tmp_path / "doc.html").write_text("<i>x</i>", encoding="utf-8")
    cache = DocumentCache(tmp_path)

    cache.remove(Path("/inbox/doc.pdf"))

    assert not (tmp_path / "doc.html").exists()


def test_prune_removes_html_orphans(tmp_path):
    for stem in ("keep", "orphan"):
        (tmp_path / f"{stem}.html").write_text("<i>x</i>", encoding="utf-8")
    DocumentCache(tmp_path).prune(["keep.pdf"])

    assert (tmp_path / "keep.html").exists()
    assert not (tmp_path / "orphan.html").exists()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest backend/tests/test_cache.py -k "read_helpers or html" -v`
Expected: FAIL (`AttributeError: ... read_markdown` and missing `.html` handling).

- [ ] **Step 3: Implement in `cache.py`**

Add the `_html` path helper next to `_md`:

```python
    def _html(self, name: str) -> Path:
        return self._base / (Path(name).stem + ".html")
```

Add read helpers (place after `load_document`):

```python
    def _read(self, target: Path) -> str | None:
        if not target.exists():
            return None
        return target.read_text(encoding="utf-8")

    def read_markdown(self, path: Path | str) -> str | None:
        return self._read(self._md(Path(path).name))

    def read_html(self, path: Path | str) -> str | None:
        return self._read(self._html(Path(path).name))

    def read_json_text(self, path: Path | str) -> str | None:
        return self._read(self._json(Path(path).name))
```

Update `remove` to also unlink the HTML artifact:

```python
    def remove(self, path: Path | str) -> None:
        name = Path(path).name
        self._json(name).unlink(missing_ok=True)
        self._md(name).unlink(missing_ok=True)
        self._html(name).unlink(missing_ok=True)
```

Update the `prune` glob to include `*.html`:

```python
        for artifact in (
            *self._base.glob("*.json"),
            *self._base.glob("*.md"),
            *self._base.glob("*.html"),
        ):
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest backend/tests/test_cache.py -v`
Expected: PASS (all, including the pre-existing cache tests).

- [ ] **Step 5: Commit**

```bash
git checkout backend/uv.lock 2>/dev/null || true
git add backend/src/zilpzalp/cache.py backend/tests/test_cache.py
git commit -m "feat(cache): add html artifact and raw-text read helpers"
```

---

### Task 2: Extractor — emit HTML into the cache

**Files:**
- Modify: `backend/src/zilpzalp/extractor.py:109-133`
- Test: `backend/tests/test_extractor.py`

**Interfaces:**
- Consumes: nothing new.
- Produces: `extract(pdf_path, cache_dir)` now also writes `<stem>.html` to `cache_dir` when the converter produced an HTML file. JSON remains required; Markdown and HTML are best-effort (moved only if present).

- [ ] **Step 1: Write the failing test**

Add to `backend/tests/test_extractor.py`:

```python
def test_extract_writes_html_cache(tmp_path, monkeypatch):
    import zilpzalp.extractor as extractor_mod

    pdf = tmp_path / "rechnung.pdf"
    pdf.write_bytes(b"%PDF-1.4")
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir(exist_ok=True)

    captured = {}

    def fake_convert(*, input_path, output_dir, format):
        captured["format"] = format
        out = Path(output_dir)
        (out / "rechnung.json").write_text(
            json.dumps({"type": "paragraph", "content": "Datum 15.01.2026",
                        "page number": 1}),
            encoding="utf-8",
        )
        (out / "rechnung.md").write_text("# Rechnung", encoding="utf-8")
        (out / "rechnung.html").write_text("<h1>Rechnung</h1>", encoding="utf-8")

    monkeypatch.setattr(extractor_mod.opendataloader_pdf, "convert", fake_convert)

    extract(pdf, cache_dir)

    assert "html" in captured["format"]
    assert (cache_dir / "rechnung.html").read_text(encoding="utf-8") == "<h1>Rechnung</h1>"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest backend/tests/test_extractor.py::test_extract_writes_html_cache -v`
Expected: FAIL — `"html"` not in requested formats and no `rechnung.html` in cache.

- [ ] **Step 3: Implement in `extractor.py`**

In `extract`, change the requested formats and move the HTML output. Replace the `convert(...)` call's `format` argument and add the HTML move after the Markdown move:

```python
        opendataloader_pdf.convert(
            input_path=[str(pdf_path)],
            output_dir=tmp,
            format=["json", "markdown", "html"],
        )
```

After the existing Markdown-move block (`if md_outputs:` ... line 128), add:

```python
        html_outputs = list(Path(tmp).glob("*.html"))
        if html_outputs:
            shutil.move(str(html_outputs[0]), str(cache_dir / f"{stem}.html"))
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest backend/tests/test_extractor.py -v`
Expected: PASS (new test plus the pre-existing extractor tests).

- [ ] **Step 5: Commit**

```bash
git checkout backend/uv.lock 2>/dev/null || true
git add backend/src/zilpzalp/extractor.py backend/tests/test_extractor.py
git commit -m "feat(extractor): also emit html into the document cache"
```

- [ ] **Step 6: Manual verification note (assumption check)**

When a real environment is available, run the worker against a real PDF and confirm `opendataloader-pdf` produced a `.html` cache file. If `convert` rejects `"html"` as a format, drop `"html"` from the list and skip Task 8's HTML tab (Markdown + JSON remain). Record the outcome in the PR description.

---

### Task 3: Route — serve the original PDF inline

**Files:**
- Modify: `backend/src/zilpzalp/web/routes.py`
- Test: `backend/tests/test_routes.py`

**Interfaces:**
- Produces: `GET /documents/{entry_id}/pdf` → the inbox PDF with `Content-Disposition: inline`. Unknown id or missing file → `404`.

- [ ] **Step 1: Write the failing tests**

Add to `backend/tests/test_routes.py`:

```python
def test_document_pdf_served_inline(client):
    entry = _add_ready(client, "rechnung.pdf")
    response = client.get(f"/documents/{entry.id}/pdf")
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert "inline" in response.headers.get("content-disposition", "")
    assert response.content.startswith(b"%PDF")


def test_document_pdf_unknown_id_404(client):
    response = client.get("/documents/deadbeef/pdf")
    assert response.status_code == 404
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest backend/tests/test_routes.py -k document_pdf -v`
Expected: FAIL with 404 for the first test (route not defined).

- [ ] **Step 3: Implement the route**

In `backend/src/zilpzalp/web/routes.py`, add `FileResponse` to the existing FastAPI responses import:

```python
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse, Response
```

Add the route (place after `review_page`):

```python
@router.get("/documents/{entry_id}/pdf")
def document_pdf(request: Request, entry_id: str):
    queue: Queue = request.app.state.queue
    entry = queue.get_by_id(entry_id)
    if entry is None or not entry.path.exists():
        return Response(status_code=404)
    return FileResponse(
        entry.path,
        media_type="application/pdf",
        content_disposition_type="inline",
    )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest backend/tests/test_routes.py -k document_pdf -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git checkout backend/uv.lock 2>/dev/null || true
git add backend/src/zilpzalp/web/routes.py backend/tests/test_routes.py
git commit -m "feat(web): serve original document pdf inline"
```

---

### Task 4: Route + partial — serve extracted content (markdown / html / json)

**Files:**
- Create: `backend/src/zilpzalp/web/templates/_extract_pane.html`
- Modify: `backend/src/zilpzalp/web/routes.py`
- Modify: `backend/src/zilpzalp/web/locales/de.json`, `backend/src/zilpzalp/web/locales/en.json`
- Test: `backend/tests/test_routes.py`

**Interfaces:**
- Consumes: `cache.read_markdown / read_html / read_json_text` (Task 1).
- Produces: `GET /documents/{entry_id}/extract/{kind}` with `kind ∈ {markdown, html, json}`. Returns a rendered `_extract_pane.html` fragment: a `<pre>` for markdown/json, a sandboxed `<iframe srcdoc>` for html, or an "unavailable" note when the cache file is missing. Unknown id or unknown kind → `404`.

- [ ] **Step 1: Write the failing tests**

Add to `backend/tests/test_routes.py`:

```python
def test_extract_markdown_returns_pre(client):
    cfg = app.state.config
    entry = _add_ready(client, "rechnung.pdf")
    Path(cfg.paths.cache).joinpath("rechnung.md").write_text("# Hallo", encoding="utf-8")

    response = client.get(f"/documents/{entry.id}/extract/markdown")
    assert response.status_code == 200
    assert "<pre" in response.text
    assert "# Hallo" in response.text


def test_extract_html_returns_sandboxed_iframe(client):
    cfg = app.state.config
    entry = _add_ready(client, "rechnung.pdf")
    Path(cfg.paths.cache).joinpath("rechnung.html").write_text("<h1>Hi</h1>", encoding="utf-8")

    response = client.get(f"/documents/{entry.id}/extract/html")
    assert response.status_code == 200
    assert "<iframe" in response.text
    assert "sandbox" in response.text
    assert "srcdoc" in response.text


def test_extract_json_is_pretty_printed(client):
    cfg = app.state.config
    entry = _add_ready(client, "rechnung.pdf")
    Path(cfg.paths.cache).joinpath("rechnung.json").write_text('{"a":1,"b":2}', encoding="utf-8")

    response = client.get(f"/documents/{entry.id}/extract/json")
    assert response.status_code == 200
    assert '"a": 1' in response.text  # indented, space after colon


def test_extract_missing_file_shows_unavailable(client):
    entry = _add_ready(client, "rechnung.pdf")
    response = client.get(f"/documents/{entry.id}/extract/markdown")
    assert response.status_code == 200
    assert "Nicht verfügbar" in response.text


def test_extract_unknown_kind_404(client):
    entry = _add_ready(client, "rechnung.pdf")
    response = client.get(f"/documents/{entry.id}/extract/bogus")
    assert response.status_code == 404
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest backend/tests/test_routes.py -k extract -v`
Expected: FAIL (route not defined → 404 for the content tests).

- [ ] **Step 3: Create the partial `_extract_pane.html`**

Create `backend/src/zilpzalp/web/templates/_extract_pane.html`:

```html
{% if content is none %}
<div class="drawer-empty">{{ t('review.extract_unavailable') }}</div>
{% elif kind == 'html' %}
<iframe class="drawer-iframe" sandbox srcdoc="{{ content }}"></iframe>
{% else %}
<pre class="drawer-pre">{{ content }}</pre>
{% endif %}
```

- [ ] **Step 4: Implement the route**

`json` is **not** currently imported in `routes.py`. Add it with the other stdlib imports at the top of the file (alongside `import datetime`, `import os`, `import tempfile`):

```python
import json
```

Add the route (place after `document_pdf`):

```python
@router.get("/documents/{entry_id}/extract/{kind}")
def extract_content(request: Request, entry_id: str, kind: str):
    queue: Queue = request.app.state.queue
    entry = queue.get_by_id(entry_id)
    if entry is None or kind not in ("markdown", "html", "json"):
        return Response(status_code=404)
    cache = request.app.state.cache
    if kind == "markdown":
        content = cache.read_markdown(entry.path)
    elif kind == "html":
        content = cache.read_html(entry.path)
    else:
        content = cache.read_json_text(entry.path)
        if content is not None:
            content = json.dumps(json.loads(content), indent=2, ensure_ascii=False)
    lang = resolve_language(request)
    context = {
        "kind": kind,
        "content": content,
        "lang": lang,
        "t": lambda key, **kw: translate(key, lang, **kw),
    }
    return templates.TemplateResponse(request, "_extract_pane.html", context)
```

- [ ] **Step 5: Add i18n key to both catalogs**

In `backend/src/zilpzalp/web/locales/de.json`, after `"review.msg_target_required"`, add:

```json
  "review.extract_unavailable": "Nicht verfügbar",
```

In `backend/src/zilpzalp/web/locales/en.json`, after `"review.msg_target_required"`, add:

```json
  "review.extract_unavailable": "Not available",
```

(Mind the trailing comma — the inserted line is not the last key in the object.)

- [ ] **Step 6: Run tests to verify they pass**

Run: `uv run pytest backend/tests/test_routes.py -k extract -v`
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git checkout backend/uv.lock 2>/dev/null || true
git add backend/src/zilpzalp/web/routes.py backend/src/zilpzalp/web/templates/_extract_pane.html backend/src/zilpzalp/web/locales/de.json backend/src/zilpzalp/web/locales/en.json backend/tests/test_routes.py
git commit -m "feat(web): serve cached extraction (markdown/html/json) as drawer panes"
```

---

### Task 5: Route — chain to the next ready document on confirm and skip

**Files:**
- Modify: `backend/src/zilpzalp/web/routes.py` (`_execute`, `skip_document`, add `_next_ready`)
- Test: `backend/tests/test_routes.py`

**Interfaces:**
- Consumes: `_by_mtime_desc(entries)` (existing).
- Produces: `_next_ready(queue: Queue) -> QueueEntry | None`. After a successful execute or skip, the `HX-Redirect` points at `/review/{next.id}?flash=…&kind=ok` when another ready document exists, otherwise `/queue?flash=…&kind=ok`.

- [ ] **Step 1: Write the failing tests**

Add to `backend/tests/test_routes.py`:

```python
def test_confirm_advances_to_next_ready_document(client):
    cfg = app.state.config
    cfg.__dict__["summary_mode"] = "never"
    first = _add_ready(client, "first.pdf")
    second = _add_ready(client, "second.pdf")

    response = client.post(
        f"/documents/{first.id}/confirm",
        data=_form(cfg.targets[0].path),
    )

    assert response.status_code == 200
    redirect = response.headers.get("HX-Redirect", "")
    assert redirect.startswith(f"/review/{second.id}")
    assert "flash=" in redirect


def test_confirm_returns_to_queue_when_no_more_ready(client):
    cfg = app.state.config
    cfg.__dict__["summary_mode"] = "never"
    only = _add_ready(client, "only.pdf")

    response = client.post(
        f"/documents/{only.id}/confirm",
        data=_form(cfg.targets[0].path),
    )

    assert response.headers.get("HX-Redirect", "").startswith("/queue")


def test_skip_advances_to_next_ready_document(client):
    first = _add_ready(client, "first.pdf")
    second = _add_ready(client, "second.pdf")

    response = client.post(f"/documents/{first.id}/skip", follow_redirects=False)

    redirect = response.headers.get("HX-Redirect", "")
    assert redirect.startswith(f"/review/{second.id}")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest backend/tests/test_routes.py -k "advances or no_more_ready" -v`
Expected: FAIL — current code always redirects to `/queue`.

- [ ] **Step 3: Add the `_next_ready` helper**

In `routes.py`, after `_recent` (around line 79), add:

```python
def _next_ready(queue: Queue):
    """First ready, reviewable entry in newest-first order, or None."""
    for entry in _by_mtime_desc(queue.list()):
        if entry.status == "ready" and entry.suggestion is not None:
            return entry
    return None
```

- [ ] **Step 4: Use it in `_execute`**

Replace the body of `_execute` (lines ~233-242) so the redirect targets the next ready document:

```python
def _execute(request, entry, filename, target_paths, config):
    queue: Queue = request.app.state.queue
    lang = resolve_language(request)
    process(entry.path, filename, target_paths, config)
    queue.remove(entry.path)
    request.app.state.cache.remove(entry.path)
    message = translate("toast.filed", lang, filename=filename)
    nxt = _next_ready(queue)
    target = f"/review/{nxt.id}" if nxt else "/queue"
    resp = Response(status_code=200)
    resp.headers["HX-Redirect"] = target + "?flash=" + quote(message) + "&kind=ok"
    return resp
```

- [ ] **Step 5: Use it in `skip_document`**

In `skip_document`, replace the final success redirect (the `message = translate("toast.skipped", ...)` block) with:

```python
    message = translate("toast.skipped", lang, filename=entry.path.name)
    nxt = _next_ready(queue)
    target = f"/review/{nxt.id}" if nxt else "/queue"
    return Response(status_code=200, headers={
        "HX-Redirect": target + "?flash=" + quote(message) + "&kind=ok"
    })
```

- [ ] **Step 6: Run the full routes suite**

Run: `uv run pytest backend/tests/test_routes.py -v`
Expected: PASS — the new chaining tests plus the existing single-document tests (which still redirect to `/queue` because only one document is queued).

- [ ] **Step 7: Commit**

```bash
git checkout backend/uv.lock 2>/dev/null || true
git add backend/src/zilpzalp/web/routes.py backend/tests/test_routes.py
git commit -m "feat(web): advance to next ready document after confirm and skip"
```

---

### Task 6: Review page — no preselected date

**Files:**
- Modify: `backend/src/zilpzalp/web/templates/review.html:17,25`
- Modify: `backend/src/zilpzalp/web/routes.py` (`review_page` context)
- Modify: `backend/src/zilpzalp/web/locales/de.json`, `backend/src/zilpzalp/web/locales/en.json` (`review.choose_date_hint`)
- Test: `backend/tests/test_routes.py`

**Interfaces:**
- Consumes: nothing new.
- Produces: review page renders with no date candidate carrying the `sel` class and an empty `data-selected-date`, so the existing JS keeps "Bestätigen" disabled until the user picks a date.

- [ ] **Step 1: Write the failing test**

Add to `backend/tests/test_routes.py`:

```python
def test_review_has_no_preselected_date(client):
    entry = _add_ready(client, "rechnung.pdf")
    response = client.get(f"/review/{entry.id}")
    assert response.status_code == 200
    body = response.text
    assert "date-opt sel" not in body          # no candidate preselected
    assert 'data-selected-date=""' in body     # hidden value starts empty
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest backend/tests/test_routes.py::test_review_has_no_preselected_date -v`
Expected: FAIL — candidate 0 currently carries `sel` and `data-selected-date` is seeded.

- [ ] **Step 3: Edit `review.html`**

Change the hidden date input (line 17) so it starts empty:

```html
    <input type="hidden" name="date_value" data-selected-date="" />
```

Change the candidate button (line 25) so no candidate is preselected:

```html
          <button type="button" class="date-opt" data-date="{{ c.normalized }}">
```

- [ ] **Step 4: Update the hint copy in both catalogs**

In `backend/src/zilpzalp/web/locales/de.json`, replace `review.choose_date_hint`:

```json
  "review.choose_date_hint": "Alle gefundenen Datumsangaben. Bitte eine wählen.",
```

In `backend/src/zilpzalp/web/locales/en.json`, replace `review.choose_date_hint`:

```json
  "review.choose_date_hint": "All detected dates. Please choose one.",
```

- [ ] **Step 5: Drop the now-unused `preselected_index` from the review context**

In `routes.py` `review_page`, remove the `"preselected_index": suggestion.preselected_date_index or 0,` line from the `context.update({...})` block (the template no longer references it). Leave `_preselected_date` (used by the overview/queue lists) untouched.

- [ ] **Step 6: Run tests to verify they pass**

Run: `uv run pytest backend/tests/test_routes.py -k review -v`
Expected: PASS — new test plus existing review tests (none assert preselection).

- [ ] **Step 7: Commit**

```bash
git checkout backend/uv.lock 2>/dev/null || true
git add backend/src/zilpzalp/web/templates/review.html backend/src/zilpzalp/web/routes.py backend/src/zilpzalp/web/locales/de.json backend/src/zilpzalp/web/locales/en.json backend/tests/test_routes.py
git commit -m "feat(web): require an explicit date choice on the review page"
```

---

### Task 7: Review page — highlight + open the original PDF

**Files:**
- Modify: `backend/src/zilpzalp/web/templates/review.html:8-11`
- Modify: `backend/src/zilpzalp/web/static/styles.css`
- Modify: `backend/src/zilpzalp/web/locales/de.json`, `backend/src/zilpzalp/web/locales/en.json`
- Test: `backend/tests/test_routes.py`

**Interfaces:**
- Consumes: `GET /documents/{id}/pdf` (Task 3).
- Produces: the original filename in the review header is a styled, clickable link opening the PDF in a new tab.

- [ ] **Step 1: Write the failing test**

Add to `backend/tests/test_routes.py`:

```python
def test_review_links_original_pdf_in_new_tab(client):
    entry = _add_ready(client, "rechnung.pdf")
    body = client.get(f"/review/{entry.id}").text
    assert f'href="/documents/{entry.id}/pdf"' in body
    assert 'target="_blank"' in body
    assert "rechnung.pdf" in body
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest backend/tests/test_routes.py::test_review_links_original_pdf_in_new_tab -v`
Expected: FAIL — the filename is currently a non-link `<p>`.

- [ ] **Step 3: Edit the review header in `review.html`**

Replace the `view-head` block (lines 8-11) with a highlighted, clickable original name:

```html
  <div class="view-head" style="margin-bottom:22px">
    <h1 class="view-title">{{ t('review.title') }}</h1>
    <a class="orig-file" href="/documents/{{ entry.id }}/pdf" target="_blank" rel="noopener">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" style="width:15px;height:15px;flex:none"><path d="M14 3v5h5M14 3l5 5v11a1 1 0 0 1-1 1H6a1 1 0 0 1-1-1V4a1 1 0 0 1 1-1z"/></svg>
      <span class="mono">{{ entry.path.name }}</span>
    </a>
  </div>
```

- [ ] **Step 4: Add styles in `styles.css`**

Append to `backend/src/zilpzalp/web/static/styles.css`:

```css
.orig-file {
  display: inline-flex; align-items: center; gap: 8px;
  margin-top: 8px; padding: 5px 11px;
  border: 1px solid var(--accent-line); border-radius: 8px;
  background: var(--accent-bg); color: var(--accent);
  font-size: 13.5px; text-decoration: none;
}
.orig-file:hover { filter: brightness(1.08); }
```

- [ ] **Step 5: Add i18n key (open-pdf label) to both catalogs**

This label is reused by the drawer in Task 8. In `de.json`, after `review.extract_unavailable`, add:

```json
  "review.open_pdf": "PDF öffnen",
```

In `en.json`, after `review.extract_unavailable`, add:

```json
  "review.open_pdf": "Open PDF",
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `uv run pytest backend/tests/test_routes.py -k "review or pdf" -v`
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git checkout backend/uv.lock 2>/dev/null || true
git add backend/src/zilpzalp/web/templates/review.html backend/src/zilpzalp/web/static/styles.css backend/src/zilpzalp/web/locales/de.json backend/src/zilpzalp/web/locales/en.json backend/tests/test_routes.py
git commit -m "feat(web): highlight and open the original pdf from the review header"
```

---

### Task 8: Review page — extraction drawer (Markdown / HTML / JSON + PDF)

**Files:**
- Modify: `backend/src/zilpzalp/web/templates/review.html` (drawer trigger + drawer markup)
- Modify: `backend/src/zilpzalp/web/static/app.js`
- Modify: `backend/src/zilpzalp/web/static/styles.css`
- Modify: `backend/src/zilpzalp/web/locales/de.json`, `backend/src/zilpzalp/web/locales/en.json`
- Test: `backend/tests/test_routes.py`

**Interfaces:**
- Consumes: `GET /documents/{id}/extract/{kind}` (Task 4), `GET /documents/{id}/pdf` (Task 3), `review.open_pdf` key (Task 7).
- Produces: a right-side overlay drawer with three lazy HTMX-loaded tabs (Markdown default) plus an "Open PDF" link. JS toggles the drawer and the active tab; HTMX fetches each pane into `#drawer-pane`.

- [ ] **Step 1: Write the failing test**

Add to `backend/tests/test_routes.py`:

```python
def test_review_renders_extraction_drawer(client):
    entry = _add_ready(client, "rechnung.pdf")
    body = client.get(f"/review/{entry.id}").text
    assert "Extrahierten Inhalt ansehen" in body          # trigger button
    assert f'/documents/{entry.id}/extract/markdown' in body
    assert f'/documents/{entry.id}/extract/html' in body
    assert f'/documents/{entry.id}/extract/json' in body
    assert 'id="extract-drawer"' in body
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest backend/tests/test_routes.py::test_review_renders_extraction_drawer -v`
Expected: FAIL — no drawer markup yet.

- [ ] **Step 3: Add the drawer trigger button**

In `review.html`, inside the `.review-actions` block, add a ghost trigger button before the cancel link (so it sits with the other actions). Replace the opening of `.review-actions` (line 99) with:

```html
        <div class="review-actions">
          <button type="button" class="btn ghost" data-drawer-open="extract-drawer">
            {{ t('review.extract_button') }}
          </button>
          <a class="btn ghost" href="/queue">{{ t('action.cancel') }}</a>
```

- [ ] **Step 4: Add the drawer markup**

In `review.html`, immediately before the closing `</form>` (line 114), insert the drawer:

```html
    <div class="drawer-scrim" id="extract-drawer" hidden>
      <aside class="drawer" onclick="event.stopPropagation()">
        <div class="drawer-head">
          <h2 class="drawer-title">{{ t('review.extract_title') }}</h2>
          <button type="button" class="drawer-close" data-drawer-close aria-label="{{ t('review.extract_close') }}">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" style="width:16px;height:16px"><path d="M6 6l12 12M18 6L6 18"/></svg>
          </button>
        </div>
        <div class="drawer-tabs">
          <button type="button" class="drawer-tab active" data-drawer-tab
                  hx-get="/documents/{{ entry.id }}/extract/markdown" hx-target="#drawer-pane" hx-swap="innerHTML">
            {{ t('review.extract_tab_markdown') }}
          </button>
          <button type="button" class="drawer-tab" data-drawer-tab
                  hx-get="/documents/{{ entry.id }}/extract/html" hx-target="#drawer-pane" hx-swap="innerHTML">
            {{ t('review.extract_tab_html') }}
          </button>
          <button type="button" class="drawer-tab" data-drawer-tab
                  hx-get="/documents/{{ entry.id }}/extract/json" hx-target="#drawer-pane" hx-swap="innerHTML">
            {{ t('review.extract_tab_json') }}
          </button>
          <a class="drawer-tab drawer-pdf" href="/documents/{{ entry.id }}/pdf" target="_blank" rel="noopener">
            {{ t('review.open_pdf') }}
          </a>
        </div>
        <div class="drawer-pane" id="drawer-pane"></div>
      </aside>
    </div>
```

- [ ] **Step 5: Add drawer behavior in `app.js`**

In `backend/src/zilpzalp/web/static/app.js`, inside the existing top-level `document.addEventListener("click", ...)` handler (the one that handles theme toggle and toast close), add drawer handling. After the toast-close block (`if (close) { ... }`), add:

```javascript
    var openBtn = e.target.closest("[data-drawer-open]");
    if (openBtn) {
      var drawer = document.getElementById(openBtn.getAttribute("data-drawer-open"));
      if (drawer) {
        drawer.hidden = false;
        var firstTab = drawer.querySelector("[data-drawer-tab]");
        if (firstTab) firstTab.click();  // lazy-load the default (Markdown) pane
      }
      return;
    }
    var closeBtn = e.target.closest("[data-drawer-close]");
    if (closeBtn) { closeBtn.closest(".drawer-scrim").hidden = true; return; }
    var scrim = e.target.closest(".drawer-scrim");
    if (scrim && e.target === scrim) { scrim.hidden = true; return; }
    var tab = e.target.closest("[data-drawer-tab]");
    if (tab) {
      tab.parentNode.querySelectorAll("[data-drawer-tab]").forEach(function (b) {
        b.classList.remove("active");
      });
      tab.classList.add("active");
      // htmx handles the fetch via the tab's hx-get attributes
    }
```

- [ ] **Step 6: Add drawer styles in `styles.css`**

Append to `backend/src/zilpzalp/web/static/styles.css`:

```css
.drawer-scrim { position: fixed; inset: 0; z-index: 80; background: rgba(0,0,0,.5);
  display: flex; justify-content: flex-end; animation: fadeIn .15s ease; }
.drawer { width: min(560px, 92vw); height: 100%; background: var(--surface);
  border-left: 1px solid var(--border); display: flex; flex-direction: column;
  animation: drawerIn .2s ease; }
@keyframes drawerIn { from { transform: translateX(24px); opacity: .6; } to { transform: none; opacity: 1; } }
.drawer-head { display: flex; align-items: center; justify-content: space-between;
  padding: 18px 20px; border-bottom: 1px solid var(--border); }
.drawer-title { font-size: 17px; font-weight: 680; margin: 0; }
.drawer-close { background: none; border: none; color: var(--text-2); cursor: pointer; padding: 4px; }
.drawer-tabs { display: flex; gap: 4px; padding: 12px 16px 0; border-bottom: 1px solid var(--border); }
.drawer-tab { background: none; border: none; cursor: pointer; padding: 8px 12px;
  font-size: 13.5px; color: var(--text-2); border-bottom: 2px solid transparent; text-decoration: none; }
.drawer-tab.active { color: var(--text); border-bottom-color: var(--accent); }
.drawer-pdf { margin-left: auto; color: var(--accent); }
.drawer-pane { flex: 1; overflow: auto; padding: 16px 20px; }
.drawer-pre { white-space: pre-wrap; word-break: break-word; font-size: 12.5px;
  font-family: var(--mono, monospace); color: var(--text); margin: 0; }
.drawer-iframe { width: 100%; height: 100%; border: 0; background: #fff; }
.drawer-empty { color: var(--text-2); font-size: 14px; padding: 24px 0; text-align: center; }
```

- [ ] **Step 7: Add the drawer i18n keys to both catalogs**

In `de.json`, after `review.open_pdf`, add:

```json
  "review.extract_button": "Extrahierten Inhalt ansehen",
  "review.extract_title": "Extrahierter Inhalt",
  "review.extract_close": "Schließen",
  "review.extract_tab_markdown": "Markdown",
  "review.extract_tab_html": "HTML",
  "review.extract_tab_json": "JSON",
```

In `en.json`, after `review.open_pdf`, add:

```json
  "review.extract_button": "View extracted content",
  "review.extract_title": "Extracted content",
  "review.extract_close": "Close",
  "review.extract_tab_markdown": "Markdown",
  "review.extract_tab_html": "HTML",
  "review.extract_tab_json": "JSON",
```

- [ ] **Step 8: Run tests to verify they pass**

Run: `uv run pytest backend/tests/test_routes.py -k drawer -v`
Expected: PASS.

- [ ] **Step 9: Verify the i18n catalogs are valid JSON and keys match**

Run: `uv run python -c "import json,pathlib; [json.loads(pathlib.Path('backend/src/zilpzalp/web/locales/'+f).read_text()) for f in ('de.json','en.json')]; print('ok')"`
Expected: `ok` (no JSONDecodeError from a stray/missing comma).

- [ ] **Step 10: Commit**

```bash
git checkout backend/uv.lock 2>/dev/null || true
git add backend/src/zilpzalp/web/templates/review.html backend/src/zilpzalp/web/static/app.js backend/src/zilpzalp/web/static/styles.css backend/src/zilpzalp/web/locales/de.json backend/src/zilpzalp/web/locales/en.json backend/tests/test_routes.py
git commit -m "feat(web): add extraction drawer with markdown/html/json tabs to review"
```

---

### Task 9: Full suite + lint + backlog update

**Files:**
- Modify: `docs/backlog.md`

- [ ] **Step 1: Run the full backend test suite**

Run: `uv run pytest backend -q`
Expected: PASS (no failures). If `backend/uv.lock` was rewritten, restore it: `git checkout backend/uv.lock`.

- [ ] **Step 2: Run the linter**

Run: `uv run ruff check backend/src`
Expected: clean for the files touched by this plan. (The pre-existing `F401` in `backend/tests/test_i18n.py` is a separate backlog item — do not fix it here.)

- [ ] **Step 3: Move the three ideas into the Umsetzung table**

In `docs/backlog.md`, per the Pflege-Regel: add one row to the `## Umsetzung` table (next number after 6) describing this review-page optimization, linking the design doc `docs/superpowers/specs/2026-06-17-0955-review-page-optimization-design.md`, with `Art = Feature`, `Status = ✅`, and the merge commit SHA (fill in after merge; use `—` until then). Remove the three now-implemented bullets from `## Ideen / später`: "Extrahierte Inhalte in der Review-Preview anzeigen", "Review-Seite — nahtlos weiterarbeiten + Fehlbestätigung verhindern", and "Review-Seite — originalen Dateinamen hervorheben".

- [ ] **Step 4: Commit**

```bash
git add docs/backlog.md
git commit -m "docs(backlog): track review page optimization"
```

---

## Notes for the implementer

- **HTMX is already loaded** globally (`base.html`); the drawer tabs need only `hx-get`/`hx-target`/`hx-swap` attributes — `app.js` re-inits review interactions on `htmx:afterSwap`, but the drawer panes contain no review-form, so no extra wiring is needed.
- **Iframe isolation:** the HTML pane uses `<iframe sandbox srcdoc="…">`. Jinja autoescaping escapes the cached HTML into the `srcdoc` attribute; `sandbox` (no allow-tokens) blocks scripts and same-origin access. Do not add `allow-scripts`.
- **Flash on `/review/{id}`:** the review page goes through `_base_context`, which reads the `flash`/`kind` query params and the base template renders the toast — so chaining preserves the "filed/skipped" toast without extra work.
- **Single source for "next ready":** only `_next_ready` decides the redirect target; both `_execute` (covers direct + modal execute) and `skip_document` call it.
