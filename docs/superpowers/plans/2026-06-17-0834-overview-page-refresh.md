# Overview-Seite Refresh Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Politur der Übersichtsseite (`/`): gleichmäßiges Counter-Layout, Betriebsangaben unter dem Upload, „bereit"-Badge in der Liste, jüngste-zuerst-Sortierung und aufgeräumtes Upload-Feedback.

**Architecture:** Reine Web-Schicht. Backend-Änderung beschränkt sich auf einen Sortier-Helfer in `routes.py` (kein Model-, Worker- oder Persistenz-Eingriff). Rest sind Jinja-Templates, eine CSS-Regel, ein i18n-Wert und eine JS-Funktion.

**Tech Stack:** FastAPI + Jinja2, HTMX (Polling), Vanilla-JS, pytest + FastAPI `TestClient`.

Spec: [docs/superpowers/specs/2026-06-17-0834-overview-page-refresh-design.md](../specs/2026-06-17-0834-overview-page-refresh-design.md)

## Global Constraints

- Doku/README/mkdocs auf Englisch; UI-Texte über die i18n-Kataloge (`de.json` + `en.json`), nie hartkodiert.
- Conventional Commits (Englisch). Add/Commit/Push selbstständig nach jedem abgeschlossenen Task.
- `uv run` schreibt evtl. `backend/uv.lock` ohne Dep-Änderung neu — vor dem Commit zurücksetzen, falls keine Deps geändert wurden.
- Tests laufen aus `backend/`: `cd backend && uv run pytest`.
- Simplicity first / surgical changes: nur anfassen, was die Task verlangt.

## File Structure

- `backend/src/zilpzalp/web/routes.py` — neuer Helfer `_by_mtime_desc`, eingesetzt in `_recent`, `queue_page`, `queue_partial` (Task 1).
- `backend/src/zilpzalp/web/templates/_overview.html` — „bereit"-Badge in der Liste (Task 2).
- `backend/src/zilpzalp/web/locales/de.json`, `en.json` — Label `upload.status.done` (Task 3).
- `backend/src/zilpzalp/web/static/styles.css` — Counter-Grid (Task 4).
- `backend/src/zilpzalp/web/templates/overview.html` — Upload+Ops in eine Spalte (Task 5).
- `backend/src/zilpzalp/web/static/app.js` — Upload-Liste pro Batch leeren (Task 6).
- `backend/tests/test_routes.py`, `backend/tests/test_i18n.py` — Tests.

Reihenfolge: erst die testbaren Backend/Daten-Tasks (1–3), dann die rein visuellen Tasks (4–6, manuell verifiziert).

---

### Task 1: Jüngste-zuerst-Sortierung nach Datei-mtime

**Files:**
- Modify: `backend/src/zilpzalp/web/routes.py` (Helfer + `_recent` Zeile ~68, `queue_page` ~128, `queue_partial` ~137)
- Test: `backend/tests/test_routes.py`

**Interfaces:**
- Consumes: `Queue.list() -> list[QueueEntry]`, `QueueEntry.path: Path` (bestehend).
- Produces: `_by_mtime_desc(entries: Iterable[QueueEntry]) -> list[QueueEntry]` — sortiert absteigend nach `path.stat().st_mtime`; fehlende Datei (OSError) sortiert ans Ende.

- [ ] **Step 1: Failing tests schreiben**

In `backend/tests/test_routes.py` ergänzen (oben `import os` ergänzen, falls nicht vorhanden):

```python
def test_queue_lists_newest_first(client):
    old = _add_ready(client, "old.pdf")
    new = _add_ready(client, "new.pdf")
    os.utime(old.path, (1000, 1000))
    os.utime(new.path, (2000, 2000))
    body = client.get("/partials/queue").text
    assert body.index("new.pdf") < body.index("old.pdf")


def test_overview_recent_newest_first(client):
    old = _add_ready(client, "old.pdf")
    new = _add_ready(client, "new.pdf")
    os.utime(old.path, (1000, 1000))
    os.utime(new.path, (2000, 2000))
    body = client.get("/partials/overview").text
    assert body.index("new.pdf") < body.index("old.pdf")


def test_queue_survives_missing_file(client):
    entry = _add_ready(client, "gone.pdf")
    entry.path.unlink()
    response = client.get("/partials/queue")
    assert response.status_code == 200
```

- [ ] **Step 2: Tests laufen, Fehlschlag bestätigen**

Run: `cd backend && uv run pytest tests/test_routes.py::test_queue_lists_newest_first tests/test_routes.py::test_overview_recent_newest_first -v`
Expected: FAIL — Reihenfolge ist Einfügereihenfolge (old vor new), `body.index` Assertion schlägt fehl. `test_queue_survives_missing_file` läuft evtl. schon grün (kein stat heute).

