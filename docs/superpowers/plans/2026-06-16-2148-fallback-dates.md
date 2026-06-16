# Fallback Dates Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Guarantee every successfully extracted PDF has at least one date candidate by appending always-on file-level dates (PDF metadata, then file mtime) below the text-extracted dates, so the broken `__…` filename never occurs.

**Architecture:** A new `file_dates(path, config)` reads PDF `CreationDate`/`ModDate` (via pypdf) and the filesystem mtime, returning them as `DateCandidate`s. The worker reads them (it already has the path) and passes them into `analyze()`, which appends and de-duplicates them after the text candidates. The review UI already lets the user pick any candidate or enter a manual date; manual entry stays the last resort and stays required to confirm.

**Tech Stack:** Python 3.12, pypdf (promoted to runtime dep), FastAPI + Jinja2, pytest.

**Spec:** `docs/superpowers/specs/2026-06-16-1924-fallback-dates-design.md`

---

## File Structure

- `backend/src/zilpzalp/analyzer.py` — add `label_key` field to `DateCandidate`; add `file_dates()`; extend `analyze()` to accept + dedup file dates.
- `backend/src/zilpzalp/worker.py` — read `file_dates(path, config)` and pass into `analyze()`.
- `backend/src/zilpzalp/web/templates/review.html` — render `label_key` via the i18n `t()` helper.
- `backend/src/zilpzalp/web/locales/de.json`, `en.json` — add `datelabel.*` strings.
- `backend/pyproject.toml` — move `pypdf>=4.0` from the dev group to runtime dependencies.
- Tests: `backend/tests/test_analyzer.py`, `backend/tests/test_worker.py`, `backend/tests/test_routes.py`.

All commands below run from `backend/` (where `pyproject.toml` lives). The project uses `uv`; run tests with `uv run pytest`.

---

### Task 1: Add `label_key` field to `DateCandidate`

App-generated candidates (file dates) carry a stable label *key* that the template translates, instead of a free-text `label`.

**Files:**
- Modify: `backend/src/zilpzalp/analyzer.py:11-16`
- Test: `backend/tests/test_analyzer.py`

- [ ] **Step 1: Write the failing test**

Add to `backend/tests/test_analyzer.py`:

```python
def test_date_candidate_carries_label_key():
    from zilpzalp.analyzer import DateCandidate

    c = DateCandidate(normalized="2026-01-15", raw="", label_key="pdf_created")
    assert c.label_key == "pdf_created"
    assert c.label is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_analyzer.py::test_date_candidate_carries_label_key -v`
Expected: FAIL — `TypeError: __init__() got an unexpected keyword argument 'label_key'`

- [ ] **Step 3: Add the field**

In `backend/src/zilpzalp/analyzer.py`, change the `DateCandidate` dataclass:

```python
@dataclass(frozen=True)
class DateCandidate:
    normalized: str            # date_format-konform (z. B. 2026-01-15)
    raw: str                   # roher Treffer-Text aus dem PDF (zu markierende Teilzeichenkette)
    label: str | None = None   # strukturgestuetzter Kontext (z. B. "Rechnungsdatum")
    snippet: str | None = None # umgebende Zeile aus dem Block; enthaelt raw
    label_key: str | None = None  # i18n-Schluessel fuer app-erzeugte Labels (z. B. "pdf_created")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_analyzer.py::test_date_candidate_carries_label_key -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/zilpzalp/analyzer.py tests/test_analyzer.py
git commit -m "feat(analyzer): add label_key field to DateCandidate"
```

---

### Task 2: Implement `file_dates()` and promote pypdf to a runtime dependency

Reads PDF metadata dates (CreationDate, ModDate) then filesystem mtime, in that fixed priority order, skipping anything unavailable. Never raises — a pypdf error falls back to mtime alone.

**Files:**
- Modify: `backend/pyproject.toml:6-15` (runtime deps) and `:17-24` (dev group)
- Modify: `backend/src/zilpzalp/analyzer.py` (imports + new function)
- Test: `backend/tests/test_analyzer.py`

- [ ] **Step 1: Move pypdf to runtime dependencies**

In `backend/pyproject.toml`, add `"pypdf>=4.0",` to the `[project] dependencies` list and remove the `pypdf>=4.0` line from `[dependency-groups] dev`. Resulting `dependencies`:

```toml
dependencies = [
    "fastapi>=0.115",
    "pydantic>=2.7",
    "pyyaml>=6.0",
    "opendataloader-pdf>=2.0",
    "watchdog>=4.0",
    "jinja2>=3.1.6",
    "python-multipart>=0.0.32",
    "uvicorn>=0.49.0",
    "pypdf>=4.0",
]
```

Resulting `dev` group (pypdf removed):

