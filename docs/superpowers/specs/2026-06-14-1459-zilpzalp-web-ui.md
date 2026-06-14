# ZilpZalp 5b — Web-UI-Umsetzung (Design-Spec)

Status: Entwurf zur Freigabe
Datum: 2026-06-14
Meilenstein: 5b (Roadmap-Zeile 5b)
Grundlagen:
[MVP Design-Spec](2026-06-13-1435-zilpzalp-mvp-design.md) (§3, §3.1, §4, §4.3, §5, §6, §7) ·
[docs/ui.md](../../ui.md) · [5a-Mockups](../../ui/design/)

Dieses Dokument verfeinert das MVP-Design-Spec für die konkrete Web-UI-Umsetzung. Es baut auf
dem vorhandenen Backend (`queue`, `suggestion`, `processor`, `config`, `analyzer`, `extractor`,
`watcher`, `main`) auf und überführt die 5a-Design-Lieferung (HTML/CSS/JSX) in Jinja2-Templates
mit HTMX. Die 5a-Mockups sind die **visuelle Zielmarke** — kein Redesign, nur Überführung.

---

## 1. Scope

**In 5b enthalten:**

- Hintergrund-Worker (`extract → analyze → suggest`, JVM-blockierend, **ein** dedizierter Thread)
- Erweiterung von `QueueEntry`/`Queue` (`id`, `suggestion`, Status `pending`/`analyzing`/`ready`/`error`)
- Erweiterung von `analyzer.DateCandidate` um `snippet` (Kontextsatz für die Datumsanzeige)
- `config.save_config` (atomar, gleiche Validierung wie `load_config`)
- FastAPI-Routen (Seiten, HTMX-Polling-Fragmente, Aktionen)
- Jinja2-Templates + Überführung von `styles.css` und der Interaktions-Logik nach `web/static`
- HTMX-Polling der selbsttätig aktualisierenden Listen
- Confirm/Summary/Konflikt-Flow
- Playwright-Tests

**Bewusst ausgeschlossen (spätere Meilensteine / nicht MVP):**

- mkdocs / Packaging / Dockerfiles → Meilenstein 6
- Das **Tweaks-Panel** der Mockups (Dashboard-Layout-Varianten, Dichte, Akzentfarbe) — reines
  Design-Explorationswerkzeug, **nicht** Teil des Produkts. Die Übersicht wird nur in der
  **zweispaltigen** Variante (`split`) umgesetzt (Default-Tweak der 5a-Lieferung).
- OCR / KI, Hash-Duplikaterkennung, Login (nicht im MVP, MVP-Spec §10)

**Abweichungen vom Mockup (bewusst):**

- Der Konfigurations-Editor zeigt **YAML** (`config.yaml`), nicht das TOML-artige Sample der
  Mockup-`data.js`. Validierung über `load_config`/`save_config`.
- Konflikterkennung ist eine **serverseitige** Prüfung (`Path.exists()` über den `processor`),
  nicht der clientseitige `EXISTING`-Abgleich des Mockups.

---

## 2. Backend-Erweiterungen

### 2.1 `queue.py` — `QueueEntry` und `Queue`

`QueueEntry` wird erweitert; das Register bleibt in-memory und thread-safe (MVP-Spec §4.2):

```python
QueueStatus = Literal["pending", "analyzing", "ready", "error"]

@dataclass(frozen=True)
class QueueEntry:
    id: str                          # uuid4-hex, einmalig bei add() vergeben, über Transitionen stabil
    path: Path
    status: QueueStatus = "pending"
    suggestion: Suggestion | None = None   # gefüllt bei status == "ready"
    error_reason: str | None = None
```

- **`id`**: stabiler Schlüssel für UI-Routen (`/review/{id}`). Wird bei der **ersten** `add()` für
  einen Pfad erzeugt und bei jeder Statustransition mitgeführt. Die Pfad-Dedup (Event + Scan)
  bleibt unverändert (gleicher Pfad → kein zweiter Eintrag, gleiche `id`).