- [ ] **Step 3: Helfer implementieren und einsetzen**

In `routes.py` nach `_counts(...)` den Helfer einfügen:

```python
def _by_mtime_desc(entries):
    """Sort queue entries newest-first by file mtime; missing files sort last."""
    def _mtime(entry):
        try:
            return entry.path.stat().st_mtime
        except OSError:
            return 0.0
    return sorted(entries, key=_mtime, reverse=True)
```

`_recent` anpassen:

```python
def _recent(queue: Queue, limit: int = 6):
    return _by_mtime_desc(queue.list())[:limit]
```

In `queue_page` und `queue_partial` jeweils `"entries": queue.list()` ersetzen durch `"entries": _by_mtime_desc(queue.list())`.

- [ ] **Step 4: Tests laufen, grün bestätigen**

Run: `cd backend && uv run pytest tests/test_routes.py -v`
Expected: PASS (inkl. der drei neuen Tests und der bestehenden Route-Tests).

- [ ] **Step 5: Commit**

```bash
git checkout -- backend/uv.lock 2>/dev/null || true
git add backend/src/zilpzalp/web/routes.py backend/tests/test_routes.py
git commit -m "feat(web): sort overview and queue newest-first by file mtime"
git push
```

---

### Task 2: „bereit"-Badge in der Übersichtsliste (#80)

**Files:**
- Modify: `backend/src/zilpzalp/web/templates/_overview.html` (Aktionsbereich der `preview-item`, Zeilen ~39-43)
- Test: `backend/tests/test_routes.py`

**Interfaces:**
- Consumes: `STATUS_BADGE` (Jinja-Global, bestehend), `entry.status`, `entry.id`, `t(...)`.
- Produces: keine.

- [ ] **Step 1: Failing test schreiben**

In `backend/tests/test_routes.py` ergänzen:

```python
def test_overview_recent_shows_ready_badge(client):
    _add_ready(client, "rechnung.pdf")
    body = client.get("/partials/overview").text
    assert "b-ready" in body
    assert "/review/" in body
```

- [ ] **Step 2: Test laufen, Fehlschlag bestätigen**

Run: `cd backend && uv run pytest tests/test_routes.py::test_overview_recent_shows_ready_badge -v`
Expected: FAIL — `ready`-Zeilen zeigen heute nur den Review-Button, kein `b-ready`-Badge.

- [ ] **Step 3: Template anpassen**

In `_overview.html` den Block

```html
          {% if entry.status == 'ready' %}
            <a class="btn sm primary" href="/review/{{ entry.id }}">{{ t('action.review') }}</a>
          {% else %}
            <span class="badge {{ STATUS_BADGE[entry.status] }}"><span class="dot"></span>{{ t('status.' ~ entry.status) }}</span>
          {% endif %}
```

ersetzen durch:

```html
          <div style="display:flex;gap:8px;align-items:center">
            <span class="badge {{ STATUS_BADGE[entry.status] }}"><span class="dot"></span>{{ t('status.' ~ entry.status) }}</span>
            {% if entry.status == 'ready' %}
            <a class="btn sm primary" href="/review/{{ entry.id }}">{{ t('action.review') }}</a>
            {% endif %}
          </div>
```

- [ ] **Step 4: Tests laufen, grün bestätigen**

Run: `cd backend && uv run pytest tests/test_routes.py -v`
Expected: PASS (neuer Test grün; bestehende Overview-Tests bleiben grün).

- [ ] **Step 5: Commit**

```bash
git checkout -- backend/uv.lock 2>/dev/null || true
git add backend/src/zilpzalp/web/templates/_overview.html backend/tests/test_routes.py
git commit -m "feat(web): show ready status badge in overview recent list"
git push
```

---

### Task 3: Upload-Status „fertig" → „hochgeladen" (#96c)

**Files:**
- Modify: `backend/src/zilpzalp/web/locales/de.json` (Zeile ~97), `backend/src/zilpzalp/web/locales/en.json` (Zeile ~97)
- Test: `backend/tests/test_i18n.py`

**Interfaces:**
- Consumes: `translate(key, lang)` aus `zilpzalp.web.i18n`.
- Produces: keine.

- [ ] **Step 1: Failing test schreiben**

In `backend/tests/test_i18n.py` ergänzen (Import `from zilpzalp.web.i18n import translate` ist dort bereits vorhanden — sonst ergänzen):

