# Design: config.yaml-Verbesserungen, Inbox-Löschen & persistenter Extraktions-Cache

## Problem

Drei zusammenhängende Schwachstellen rund um `config.yaml` und den Dokumenten-Fluss:

1. **Container ohne Config startet nicht.** `Dockerfile.backend` setzt
   `ZILPZALP_CONFIG=/config/config.yaml`, backt aber keine Datei ein.
   `docker run zilpzalp-backend` ohne Volume-Mount stürzt beim Start in
   `load_config` ab.
2. **Pattern-Schema ist redundant und kollisionsanfällig.** `patterns` ist eine
   Liste mit `name`-Feld, `default_pattern` dupliziert einen rohen Template-String.
   Doppelte Namen sind möglich, und der Default verweist nicht auf ein benanntes
   Pattern.
3. **Config-Änderungen über die UI wirken nur teilweise ohne Neustart**, und
   `original_handling: keep` lässt Originale im Watchfolder liegen, ohne dass man
   sie über die UI wieder loswird. Außerdem behalten bereits analysierte Einträge
   ihren mit der alten Config berechneten Vorschlag.

## Ziele

- Ein blankes Backend-Image startet eigenständig (minimale eingebackene Config).
- `patterns` als Map mit dem Namen als Schlüssel; `default_pattern` verweist auf
  einen Schlüssel; strikte Validierung.
- Inbox-Dateien lassen sich über die UI hart löschen (Gegenstück zu `keep`).
- Config-Änderungen über die UI wirken **ohne Container-Neustart** — inklusive
  automatischer Re-Analyse aller offenen Dokumente.
- Ein persistenter Extraktions-Cache (json + markdown pro Dokument) macht die
  Re-Analyse billig und legt das Fundament für eine spätere Preview-Anzeige.

## 1. Minimale Config im Container

Neue Datei **`backend/config.default.yaml`** — minimal und gültig gegen die im
Image angelegten Ordner, bewusst **ohne** `targets`/`rules`/`date_patterns`:

```yaml
paths:
  watchfolder: /data/inbox
  error_folder: /data/error
  processed_folder: /data/processed
original_handling: move
summary_mode: on_conflict
default_pattern: standard
date_format: "%Y-%m-%d"
patterns:
  standard:
    template: "{date}__{sender}_{doctype}_{description}"
```

Sie ist getrennt von `backend/config.example.yaml` (reiche Editier-Vorlage mit
targets + rules für lokale Läufe). Ohne Target kann noch nichts abgelegt werden —
der User legt sein erstes Target per UI an. Das ist der bewusst minimale Erststart.

`Dockerfile.backend` (runtime-Stage):

- `mkdir -p /data/inbox /data/error /data/processed /data/cache`
- `COPY backend/config.default.yaml /config/config.yaml`

Ein Bind-Mount (`docker-compose.yml`: `./demo/config:/config`) überschreibt die
eingebackene Datei weiterhin — das Demo-Verhalten bleibt unverändert.

## 2. Pattern-Schema: Liste → Map

**Vorher:**

```yaml
default_pattern: "{date}__{sender}_{doctype}_{description}"
patterns:
  - name: standard
    template: "{date}__{sender}_{doctype}_{description}"
```

**Nachher:**

```yaml
patterns:
  standard:
    template: "{date}__{sender}_{doctype}_{description}"
default_pattern: standard
```

Änderungen in `backend/src/zilpzalp/config.py`:

- `patterns: dict[str, Pattern]`, `Pattern` = `{ template: str }` (das `name`-Feld
  entfällt — der Schlüssel ist der Name).
- `default_pattern: str` ist jetzt ein **Schlüssel-Verweis**, kein Template.
- Neue Validierung (`model_validator`, `mode="after"`): `patterns` darf nicht leer
  sein **und** `default_pattern` muss ein vorhandener Schlüssel sein — sonst
  `ConfigError`.
- Der Platzhalter-Check iteriert über `patterns.items()` statt über die Liste.

Lookups vereinfachen sich zu Dict-Zugriff (Fallback `patterns[default_pattern].template`):

- `_resolve_pattern` in `backend/src/zilpzalp/suggestion.py`
- `_resolve_template` in `backend/src/zilpzalp/web/routes.py`

`rules[].apply.pattern: standard` bleibt unverändert — referenziert weiter per Name
(= Schlüssel).