- **Neue/erweiterte Methoden** (frozen-dataclass → Eintrag wird bei Transition ersetzt, `id`
  bleibt erhalten):
  - `add(path) -> bool` — wie bisher, vergibt zusätzlich `id`.
  - `mark_analyzing(path) -> None`
  - `set_ready(path, suggestion) -> None`
  - `mark_error(path, reason) -> None` (vorhanden; trägt `id` weiter)
  - `get_by_id(id) -> QueueEntry | None`
  - `get(path)`, `list()`, `remove(path)` — unverändert.
- Import von `Suggestion` aus `suggestion.py`. (Kein Importzyklus: `suggestion` importiert `queue`
  nicht.)

### 2.2 `analyzer.py` — `DateCandidate` um `snippet` erweitern

Bewusst kleiner Eingriff in das M2-Modul (vom Nutzer freigegeben), um die Datumsanzeige der
Prüfungsansicht mockup-getreu zu treffen (vollständiger Kontextsatz mit markiertem Datum).

```python
@dataclass(frozen=True)
class DateCandidate:
    normalized: str            # date_format-konform
    raw: str                   # roher Treffer-Text (= die zu markierende Teilzeichenkette)
    label: str | None = None   # strukturgestützter Kontext
    snippet: str | None = None # umgebende Zeile/Satz aus dem Block; enthält raw
```

- `snippet` = der den Treffer enthaltende Zeilen-/Satzausschnitt des Blocks (bei Tabellen die
  Zellzeile als zusammengeführter Text). `raw` bleibt die zu markierende Teilzeichenkette; das
  Template hebt `raw` innerhalb von `snippet` hervor (`<mark>`).
- **Unverändert:** Kandidatenmenge, Reihenfolge, Labels, Vorauswahl-Logik. `snippet` ist rein
  additiv. `suggestion`/`Suggestion` brauchen keine Änderung (reichen `date_candidates` durch).
- **Tests (verbindlich):** Snippet-Erfassung für Inline-Treffer (Satz vor/um das Datum) und
  Tabellen-Treffer (Zellzeile); Bestätigung, dass `raw` Teilzeichenkette von `snippet` ist und die
  Kandidatenmenge sich nicht ändert.

### 2.3 `config.py` — `save_config`

```python
def save_config(path: str | Path, text: str) -> Config: ...
```

- Validiert `text` mit **derselben** Logik wie `load_config` (`yaml.safe_load` → `Config(**data)`,
  inkl. Pfad-/Platzhalter-/Wertprüfung). Bei jedem Fehler: `ConfigError` (über
  `_format_validation_error`) **werfen und die bestehende Datei unangetastet lassen**.
- Bei Erfolg: **atomar** schreiben — Temp-Datei im selben Verzeichnis, dann `os.replace`. Gibt das
  geparste `Config` zurück (für die Übernahme in `app.state.config`).
- Die Validierung prüft u. a. die Existenz der Pfade (`watchfolder`, `error_folder`,
  ggf. `processed_folder`) — wie beim Start. Eine fehlerhafte Eingabe kann den Betrieb nicht stören.

### 2.4 `worker.py` — neues Modul (ein Worker-Thread)

```python
class Worker:
    def __init__(self, register: Queue, config_provider: Callable[[], Config]) -> None: ...
    def submit(self, path: Path) -> None: ...   # Watcher-Callback
    def start(self) -> None: ...
    def stop(self) -> None: ...
```

- Interner stdlib-`queue.Queue` als Arbeitskanal; **ein** Daemon-Thread.
- `submit(path)`: `register.add(path)` (Dedup); nur wenn neu → Pfad in den Arbeitskanal legen.
- Thread-Schleife je Pfad:
  1. `register.mark_analyzing(path)`
  2. `document = extract(path)` → `analysis = analyze(document, config)` → `suggestion = suggest(analysis, config)`
     — `config` über `config_provider()` (immer **aktuelle** Config; siehe §4 Laufzeitänderung).
  3. Erfolg → `register.set_ready(path, suggestion)`.
  - `ExtractionError` → Datei nach `config.paths.error_folder` verschieben, `register.mark_error(path, reason)`.
    (Bei Namenskonflikt im `error/`: vorhandene Datei überschreiben — `error/` ist Fehlerspur, kein Archiv.)
  - Jede andere Exception → nach stdout loggen, `register.mark_error(path, "technischer Fehler bei der Analyse")`.