```python
def test_upload_done_label_uploaded():
    assert translate("upload.status.done", "de") == "hochgeladen"
    assert translate("upload.status.done", "en") == "uploaded"
```

- [ ] **Step 2: Test laufen, Fehlschlag bestätigen**

Run: `cd backend && uv run pytest tests/test_i18n.py::test_upload_done_label_uploaded -v`
Expected: FAIL — aktuell „fertig" / „done".

- [ ] **Step 3: Kataloge anpassen**

`de.json`: `"upload.status.done": "fertig"` → `"upload.status.done": "hochgeladen"`.
`en.json`: `"upload.status.done": "done"` → `"upload.status.done": "uploaded"`.

- [ ] **Step 4: Test laufen, grün bestätigen**

Run: `cd backend && uv run pytest tests/test_i18n.py -v`
Expected: PASS (neuer Test grün; Katalog-Vollständigkeitstests bleiben grün).

- [ ] **Step 5: Commit**

```bash
git checkout -- backend/uv.lock 2>/dev/null || true
git add backend/src/zilpzalp/web/locales/de.json backend/src/zilpzalp/web/locales/en.json backend/tests/test_i18n.py
git commit -m "feat(web): rename upload status 'done' to 'uploaded'"
git push
```

---

### Task 4: Counter-Boxen gleichmäßig layouten (#85)

**Files:**
- Modify: `backend/src/zilpzalp/web/static/styles.css` (Zeile ~196)

**Interfaces:** keine. Reine CSS-Änderung, kein automatisierter Test (manuelle Sichtprüfung).

- [ ] **Step 1: CSS-Regel ändern**

In `styles.css` die Basisregel

```css
.counters { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: var(--gap); }
```

ändern zu:

```css
.counters { display: grid; grid-template-columns: repeat(4, 1fr); gap: var(--gap); }
```

Die bestehende Schmal-Regel `.counters { grid-template-columns: repeat(2, 1fr); }` (im Media-Query, Zeile ~473) bleibt unverändert und liefert 2×2.

- [ ] **Step 2: Manuell verifizieren**

Run: `docker compose up -d --build` (Repo-Root) und <http://localhost:8000> öffnen. Die mitgelieferte `demo/`-Inbox enthält bereits ein Dokument, das vier Counter befüllt.
Expected: Breit → vier Counter in einer Reihe (1×4). Fenster auf < ~720px verschmälern → 2×2. Nie 3+1.

- [ ] **Step 3: Commit**

```bash
git checkout -- backend/uv.lock 2>/dev/null || true
git add backend/src/zilpzalp/web/static/styles.css
git commit -m "fix(web): lay out the four overview counters as 1x4 / 2x2"
git push
```

---

### Task 5: Betriebsangaben unter „Hochladen" platzieren (#88)

**Files:**
- Modify: `backend/src/zilpzalp/web/templates/overview.html` (Zeilen ~7-39)