Mitziehen: `backend/config.example.yaml`, `demo/config/config.yaml`,
`backend/config.default.yaml`, mkdocs-Doku.

## 3. Inbox-Löschen-Button

`original_handling: keep` bleibt erhalten; der Lösch-Button ist sein Gegenstück
(kept-Originale lassen sich so loswerden).

**Route** `POST /documents/{entry_id}/delete` in `backend/src/zilpzalp/web/routes.py`:

- Entry per `queue.get_by_id` holen; fehlt er → HX-Redirect `/queue`.
- `entry.path.unlink(missing_ok=True)` + `queue.remove(entry.path)` +
  `cache.remove(entry.path)` (siehe Teil 4).
- Toast „… wurde gelöscht", HX-Redirect auf `/queue`.

**UI** — Lösch-Button für **alle** Stati (pending, analyzing, ready, error):

- in `_queue_list.html` (jede Zeile) und auf `review.html`,
- mit nativem `hx-confirm` (Bestätigungsdialog) und `hx-post`.

**i18n** — neue Keys `action.delete`, `confirm.delete` (Dialogtext),
`toast.deleted` in `de.json` / `en.json`.

**Race (analyzing):** Datei-Delete während laufender Analyse ist tolerierbar —
`queue.remove` macht spätere `set_ready`/`mark_error` zu No-ops,
`unlink(missing_ok=True)` ist idempotent. Bewusste Akzeptanz.

## 4. Persistenter Extraktions-Cache, Live-Reload & Re-Analyse

### Ausgangslage