- Verarbeitet seriell (1-Nutzer-Tool, JVM ~1–2 s/PDF). Der initiale Scan liefert Dateien nacheinander
  als `ready`.

### 2.5 `web/naming.py` — gemeinsame Namensbildung

```python
def render_filename(template: str, *, date: str, sender: str, doctype: str,
                    description: str, ext: str) -> str: ...
```

- Slug-Regeln mockup-getreu (`components.jsx` `slug`/`buildName`): Whitespace → `-`,
  Entfernen von `/\:*?"<>|`, Umlaute bleiben. Fallbacks: leerer `sender` → `"Unbekannt"`,
  leerer `doctype` → `"Dokument"`. `date`/`description` ohne Fallback.
- `ext` = Suffix der Quelldatei (faktisch `.pdf`, da der Watcher nur PDFs aufnimmt).
- Die clientseitige Vorschau (`app.js`) implementiert **dieselben** Regeln, damit Live-Vorschau und
  serverseitig erzeugter Name identisch sind. Der finale Name wird beim Confirm/Execute **server­seitig**
  aus den abgeschickten Feldern + gewähltem Pattern-Template neu gebildet (nicht der Vorschau vertraut).

### 2.6 `main.py` — Verdrahtung

- Lifespan: `Queue` anlegen, `Worker(register, lambda: app.state.config)` erzeugen,
  Watcher-Callback = `worker.submit`. `worker.start()` und `watcher.start()`; im `finally`
  beide stoppen.
- Jinja2-`Templates` und `StaticFiles` (`web/static`) einbinden, Web-Router (`web/routes.py`)
  registrieren. `/health` bleibt.

---

## 3. Web-Schicht (`backend/src/zilpzalp/web/`)

### 3.1 Routen (`web/routes.py`)

**Seiten (volle HTML-Dokumente):**

| Methode | Pfad | Inhalt |
|---|---|---|
| GET | `/` | Übersicht (split-Layout): Zähler, Betriebsangaben, jüngste Dokumente |
| GET | `/queue` | Warteschlange (volle Liste) |
| GET | `/config` | Konfigurations-Editor (YAML) |
| GET | `/review/{id}` | Prüfungsansicht — nur bei `status == "ready"`, sonst Redirect auf `/queue` |

**HTMX-Polling-Fragmente** (`hx-get`, Intervall ~2 s, `hx-swap="innerHTML"`):

| Methode | Pfad | Inhalt |
|---|---|---|
| GET | `/partials/overview` | Zähler + Vorschau „jüngste Dokumente" (`_overview.html`) |
| GET | `/partials/queue` | Zeilenliste der Warteschlange (`_queue_list.html`) |

**Aktionen:**

| Methode | Pfad | Verhalten |
|---|---|---|
| POST | `/documents/{id}/confirm` | Formular (Datum-Art+Wert, Absender, Typ, Beschreibung, Pattern, `targets[]`). Server bildet finalen Namen. `summary_mode == "always"` **oder** Konflikt erkannt → **Summary-Modal**-Fragment zurück; sonst direkt ausführen (wie `/execute`). |
| POST | `/documents/{id}/execute` | Gleiche Formularfelder. `processor.process(...)`. `FileConflictError` → Summary-Modal mit markiertem Konflikt, `Ausführen` gesperrt. Erfolg → `queue.remove`, aktualisierte Queue-Liste + Erfolgs-Toast (OOB-Swap). |
| POST | `/config` | `save_config(path, text)`. Erfolg → `app.state.config` ersetzen + Toast. `ConfigError` → Editor mit Fehlerliste neu rendern; alte Config bleibt aktiv. |