```toml
dev = [
    "pytest>=8.2",
    "httpx>=0.27",
    "ruff>=0.5",
    "reportlab>=4.0",
]
```

Then sync: `uv sync`

- [ ] **Step 2: Write the failing tests**

Add to `backend/tests/test_analyzer.py` (imports at top of file as needed):

```python
def _config(tmp_path: Path):
    ...  # ALREADY EXISTS in this file — reuse it; do not redefine.


def _pdf_with_metadata(path, *, created=None, modified=None):
    """Write a minimal PDF carrying the given PDF-date strings (D:YYYYMMDDHHmmSS)."""
    from pypdf import PdfWriter

    writer = PdfWriter()
    writer.add_blank_page(width=595, height=842)
    meta = {}
    if created is not None:
        meta["/CreationDate"] = created
    if modified is not None:
        meta["/ModDate"] = modified
    if meta:
        writer.add_metadata(meta)
    with open(path, "wb") as fh:
        writer.write(fh)


def test_file_dates_reads_pdf_metadata_in_priority_order(tmp_path):
    from zilpzalp.analyzer import file_dates

    pdf = tmp_path / "doc.pdf"
    _pdf_with_metadata(pdf, created="D:20260115120000", modified="D:20260201120000")

    result = file_dates(pdf, _config(tmp_path))
    by_key = [(c.label_key, c.normalized) for c in result]

    # created first, then modified, then mtime (mtime is "today" — just assert presence/order)
    assert by_key[0] == ("pdf_created", "2026-01-15")
    assert by_key[1] == ("pdf_modified", "2026-02-01")
    assert by_key[2][0] == "file_modified"
    assert all(c.raw == "" and c.snippet is None and c.label is None for c in result)


def test_file_dates_falls_back_to_mtime_when_no_metadata(tmp_path):
    from zilpzalp.analyzer import file_dates

    pdf = tmp_path / "nometa.pdf"
    _pdf_with_metadata(pdf)  # blank PDF, no /CreationDate or /ModDate

    result = file_dates(pdf, _config(tmp_path))
    keys = [c.label_key for c in result]

    assert keys == ["file_modified"]


def test_file_dates_falls_back_to_mtime_when_pdf_unreadable(tmp_path):
    from zilpzalp.analyzer import file_dates

    junk = tmp_path / "broken.pdf"
    junk.write_bytes(b"%PDF-1.4 not a real pdf")

    result = file_dates(junk, _config(tmp_path))
    keys = [c.label_key for c in result]

    assert keys == ["file_modified"]  # pypdf raised -> mtime only, no exception
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `uv run pytest tests/test_analyzer.py -k file_dates -v`
Expected: FAIL — `ImportError: cannot import name 'file_dates'`

- [ ] **Step 4: Implement `file_dates()`**

In `backend/src/zilpzalp/analyzer.py`, add imports near the top (after the existing imports):

```python
import datetime
import logging
from pathlib import Path

from pypdf import PdfReader

logger = logging.getLogger(__name__)
```

(Keep the existing `import datetime` — do not duplicate it. Add only `logging`, `Path`, and the `pypdf` import.)

Add this function (place it after `_find_dates_in_text`, before `analyze`):

```python
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
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `uv run pytest tests/test_analyzer.py -k file_dates -v`
Expected: PASS (3 tests)

- [ ] **Step 6: Commit**

```bash
git add src/zilpzalp/analyzer.py tests/test_analyzer.py pyproject.toml uv.lock
git commit -m "feat(analyzer): add file_dates fallback (PDF metadata, then mtime)"
```

---

### Task 3: Append + dedup file dates in `analyze()`

`analyze()` gains an optional `file_dates` parameter. File candidates are appended after the text candidates, skipping any whose normalized value already appears (text wins). The default keeps every existing caller unchanged.

**Files:**
- Modify: `backend/src/zilpzalp/analyzer.py:138` (the `analyze` signature + return)
- Test: `backend/tests/test_analyzer.py`

- [ ] **Step 1: Write the failing tests**

Add to `backend/tests/test_analyzer.py`:

