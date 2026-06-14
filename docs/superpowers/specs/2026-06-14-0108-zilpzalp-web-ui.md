# ZilpZalp — Web-UI (Meilenstein 5) · Design

Status: zur Umsetzung freigegeben
Datum: 2026-06-14
Verfeinert: [MVP Design-Spec](2026-06-13-1435-zilpzalp-mvp-design.md) §3, §4, §4.3, §5, §6, §7

Dieses Spec verfeinert die Architektur-Referenz für Meilenstein 5 (Web-UI). Es legt fest,
wie die bestehenden Module (`queue`, `extractor`, `analyzer`, `suggestion`, `processor`,
`config`) zu einer bedienbaren Jinja2+HTMX-Oberfläche verbunden werden. Strikt auf den
Roadmap-Scope von M5 begrenzt; mkdocs/Packaging (M6), KI/OCR und Hash-Duplikate bleiben außen vor.

---

## 1. Ausgangslage & Lücke

Nach M4 ruft der `watcher` nur `queue.add(path)` auf (Status `pending`). Die Kette
`extract → analyze → suggest` ist **nirgends verdrahtet**, und `QueueEntry` speichert kein
Analyseergebnis. Die Review-View braucht aber ein `Suggestion`. Design-Spec §4.2 fordert:
„Analyseergebnisse leben rein in-memory im `queue`-Register." Daraus folgt der M5-Zuschnitt:
ein **Hintergrund-Worker** führt die Analyse aus und cacht das Ergebnis im Register; die UI
liest nur gecachte Ergebnisse und löst selbst keine Analyse aus.

---

## 2. Architektur & Datenfluss

```
watcher ─► worker.submit(path) ─► queue.add (pending)
                                  └─► extract ─► analyze ─► suggest
                                        │            └─► Suggestion im QueueEntry (ready)
                                        ├─ ExtractionError ─► Datei → error/, mark_error
                                        └─ sonstiger Fehler ─► stdout-Log, mark_error (transient)

Web-UI (Jinja2+HTMX) liest queue.list()/get_by_id() ─► Review ─► Bestätigung
                                                          └─► processor.process(...)
```

### 2.1 Hintergrund-Worker (`worker.py`, neu)

- **Ein einzelner Worker-Thread.** Der `extractor`-Aufruf startet eine JVM (~1–2 s, blockierend);
  serielle Abarbeitung in einem Thread hält den FastAPI-Event-Loop frei und reicht für ein
  1-Nutzer-Tool. Keine Parallelität, kein Pool (YAGNI).
- **Schnittstelle:** `submit(path)` reiht ein; ein interner Lauf macht pro Job
  `queue.set_analyzing(path)` → `extract` → `analyze` → `suggest` → `queue.set_ready(path, suggestion)`.
- **Fehlerpfade (§6):**
  - `ExtractionError` (kein Text/korrupt/reiner Scan): Datei nach `config.paths.error_folder`
    verschieben, `queue.mark_error(path, grund)`.
  - sonstige Exception: nach `stdout` loggen, `queue.mark_error(path, "interner Fehler …")`
    (transient, Rescan baut neu auf).
- **Testbarkeit:** `run_once()` verarbeitet genau einen Job synchron (kein laufender Thread im
  Unit-Test); der echte JVM-Lauf bleibt dem markierten Integrationszweig vorbehalten.

### 2.2 `queue` — Erweiterung

`QueueEntry` wird erweitert; `Queue` bleibt thread-sicher und pfad-dedupliziert:

```python
QueueStatus = Literal["pending", "analyzing", "ready", "error"]

@dataclass(frozen=True)
class QueueEntry:
    id: str                       # stabiles URL-Token (aus dem Pfad abgeleitet)
    path: Path
    status: QueueStatus = "pending"
    suggestion: Suggestion | None = None   # gesetzt bei status == "ready"
    error_reason: str | None = None
```

- `id` = deterministisches Token aus dem aufgelösten Pfad (z. B. `sha1(str(path))[:12]`), damit
  Review-URLs stabil sind und kein Reverse-Map-Pflegeaufwand entsteht.