**Interfaces:** keine neuen. Markup-Umbau; bestehender Test `test_overview_renders_counters_and_betriebsangaben` muss grün bleiben (prüft, dass „Betriebsangaben" weiterhin gerendert wird).

- [ ] **Step 1: Markup umbauen**

In `overview.html` enthält `<div class="dash-cols">` heute drei Kinder: den pollenden `dash-stack`, die Upload-Karte und die Ops-Karte. Upload-Karte und Ops-Karte in einen gemeinsamen `<div class="dash-stack">` als zweites Grid-Kind zusammenfassen. Resultat:

```html
  <div class="dash-cols">
    <div class="dash-stack" hx-get="/partials/overview" hx-trigger="every 2s" hx-swap="innerHTML">
      {% include "_overview.html" %}
    </div>

    <div class="dash-stack">
      <div class="card card-pad">
        <h2 class="card-h">{{ t('upload.title') }}</h2>
        <div id="upload-zone" class="upload-zone" data-msg-not-pdf="{{ t('upload.err_not_pdf') }}"
             data-label-queued="{{ t('upload.status.queued') }}"
             data-label-uploading="{{ t('upload.status.uploading') }}"
             data-label-done="{{ t('upload.status.done') }}"
             data-label-error="{{ t('upload.status.error') }}">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" style="width:28px;height:28px"><path d="M12 16V4M7 9l5-5 5 5"/><path d="M4 16v3a1 1 0 0 0 1 1h14a1 1 0 0 0 1-1v-3"/></svg>
          <div class="uz-text">{{ t('upload.dropzone') }}</div>
          <div class="uz-hint">{{ t('upload.hint') }}</div>
          <input id="upload-input" type="file" accept="application/pdf,.pdf" multiple hidden />
        </div>
        <div id="upload-list" class="upload-list"></div>
      </div>

      <div class="card card-pad">
        <h2 class="card-h">{{ t('overview.operations') }}</h2>
        <div class="info-grid">
          <div class="info-cell"><div class="info-k">{{ t('overview.watchfolder') }}</div><div class="info-v mono">{{ config.paths.watchfolder }}</div></div>
          <div class="info-cell"><div class="info-k">{{ t('overview.config_file') }}</div><div class="info-v mono">{{ config_path }}</div></div>
          <div class="info-cell"><div class="info-k">{{ t('overview.original_handling') }}</div><div class="info-v">{{ t('original.' ~ config.original_handling) }}</div></div>
          <div class="info-cell"><div class="info-k">{{ t('overview.summary') }}</div><div class="info-v">{{ t('summary_mode.' ~ config.summary_mode) }}</div></div>
          <div class="info-cell"><div class="info-k">{{ t('overview.targets') }}</div><div class="info-v">{{ config.targets | length }}</div></div>
          <div class="info-cell"><div class="info-k">{{ t('overview.patterns') }}</div><div class="info-v">{{ config.patterns | length }}</div></div>
          <div class="info-cell span2"><div class="info-k">{{ t('overview.rules') }}</div><div class="info-v">{{ config.rules | length }}</div></div>
        </div>
      </div>
    </div>
  </div>
```

- [ ] **Step 2: Bestehende Tests laufen**

Run: `cd backend && uv run pytest tests/test_routes.py -v`
Expected: PASS — insbesondere `test_overview_renders_counters_and_betriebsangaben` bleibt grün.

- [ ] **Step 3: Manuell verifizieren**

`docker compose up -d --build`, <http://localhost:8000> öffnen. Expected: linke Spalte = Counter + „Jüngste Dokumente"; rechte Spalte = „PDFs hochladen" **oben**, „Betriebsangaben" direkt darunter. Schmaler Viewport: beide Spalten untereinander.

- [ ] **Step 4: Commit**

```bash
git checkout -- backend/uv.lock 2>/dev/null || true
git add backend/src/zilpzalp/web/templates/overview.html
git commit -m "feat(web): place operational details below upload card"
git push
```

---

### Task 6: Upload-Liste pro Batch leeren (#96b)

**Files:**
- Modify: `backend/src/zilpzalp/web/static/app.js` (`enqueue`-Funktion in `initUpload`)

**Interfaces:** keine. Client-seitig; manuelle Sichtprüfung.

- [ ] **Step 1: `enqueue` anpassen**

In `app.js` in der Funktion `enqueue(files)` als erste Anweisung die bestehende Liste leeren, bevor neue Zeilen angelegt werden:

```js
    function enqueue(files) {
      list.replaceChildren();
      Array.prototype.forEach.call(files, function (file) {
        if (!isPdf(file)) {
          var row = addRow(file.name, notPdfMsg);
          row.className = "upload-row error";
          return;
        }
        var r = addRow(file.name, L.queued);
        pending.push({ file: file, row: r, bar: r.querySelector(".ur-bar > span") });
      });
      pump();
    }
```

(`pending` wird bewusst nicht geleert, damit ein noch laufender Upload aus einer vorherigen Charge serverseitig nicht verloren geht; nur die sichtbare Liste wird zurückgesetzt.)

- [ ] **Step 2: Manuell verifizieren**

`docker compose up -d --build`, <http://localhost:8000> öffnen. Eine PDF hochladen → eine Zeile. Danach erneut eine andere PDF wählen → die Liste zeigt **nur** die neue Datei (die alte Zeile ist weg). Der Status der fertigen Datei heißt „hochgeladen" (aus Task 3).

- [ ] **Step 3: Commit**

```bash
git checkout -- backend/uv.lock 2>/dev/null || true
git add backend/src/zilpzalp/web/static/app.js
git commit -m "feat(web): reset upload feedback list per upload batch"
git push
```

---

## Abschluss

- [ ] **Volle Testsuite + Linter grün**

Run: `cd backend && uv run pytest && uv run ruff check .`
Expected: alle Tests PASS, ruff ohne neue Fehler (der vorbestehende F401 in `test_i18n.py` ist ein separater Backlog-Eintrag und nicht Teil dieses Features).

- [ ] **Backlog-Status auf ✅ setzen**

In `docs/backlog.md` Zeile 6 (Overview-Seite — Refresh) Status auf ✅ und in der Spalte `Commit` den finalen (Merge-)Commit-SHA eintragen. Commit:

```bash
git add docs/backlog.md
git commit -m "docs(backlog): mark Overview-Seite refresh as done"
git push
```