- Theme-Umschaltung ist rein clientseitig (`app.js` + `localStorage`), keine Serverroute.
- Datums-Art: gewählter Kandidat liefert seinen `normalized`-Wert direkt; manuelle Eingabe (ISO
  `JJJJ-MM-TT`) wird serverseitig per `config.date_format` normalisiert.

### 3.2 Templates (`web/templates/`)

- `base.html` — Rahmen: Kopfleiste (Marke, Navigation mit `Warteschlange`-Zähler, Theme-Toggle),
  `#toasts`-Container, `<head>` mit Google-Fonts-`<link>` und `styles.css`, `app.js`, `htmx.min.js`.
- `overview.html`, `queue.html`, `review.html`, `config.html` — erweitern `base.html`.
- Partials: `_overview.html`, `_queue_list.html`, `_summary_modal.html`, `_toast.html`.
- Markup und CSS-Klassen werden **1:1** aus den JSX-Komponenten übernommen, sodass `styles.css`
  unverändert greift. Statusabzeichen-Klassen (`b-wait`/`b-ana`/`b-ready`/`b-err`), Karten,
  Datumsoptionen, Ordner-Chips, Namensvorschau, Modal exakt wie im Mockup.

### 3.3 Statische Dateien (`web/static/`)

- `styles.css` — wörtlich aus der 5a-Lieferung übernommen.
- `htmx.min.js` — vendored (kein Build-Step, offline-fähig).
- `app.js` — überführt die clientseitige Interaktion aus `components.jsx`/`review.jsx`/`app.jsx`:
  - Theme-Toggle + `localStorage` + System-Default (`prefers-color-scheme`).
  - Prüfungsansicht: Live-Namensvorschau (`buildName`/`segmentsForName` → `render_filename`-konform),
    Datumsauswahl (inkl. manuell), Ordner-Mehrfachauswahl, `Bestätigen` deaktiviert bis gültig
    (Datum gewählt **und** ≥1 Zielordner).
  - Toast-Auto-Dismiss (Animation/Timeout wie im Mockup).

### 3.4 Confirm / Summary / Konflikt

- **Clientseitig** (app.js): Live-Vorschau, Datums-/Ordnerauswahl, Gültigkeitsprüfung des
  `Bestätigen`-Buttons.
- **Serverseitig**: Konflikt = existierende gleichnamige Zieldatei (`processor`/`Path.exists()`).
  Das Summary-Modal markiert kollidierende Ablageorte und hält `Ausführen` gesperrt. Auflösung
  ausschließlich durch Ändern der Felder (Absender/Typ/Datum/Beschreibung/Pattern) — **kein
  Auto-Suffix** (MVP-Spec §4.1). Abbrechen kehrt ohne Änderung zur Prüfung zurück.
- Zusammenfassung erscheint laut `summary_mode` (`always` | `on_conflict` | `never`); ein Konflikt
  erzwingt sie immer.

---

## 4. Datenfluss und Laufzeitzustand

```
watcher → worker.submit → queue(pending)
        → worker: mark_analyzing
        → extract → analyze → suggest
        → queue.set_ready(+suggestion)            [oder: ExtractionError → error/ + queue.error]
UI-Listen pollen /partials/* (~2 s) und zeigen die Übergänge live.
User öffnet /review/{id} (nur ready) → korrigiert Felder → confirm
        → [Summary, falls verlangt/Konflikt] → execute
        → processor: Copy an Zielordner + Original-Handling
        → queue.remove → transiente Erfolgsmeldung (Toast)
```

- **Zustandsarm** (MVP-Spec §4.2): Pending-Dokumente und Analyseergebnisse leben rein in-memory im
  `queue`-Register (Ergebnis-Caching = `QueueEntry.suggestion`). Keine Historie auf Platte.
- **Laufzeit-Konfigänderung:** Eine über `/config` gespeicherte Config gilt für **künftig**
  hinzukommende Dokumente (der Worker liest `config_provider()` zum Analysezeitpunkt). Bereits
  `ready`-Einträge behalten ihren gecachten `suggestion` und werden **nicht** neu bewertet
  (ui.md). Eine Neubewertung erfolgt nur, wenn die Datei erneut in den überwachten Ordner gelegt wird.