- Neue Methoden: `set_analyzing(path)`, `set_ready(path, suggestion)`, `get_by_id(id)`.
- Idempotenz/Dedup über den Pfad bleibt unverändert (§4.2).

### 2.3 `config` — Erweiterung

- Neu: `save_config(path, raw_text) -> Config`. Schreibt `raw_text` in eine Temp-Datei, validiert
  über die bestehende `load_config`-Logik, und ersetzt die Zieldatei nur bei Erfolg atomar
  (`os.replace`). Bei Validierungsfehler wird `ConfigError` geworfen, die Zieldatei bleibt unberührt.
- Kein neues Validierungsregelwerk — dieselben Regeln wie beim Start (§5/§6).

`extractor`, `analyzer`, `suggestion`, `processor` bleiben **unverändert** (reine Funktionen,
Design-Kernregel §3).

---

## 3. Seiten, Routen & Verhalten

Stack: FastAPI + Jinja2 (`web/templates/`), HTMX + CSS vendored unter `web/static/`. Ein
`base.html` definiert die App-Shell (Kopfleiste mit Produktname, aktive Navigation
Übersicht · Warteschlange · Konfiguration, Theme-Umschalter) und ein gemeinsames Design-System
(`style.css`); Seiten erweitern es, Fragmente liefern Teilbereiche für HTMX-Polling.
Server-rendered, kein Build-Step (Design-Spec §1). Look & Feel und Zustände: siehe §3.6.

| Route | Methode | Zweck |
|---|---|---|
| `/` | GET | Dashboard / Startseite (Vollseite) |
| `/dashboard/cards` | GET | Fragment: Status-Kacheln + Queue-Vorschau, HTMX-Poll alle 2 s |
| `/queue` | GET | Warteschlange (Vollseite) |
| `/queue/rows` | GET | Listen-Fragment (`<tbody>`), HTMX-Poll alle 2 s |
| `/review/{id}` | GET | Review-View für einen `ready`-Eintrag |
| `/review/{id}/preview` | POST | Live-Namensvorschau (HTMX-Fragment) |
| `/review/{id}/confirm` | POST | Entscheidet Zusammenfassung vs. direkte Ausführung |
| `/review/{id}/execute` | POST | Endgültige Ausführung aus der Zusammenfassung |
| `/config` | GET | Roh-YAML-Editor |
| `/config` | POST | Validieren + speichern |
| `/health` | GET | bestehend |

### 3.1 Dashboard / Startseite (`/`, Fragment `/dashboard/cards`)

Die Einstiegsseite. Soll dem Tool ein „vollwertiges“ Gesicht geben und auf einen Blick zeigen,
was ansteht. Inhalt:

- **Status-Kacheln** mit den Zählern je `QueueEntry.status` (`bereit` / `Analyse` / `wartet` /
  `Fehler`), berechnet aus `queue.list()`.
- **Betriebsinfo** (read-only Anzeige aus `app.state.config`): Watchfolder-Pfad, Config-Pfad,
  `original_handling`, `summary_mode`, Anzahl Ziele/Regeln/Muster.
- **Queue-Vorschau:** die jüngsten Einträge als kompakte Tabelle mit „Prüfen →“ (bei `ready`) und
  „Alle anzeigen →“ zur Warteschlange.

Die dynamischen Teile (Kacheln + Vorschau) liegen im Fragment `/dashboard/cards` und pollen sich
per HTMX alle 2 s selbst neu. Reine Anzeige des In-Memory-Zustands — kein zusätzlicher
Persistenz-/Statuspfad.

### 3.2 Warteschlange (`/queue`, Fragment `/queue/rows`)

Tabelle aller Einträge: Datei, Status-Badge (`wartet`/`Analyse`/`bereit`/`Fehler`), Vorschau
(bei `ready`: gewähltes Datum · Absender · Typ; bei `error`: `error_reason`), Aktion „Prüfen →“
nur bei `ready`. Das `<tbody>`-Fragment (`/queue/rows`) pollt sich per HTMX alle 2 s selbst neu,
damit `analyzing → ready` ohne Reload erscheint. Transiente Erfolgs-/Fehler-Banner werden oberhalb
der Liste gezeigt; leerer Zustand: „Keine Dokumente in der Warteschlange.“