```python
def test_analyze_appends_file_dates_after_text_dates(tmp_path):
    from zilpzalp.analyzer import DateCandidate, analyze

    doc = Document(blocks=[
        Block(kind="paragraph", text="Rechnungsdatum: 15.01.2026", page=1, bbox=(0, 0, 0, 0)),
    ])
    extra = [DateCandidate(normalized="2020-07-09", raw="", label_key="file_modified")]

    analysis = analyze(doc, _config(tmp_path), file_dates=extra)
    normalized = [c.normalized for c in analysis.date_candidates]

    assert normalized == ["2026-01-15", "2020-07-09"]   # text first, file date appended


def test_analyze_dedups_file_date_equal_to_text_date(tmp_path):
    from zilpzalp.analyzer import DateCandidate, analyze

    doc = Document(blocks=[
        Block(kind="paragraph", text="Rechnungsdatum: 15.01.2026", page=1, bbox=(0, 0, 0, 0)),
    ])
    extra = [DateCandidate(normalized="2026-01-15", raw="", label_key="pdf_created")]

    analysis = analyze(doc, _config(tmp_path), file_dates=extra)

    assert [c.normalized for c in analysis.date_candidates] == ["2026-01-15"]  # no duplicate


def test_analyze_without_file_dates_is_unchanged(tmp_path):
    from zilpzalp.analyzer import analyze

    doc = Document(blocks=[
        Block(kind="paragraph", text="Rechnungsdatum: 15.01.2026", page=1, bbox=(0, 0, 0, 0)),
    ])
    analysis = analyze(doc, _config(tmp_path))

    assert [c.normalized for c in analysis.date_candidates] == ["2026-01-15"]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_analyzer.py -k "analyze_appends or analyze_dedups or analyze_without_file_dates" -v`
Expected: FAIL — `analyze() got an unexpected keyword argument 'file_dates'`

- [ ] **Step 3: Extend `analyze()`**

In `backend/src/zilpzalp/analyzer.py`, change the signature and the return block:

```python
def analyze(
    document: Document,
    config: Config,
    file_dates: list[DateCandidate] | None = None,
) -> Analysis:
    full_text = "\n".join(b.text for b in document.blocks)
    candidates: list[DateCandidate] = []
    # ... existing body unchanged: builds text candidates ...
```

Then, just before the `return Analysis(...)`, append + dedup the file dates:

```python
    seen = {c.normalized for c in candidates}
    for fc in file_dates or []:
        if fc.normalized not in seen:
            candidates.append(fc)
            seen.add(fc.normalized)
    return Analysis(
        date_candidates=candidates,
        sender=_detect_sender(document),
        doctype=_detect_doctype(document),
        full_text=full_text,
    )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_analyzer.py -k "analyze_appends or analyze_dedups or analyze_without_file_dates" -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add src/zilpzalp/analyzer.py tests/test_analyzer.py
git commit -m "feat(analyzer): append and dedup file dates in analyze()"
```

---

### Task 4: Wire the worker to supply file dates

The worker already holds the source path. It reads `file_dates(path, config)` and passes them into `analyze()`. Result: a PDF with no text dates still yields a preselected candidate (at least the mtime), so the filename always has a date.

**Files:**
- Modify: `backend/src/zilpzalp/worker.py:10` (import) and `:77` (the `analyze` call)
- Test: `backend/tests/test_worker.py`

- [ ] **Step 1: Write the failing test**

Add to `backend/tests/test_worker.py`:

```python
def test_process_supplies_fallback_date_when_no_text_date(tmp_path, config, monkeypatch):
    pdf = Path(config.paths.watchfolder) / "nodate.pdf"
    pdf.write_bytes(b"%PDF-1.4")  # invalid PDF -> pypdf falls back to mtime
    doc = Document(blocks=[
        Block(kind="paragraph", text="Kein Datum hier drin.", page=1, bbox=(0, 0, 0, 0)),
    ])
    monkeypatch.setattr(worker_mod, "extract", lambda p: doc)

    register, worker = _make_worker(config)
    register.add(pdf)
    worker._process(pdf)

    entry = register.get(pdf)
    assert entry.status == "ready"
    candidates = entry.suggestion.date_candidates
    assert candidates, "expected a fallback candidate when no text date is found"
    assert candidates[0].label_key == "file_modified"
    assert entry.suggestion.preselected_date_index == 0
    assert not entry.suggestion.filename.startswith("__")  # date segment is filled
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_worker.py::test_process_supplies_fallback_date_when_no_text_date -v`
Expected: FAIL — `candidates` is empty (`AssertionError: expected a fallback candidate ...`)

- [ ] **Step 3: Wire the worker**

In `backend/src/zilpzalp/worker.py`, change the import:

```python
from zilpzalp.analyzer import analyze, file_dates
```

And in `_process`, change the analyze call (currently `analysis = analyze(document, config)`):

```python
            analysis = analyze(document, config, file_dates=file_dates(path, config))
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_worker.py -v`
Expected: PASS (including the existing `test_process_marks_ready_with_suggestion`, whose text date `2026-01-15` still sorts first)

- [ ] **Step 5: Commit**

```bash
git add src/zilpzalp/worker.py tests/test_worker.py
git commit -m "feat(worker): supply file-date fallbacks to analyze()"
```

---

### Task 5: Render file-date labels via i18n

App-generated candidates show a localized label (`label_key` → `t()`), while text candidates keep their free-text `label`.