Heute schreibt `extract()` ([extractor.py](../../../backend/src/zilpzalp/extractor.py))
das ODL-JSON in ein `TemporaryDirectory`, parst es zu `Document` und **löscht** das
Verzeichnis wieder („kein Volltext bleibt auf Platte"). Die Analyse nutzt
ausschließlich das JSON; Markdown ist rein für menschliches Lesen relevant.

`config_save` ([routes.py](../../../backend/src/zilpzalp/web/routes.py)) setzt
bereits `app.state.config` live neu, und der Worker liest die Config pro Job frisch
(`lambda: app.state.config`). Damit nutzen **künftig analysierte** Dokumente sofort
die neue Config. Zwei Lücken: bereits `ready`-Einträge behalten ihren alten
Vorschlag, und ein geänderter `paths.watchfolder` wird vom Watcher erst nach
Neustart übernommen.

### Cache-Modul (`backend/src/zilpzalp/cache.py`)

App-verwaltetes Verzeichnis, **nicht** in der user-config. Pfad aus Env
`ZILPZALP_CACHE` (Default `/data/cache`), beim Start per
`mkdir(parents=True, exist_ok=True)` angelegt.

`DocumentCache` über einem Basisverzeichnis:

- Schlüssel = PDF-Dateiname (im Watchfolder eindeutig; Upload und Processor
  verhindern Namenskollisionen).
- Pro Dokument zwei Dateien: `<stem>.json` und `<stem>.md`.
- `load_document(path) -> Document | None` — liest `<stem>.json` und parst via
  `document_from_odl`; `None`, wenn keine Datei existiert.
- `remove(path)` — löscht beide Dateien (idempotent).
- `prune(valid_names)` — entfernt Cache-Dateien ohne zugehöriges Inbox-PDF.

Instanz liegt auf `app.state.cache` und wird vom Worker (Konstruktor) und von den
Routes gemeinsam genutzt.

### Extractor

`extract(pdf_path, cache_dir) -> Document`:

- `opendataloader_pdf.convert(format=["json", "markdown"], output_dir=tmp)` (ein
  JVM-Lauf erzeugt beide Formate).
- Die beiden Ausgaben deterministisch nach `cache/<stem>.json` und
  `cache/<stem>.md` verschieben (unabhängig von ODLs interner Benennung).
- Das JSON zu `Document` parsen und zurückgeben.

Damit ersetzt persistentes Schreiben das bisherige „Temp löschen" — eine bewusste
Umkehr der heutigen „kein Text auf Platte"-Entscheidung, vertretbar für ein
selbst-gehostetes Einzelnutzer-Tool und Voraussetzung für die spätere Preview.

### Worker (`backend/src/zilpzalp/worker.py`)

Zwei Job-Typen auf der internen Work-Queue:

- **`submit`** (neuer Watcher-/Scan-Fund): **immer** `extract(...)` → Cache wird
  überschrieben. Das löst die Stale-Frage beim Start: der Re-Scan extrahiert jedes
  Inbox-PDF frisch.
- **`reanalyze`** (nach Config-Save): `cache.load_document(path)` lesen; wenn
  vorhanden, `extract` überspringen und nur `analyze` + `suggest` mit frischer
  Config ausführen (≈ instantan). Fehlt der Cache, fällt der Job auf `extract`
  zurück.

`reanalyze_all()`: re-queued alle Einträge, für die ein Cache-JSON existiert
(definitionsgemäß die erfolgreich extrahierten / `ready`-Einträge). Ins error/
verschobene Fehl-Dokumente haben kein Inbox-File und keinen Cache → werden nicht
angefasst.

Das früher erwogene `document`-Feld am `QueueEntry` entfällt — der Disk-Cache ist
die Persistenz.

### Live-Reload in `config_save`

Nach erfolgreichem Speichern (`app.state.config` gesetzt):

1. Hat sich `paths.watchfolder` geändert (alte vs. neue Config vergleichen, bevor
   `app.state.config` überschrieben wird): Watcher stoppen, mit neuem Pfad neu
   aufsetzen und starten (inkl. Re-Scan).
2. `worker.reanalyze_all()` aufrufen.

Die Queue-Liste pollt ohnehin alle 2 s und zeigt währenddessen `analyzing`.

### Lifecycle

- Erfolgreiches Ablegen (`_execute`) → `cache.remove(entry.path)`.
- Inbox-Löschen (Teil 3) → `cache.remove(entry.path)`.
- Extraktionsfehler → evtl. Teilausgaben aufräumen.
- Beim Start → `cache.prune` verwaister Dateien.

## Bekannte Akzeptanzen

- Eine offene Review-Seite pollt nicht; ihr Vorschlag kann bis zur Navigation
  veraltet sein, wenn der Eintrag im Hintergrund neu analysiert wurde.
- Nach einem `watchfolder`-Wechsel bleiben alte Pending-Einträge mit alten Pfaden
  in der Queue (im Container praktisch irrelevant, da der Pfad durch Volume-Mounts
  fix ist).

## Testing

- `test_config.py`: Map-Schema lädt; leeres `patterns` und unbekannter
  `default_pattern` → `ConfigError`; Platzhalter-Check über die Map.
- `test_cache.py`: `load_document`/`remove`/`prune`; `load_document` ohne Datei →
  `None`.
- `test_extractor.py`: `extract` schreibt `<stem>.json` + `<stem>.md` in den Cache
  und parst das `Document` (bestehende Tests an die `cache_dir`-Signatur anpassen).
- `test_worker.py`: `submit` extrahiert immer; `reanalyze` überspringt `extract`
  bei vorhandenem Cache; `reanalyze_all` betrifft nur gecachte Einträge.
- `test_routes.py`: `/delete` entfernt Datei + Eintrag + Cache; fehlender Entry →
  Redirect; `config_save` triggert Re-Analyse ohne erneute Extraktion und startet
  den Watcher bei geändertem `watchfolder` neu.
- Bestehende Tests aufs neue Pattern-Schema anpassen.

## i18n und Dokumentation

- **i18n** — `action.delete`, `confirm.delete`, `toast.deleted` (de/en).
- **Docs** — mkdocs-Konfigurationsseite auf das neue `patterns`-Map-Schema
  aktualisieren; kurzer Hinweis, dass UI-Config-Änderungen ohne Neustart wirken.

## Out of scope (YAGNI)

Als Ideen ins [Backlog](../../backlog.md) aufgenommen:

- **Extrahierte Inhalte in der Review-Preview anzeigen** (json + markdown) — das
  persistierte Cache-Fundament liegt mit diesem Spec; die Anzeige ist ein eigenes
  Folge-Spec.
- **Papierkorb/Wiederherstellung beim Inbox-Löschen** statt hartem Löschen.
- **Cache-Wiederverwendung über Neustart** (extract überspringen, Invalidierung
  über Dateigröße + mtime).
- **Manueller Re-Analyse-Button** (global / pro Eintrag) als Ergänzung zur
  automatischen Re-Analyse.

Kein Migrationslayer für das alte Listen-Schema: Breaking Change, Beispiele und
Doku werden mitgezogen.