### 3.3 Review-View (`/review/{id}`)

- **Datum (Kernanforderung §4.3):** alle `suggestion.date_candidates` als Radio-Liste (normalisiert
  · Label · Rohtext), vorausgewählt = `preselected_date_index`. Zusätzlich eine Option „manuell“
  mit Datumseingabe — auch genutzt, wenn die Kandidatenliste leer ist. Die UI entfernt/verdichtet
  **keine** Kandidaten.
- **Felder:** Absender, Typ, Beschreibung (Textfelder, vorbefüllt aus `suggestion`); Muster-Auswahl
  (`config.patterns` + Default); Zielordner als Checkbox-Liste (`config.targets`, vorgewählt aus
  `suggestion.target_paths`).
- **Live-Namensvorschau:** Bei Änderung postet HTMX das Formular an `/review/{id}/preview`; der
  Server rendert den Dateinamen aus gewähltem Datum + Feldern + Muster und gibt das Vorschau-Fragment
  zurück. Rendering serverseitig (kein JS-Templating, kein Build).
- „Bestätigen“ postet an `/review/{id}/confirm`.

### 3.4 Zusammenfassung & Konflikt (`/confirm`, `/execute`)

`/confirm` berechnet finalen Namen + Zielpfade und führt eine **Dry-Run-Konfliktprüfung** aus
(gleiche Vorbedingungen wie `processor.process`: Ziel existiert? bei `move` auch `processed`-Ziel?).

- Zusammenfassung wird gezeigt, wenn `summary_mode == "always"` **oder** ein Konflikt vorliegt
  (deckt `on_conflict` ab). Sonst (`never`/`on_conflict` ohne Konflikt) wird direkt ausgeführt.
- Die Zusammenfassung zeigt Quelle, finalen Namen (editierbar), Ziel-Pfade (Konflikte rot markiert)
  und das Original-Handling. Bei Konflikt ist „Ausführen“ gesperrt, bis der Nutzer den Namen ändert
  oder abbricht. **Kein Auto-Suffix** (§4.1).
- „Ausführen“ postet an `/execute` → `processor.process(...)`. Erfolg: Eintrag aus der Queue
  entfernen, zurück zur Liste mit transientem Erfolgs-Banner. `FileConflictError` (Race): zurück zur
  Zusammenfassung mit Konfliktmarkierung. `ProcessorError`/Laufzeitfehler: stdout-Log + transienter
  Fehler an der Liste (§6).

### 3.5 Konfiguration (`/config`)

GET zeigt den aktuellen `config.yaml`-Rohtext in einer Textarea. POST ruft `save_config`:
bei Erfolg atomar speichern, `app.state.config` neu laden, Erfolgs-Banner. Bei `ConfigError` die
Validierungsmeldungen anzeigen und die alte Config aktiv lassen (§6). Neu hinzukommende Dokumente
nutzen die neue Config; bereits analysierte Einträge bleiben unangetastet (zustandsarm, §4.2).

### 3.6 Look & Feel, Zustände, Theme

Die Oberfläche soll sich wie ein vollwertiges Tool anfühlen, nicht wie Roh-HTML — erreicht allein
über handgeschriebenes `style.css` (kein Build-Step, kein CSS-Framework):

- **App-Shell:** durchgängige Kopfleiste mit Produktname und Navigation (Übersicht · Warteschlange ·
  Konfiguration), aktiver Menüpunkt hervorgehoben; konsistentes Seitenlayout mit zentriertem
  Inhaltsbereich in angenehmer Laptop-Breite.
- **Design-System:** abgestimmte Typografie, Abstände, Farbpalette und Status-Farben; wiederkehrende
  Komponenten als CSS-Klassen — Karten, Tabellen, Buttons (primär/sekundär), Formularfelder,
  Badges, Banner/Toasts.