**Files:**
- Modify: `backend/src/zilpzalp/web/locales/de.json`, `backend/src/zilpzalp/web/locales/en.json`
- Modify: `backend/src/zilpzalp/web/templates/review.html:30`
- Test: `backend/tests/test_routes.py`

- [ ] **Step 1: Write the failing test**

In `backend/tests/test_routes.py`, add a candidate with a `label_key` to a ready suggestion and assert the localized label renders. Add this test (it builds its own suggestion so it does not disturb `_ready_suggestion`):

```python
def test_review_renders_localized_file_date_label(client):
    cfg = app.state.config
    pdf = Path(cfg.paths.watchfolder) / "fallback.pdf"
    app.state.queue.add(pdf)
    app.state.queue.set_ready(pdf, Suggestion(
        filename="2020-07-09__Unbekannt_Dokument_.pdf",
        date_candidates=[
            DateCandidate(normalized="2020-07-09", raw="", label_key="file_modified"),
        ],
        preselected_date_index=0,
        sender="",
        doctype="",
        description="",
        pattern_name="standard",
        target_paths=[Path(cfg.targets[0].path)],
    ))
    pdf.write_bytes(b"%PDF-1.4")
    entry = app.state.queue.get(pdf)

    response = client.get(f"/documents/{entry.id}/review")

    assert response.status_code == 200
    assert "Datei geändert" in response.text  # de default locale
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_routes.py::test_review_renders_localized_file_date_label -v`
Expected: FAIL — `"Datei geändert"` not in response (label_key not rendered yet)

- [ ] **Step 3: Add locale strings**

In `backend/src/zilpzalp/web/locales/de.json`, add:

```json
  "datelabel.pdf_created": "PDF erstellt",
  "datelabel.pdf_modified": "PDF geändert",
  "datelabel.file_modified": "Datei geändert",
```

In `backend/src/zilpzalp/web/locales/en.json`, add:

```json
  "datelabel.pdf_created": "PDF created",
  "datelabel.pdf_modified": "PDF modified",
  "datelabel.file_modified": "File modified",
```

(Add inside the top-level JSON object; mind the trailing commas so the file stays valid JSON.)

- [ ] **Step 4: Render the label key in the template**

In `backend/src/zilpzalp/web/templates/review.html`, replace the label line (currently line 30):

```html
                {% if c.label %}<span class="date-ctx"><span class="ctx-label">{{ c.label }}</span></span>{% endif %}
```

with:

```html
                {% if c.label_key %}<span class="date-ctx"><span class="ctx-label">{{ t('datelabel.' + c.label_key) }}</span></span>{% elif c.label %}<span class="date-ctx"><span class="ctx-label">{{ c.label }}</span></span>{% endif %}
```

- [ ] **Step 5: Run test to verify it passes**

Run: `uv run pytest tests/test_routes.py::test_review_renders_localized_file_date_label -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add src/zilpzalp/web/locales/de.json src/zilpzalp/web/locales/en.json src/zilpzalp/web/templates/review.html tests/test_routes.py
git commit -m "feat(web): render file-date labels via i18n"
```

---

### Task 6: Lock in manual date as the last resort (regression test)

The manual-date path already works end-to-end (template input, JS `date_kind="manual"`, confirm route, `_normalize_date`). This task adds a regression test so it cannot silently break. No production code changes.

**Files:**
- Test: `backend/tests/test_routes.py`

- [ ] **Step 1: Write the test**

In `backend/tests/test_routes.py`, add:

```python
def test_confirm_uses_manually_entered_date(client):
    cfg = app.state.config
    cfg.__dict__["summary_mode"] = "never"  # in-memory override for this test
    entry = _add_ready(client, "manual.pdf")

    response = client.post(
        f"/documents/{entry.id}/confirm",
        data=_form(cfg.targets[0].path, date_kind="manual", date_value="2020-07-09"),
    )

    assert response.status_code == 200
    target = Path(cfg.targets[0].path)
    assert any(f.name.startswith("2020-07-09") for f in target.iterdir())
```

- [ ] **Step 2: Run test to verify it passes**

Run: `uv run pytest tests/test_routes.py::test_confirm_uses_manually_entered_date -v`
Expected: PASS (this guards existing behavior; it should pass immediately)

- [ ] **Step 3: Commit**

```bash
git add tests/test_routes.py
git commit -m "test(web): lock manual date as last-resort on confirm"
```

---

### Task 7: Full verification

- [ ] **Step 1: Run the whole suite**

Run: `uv run pytest`
Expected: all tests pass (no regressions in analyzer, worker, routes, naming, pipeline).

- [ ] **Step 2: Lint**

Run: `uv run ruff check src tests`
Expected: no errors.

- [ ] **Step 3: Commit any lint fixes (only if ruff reported something)**

```bash
git add -A
git commit -m "style: ruff fixes for fallback dates"
```

Skip this step entirely if ruff reported no errors.