- **Bewusste MVP-Grenze:** Änderungen an Pfaden (`watchfolder`/`error_folder`/`processed_folder`)
  greifen erst nach einem Neustart (der Watcher wird zur Laufzeit nicht neu verdrahtet). Alle übrigen
  Config-Felder (Regeln, Pattern, `summary_mode`, `original_handling`, Zielordner) wirken sofort für
  neue Dokumente. Dies wird so dokumentiert.

---

## 5. Fehlerbehandlung (MVP-Spec §6)

| Fehlerart | Behandlung |
|---|---|
| Unlesbares/textloses PDF (inkl. reiner Scan) | Worker: Datei → `error/`, Queue-Eintrag `error` mit Kurzgrund. Nur die Datei in `error/` persistiert. |
| Technischer Laufzeitfehler (Analyse/Copy/Permission) | stdout-Log + transiente UI-Meldung (Toast bzw. `error`-Eintrag). Kein Verlauf. |
| Config-Fehler beim Speichern | Validierungsfehler-Liste in der UI; alte Config bleibt aktiv; Datei unverändert. |

---

## 6. Teststrategie (MVP-Spec §7)

**pytest (uv):**

- `queue` — `id`-Vergabe + Stabilität über Transitionen, Statuswechsel `pending→analyzing→ready`
  (mit `suggestion`-Caching), `get_by_id`, Pfad-Dedup unverändert.
- `config.save_config` — gültig (atomar geschrieben, geparstes Config zurück), ungültig (wirft
  `ConfigError`, **Datei unverändert**), fehlende Pflichtpfade.
- `analyzer` — `snippet`-Erfassung (Inline + Tabelle), `raw` ist Teilzeichenkette von `snippet`,
  Kandidatenmenge unverändert.
- `worker` — `pending→analyzing→ready` mit Fake-Extractor (kein JVM im Unit-Test);
  `ExtractionError` → `error` + Datei nach `error/` verschoben; sonstige Exception → `error` + Log.
- `web/naming.render_filename` — Slug-Regeln, Fallbacks, Extension, Pattern-Rendering.
- `web/routes` (FastAPI `TestClient`) — Seiten rendern; Polling-Fragmente; `confirm` →
  Summary vs. direktes Execute (je `summary_mode`); Konflikt sperrt Ausführung; `config`-Save
  gültig/ungültig.

**Playwright (Skill):**

- Warteschlange zeigt `pending`/`analyzing`, Übergang nach `ready` ohne Reload (Polling).
- Prüfungsansicht rendert **alle** Datumskandidaten als auswählbare Liste (mit Snippet/Label),
  Live-Namensvorschau aktualisiert sich bei Feldänderung, `Bestätigen` erst aktiv bei
  gültigem Datum + ≥1 Zielordner.
- Bestätigen ohne Konflikt/`summary_mode=never` → Ausführung, Eintrag verschwindet, Erfolgs-Toast.
- Konflikt-Pfad → Summary-Modal mit markiertem Ablageort, `Ausführen` gesperrt.
- Konfiguration speichern: gültig → Toast; ungültig → Fehlerliste, alte Config bleibt.

---

## 7. Betroffene Dateien (Überblick, kein Implementierungsplan)

```
backend/src/zilpzalp/
  queue.py        # QueueEntry/Queue erweitern
  analyzer.py     # DateCandidate.snippet
  config.py       # save_config
  worker.py       # NEU
  main.py         # Worker + Web verdrahten
  web/            # NEU
    __init__.py
    routes.py
    naming.py
    templates/    # base, overview, queue, review, config, _partials
    static/       # styles.css, htmx.min.js, app.js
backend/tests/
  test_queue.py, test_config.py, test_analyzer.py   # erweitern
  test_worker.py, test_naming.py, test_routes.py     # NEU
  (Playwright-UI-Tests separat über den Skill)
```

Der konkrete bite-sized TDD-Umsetzungsplan (exakte Pfade, vollständiger Code/Tests je Schritt)
entsteht im Anschluss via `superpowers:writing-plans`.