- **Zustände:** Lade-/Analyse-Indikator (für `analyzing`), leere Zustände, Erfolgs-Toasts,
  transiente Fehler-Banner, deaktivierte Buttons (z. B. „Ausführen“ bei Konflikt). Klare primäre vs.
  sekundäre Aktionen.
- **Theme (hell/dunkel):** Farben über CSS-Variablen; Standard folgt `prefers-color-scheme`. Ein
  Umschalter in der Kopfleiste setzt `data-theme` auf `<html>` und merkt die Wahl in
  `localStorage` (wenige Zeilen Vanilla-JS — die einzige eigene JS-Datei neben HTMX). Keine
  serverseitige Theme-Speicherung.
- **Visuelle Grundrichtung:** ruhiges, modernes Utility — heller/dunkler Hintergrund mit viel
  Weißraum, eine ruhige Akzentfarbe, abgerundete Karten, dezente Schatten.

---

## 4. Startup-Verdrahtung (`main.py`)

`lifespan` erzeugt zusätzlich den Worker und verbindet ihn mit dem Watcher:

```
config = load_config(...)            # bestehend
queue = Queue()                      # bestehend
worker = AnalysisWorker(queue, lambda: app.state.config)   # neu, liest Config dynamisch
watcher = Watcher(config.paths.watchfolder, worker.submit) # Callback statt queue.add
worker.start(); watcher.start()  →  finally: watcher.stop(); worker.stop()
```

Der Worker liest die Config über einen Getter (`lambda: app.state.config`), damit Config-Edits zur
Laufzeit für neue Jobs greifen. Templates/Static werden über `Jinja2Templates` bzw.
`StaticFiles` eingebunden.

---

## 5. Teststrategie (§7)

- **Routen-Tests (pytest + `TestClient`)** gegen einen synchron befüllten `Queue`:
  Dashboard-Render (Status-Zähler + Betriebsinfo + Vorschau-Fragment), Warteschlangen-Render
  (alle vier Status), Review-Render **mit mehreren Datumskandidaten** (§4.3: alle sichtbar,
  Vorauswahl korrekt), Preview-Fragment, `confirm` → Zusammenfassung bei Konflikt vs. direkte
  Ausführung, `execute` happy path, Config-Save-Fehlerpfad (alte Config bleibt aktiv).
- **Worker-Tests:** `run_once()` synchron — Erfolgspfad (Suggestion gecacht, Status `ready`),
  `ExtractionError` (Datei nach `error/`, Status `error`) mit Hand-Fixtures/Fakes statt echter JVM.
- **Playwright (Skill):** End-to-End-Klickpfad Dashboard → Warteschlange → Prüfen → Datum wählen →
  Bestätigen → Ausführen → Eintrag verschwindet; Theme-Umschalter wechselt hell/dunkel; plus
  transiente Fehleranzeige.
- **Datensparsamkeit:** kein zusätzlicher Persistenzpfad außer Config + Zieldateien (§7).

---

## 6. `docs/ui.md` (Liefergegenstand)

Eine einzige, rein sprachliche Beschreibung der Oberfläche (Design-Spec §8) in
[`docs/ui.md`](../../ui.md): was der Nutzer sieht, welche Funktionen es gibt und wie die Seiten
zusammenhängen — ohne HTML/Technikdetails. Inhaltlich abgedeckt: Erscheinungsbild & Theme,
wiederkehrende Elemente (Status, Aktualisierung, Meldungen, Bestätigungsprinzip), die Bereiche
Übersicht, Warteschlange, Prüfungsansicht (inkl. Datumsliste §4.3), Zusammenfassung/Konflikt und
Konfiguration sowie die Wege zwischen den Seiten. Wird mit der Implementierung aktuell gehalten.

---

## 7. Scope-Ausschlüsse (M5)

- Keine mkdocs-Endnutzerdoku, kein Docker/Packaging (M6).
- Keine strukturierten Config-Formulare (bewusst Roh-YAML).
- Kein serverseitiger Entwurf-Speicher; In-Bearbeitung-Korrekturen leben im Request (§4.2).
- Keine KI/OCR, keine Hash-Duplikate, kein Login (Design-Spec §1, §10).
