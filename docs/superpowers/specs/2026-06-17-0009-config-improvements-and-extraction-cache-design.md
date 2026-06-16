# Design: Pfade via Env, config.yaml-Verbesserungen, Skip/Disposal & persistenter Extraktions-Cache

## Problem

Mehrere zusammenhängende Schwachstellen rund um Konfiguration und Dokumenten-Fluss:

1. **Container ohne Config startet nicht.** `Dockerfile.backend` setzt
   `ZILPZALP_CONFIG=/config/config.yaml`, backt aber keine Datei ein. Ein blankes
   Image stürzt beim Start in `load_config` ab.
2. **Pfade sind doppelt und an der falschen Stelle.** `watchfolder`/`error_folder`/
   `processed_folder` stehen in der config.yaml *und* werden über Volume-Mounts in
   `docker-compose.yml` gespiegelt. Pfade sind Deployment-Belange, keine Domäne.
3. **Pattern-Schema ist redundant und kollisionsanfällig.** `patterns` ist eine
   Liste mit `name`-Feld, `default_pattern` dupliziert einen rohen Template-String.
4. **Frischer Start ist funktional „tot".** Ohne definiertes Target kann nichts
   abgelegt werden.
5. **`original_handling` ist unklar und unvollständig.** `move`/`processed` erzeugt
   eine redundante Zweitkopie neben dem Target, `keep` lässt Originale in der Inbox
   liegen (die dann nie automatisch verschwinden), und es gibt keinen UI-Weg, ein
   Dokument unabgelegt aus der Inbox zu entfernen. Zudem behalten bereits
   analysierte Einträge ihren mit der alten Config berechneten Vorschlag.

## Leitidee: Infrastruktur ↔ Domäne trennen, Entsorgung vereinheitlichen

- **Infrastruktur-Pfade kommen aus Env** (`ZILPZALP_PATH_*`, mit Defaults). Die App
  legt sie beim Start an.
- **Domänen-Config bleibt in der config.yaml** (original_handling, summary_mode,
  patterns, default_pattern, date_format, date_patterns, rules, targets). Eine
  minimale Datei wird per Entrypoint geseedet und ist in der UI sichtbar/editierbar.
- **Ein Original verlässt die Inbox auf genau zwei Wegen** — Ablegen oder Skip — und
  in beiden Fällen entscheidet **dieselbe** Policy `original_handling`, was mit dem
  Original passiert. Die Inbox leert sich dadurch immer automatisch.

## 1. Pfade über `ZILPZALP_PATH_*`

| Variable | Default | Zweck |
|---|---|---|
| `ZILPZALP_PATH_INBOX` | `/data/inbox` | Watchfolder |
| `ZILPZALP_PATH_ERROR` | `/data/error` | unlesbare/fehlerhafte PDFs |
| `ZILPZALP_PATH_TRASH` | `/data/trash` | entsorgte Originale (Modus `trash`) |
| `ZILPZALP_PATH_CACHE` | `/data/cache` | Extraktions-Cache (Teil 5) |
| `ZILPZALP_PATH_OUTBOX` | `/data/outbox` | Default-Target (Teil 3) |
| `ZILPZALP_CONFIG` | `/config/config.yaml` | Pfad der Domänen-Config |

Änderungen in `backend/src/zilpzalp/config.py`:

- `Paths` (watchfolder, error_folder, trash, cache) wird **aus Env** gebaut
  (`load_paths() -> Paths`), nicht mehr aus der YAML.
- `Config` behält das Feld `paths: Paths`, aber `load_config`/`save_config`
  entfernen ein etwaiges `paths:` aus den YAML-Daten und **injizieren** die
  env-basierten Pfade. Downstream (`processor`, `worker`, `watcher`, `routes`)
  bleibt unverändert, weil `config.paths.X` weiter funktioniert.
- Der bisherige `_check_paths_exist`-Validator entfällt; die App legt die
  Verzeichnisse beim Start an (`mkdir(parents=True, exist_ok=True)` für inbox,
  error, trash, cache und das Outbox-Target).

## 2. Pattern-Schema: Liste → Map

```yaml
# vorher
default_pattern: "{date}__{sender}_{doctype}_{description}"
patterns:
  - name: standard
    template: "{date}__{sender}_{doctype}_{description}"
# nachher
patterns:
  standard:
    template: "{date}__{sender}_{doctype}_{description}"
default_pattern: standard
```

- `patterns: dict[str, Pattern]`, `Pattern = { template: str }` (kein `name`-Feld).
- `default_pattern: str` ist ein **Schlüssel-Verweis**.
- Validierung: `patterns` nicht leer **und** `default_pattern` muss vorhandener
  Schlüssel sein — sonst `ConfigError`. Platzhalter-Check über `patterns.items()`.
- Lookups → Dict-Zugriff (Fallback `patterns[default_pattern].template`) in
  `suggestion.py` (`_resolve_pattern`) und `web/routes.py` (`_resolve_template`).
- `rules[].apply.pattern: standard` bleibt Name-Verweis.

Mitziehen: `backend/config.example.yaml`, `backend/config.default.yaml`, mkdocs-Doku.

## 3. Default-Target „Outbox"

Definiert die config.yaml eigene `targets`, gewinnen diese. Fehlen sie,
synthetisiert `load_config`/`save_config` **ein** Default-Target:

```python
Target(name="Outbox", path=<ZILPZALP_PATH_OUTBOX>, default=True)
```

Das Outbox-Verzeichnis wird beim Start angelegt. Ein frisch gestarteter Container
ist sofort benutzbar (inbox → outbox). Der Name ist über eigene `targets`
überschreibbar.

## 4. Einheitliches `original_handling` & Skip-Button

`original_handling: delete | trash` (Default **`delete`**) — gilt für **beide**
Wege, auf denen ein Original die Inbox verlässt:

| | `delete` | `trash` |
|---|---|---|
| **Ablegen** (confirm/execute) | Kopie → Target, Original gelöscht | Kopie → Target, Original → `/data/trash` |
| **Skip** | Original gelöscht | Original → `/data/trash` |

In beiden Modi leert sich die Inbox automatisch. `trash` dient zugleich als
Roh-Original-Archiv (Abgelegtes) und Papierkorb (Übersprungenes); `delete` ist der
schlanke Modus (Outbox ist das einzige Archiv). `move`/`processed` und `keep`
entfallen.

**Processor** (`backend/src/zilpzalp/processor.py`):

- `_dispose(source, config)` — gemeinsamer Helfer: `delete` → `source.unlink()`;
  `trash` → nach `paths.trash` verschieben, mit eindeutigem Namen bei Kollision
  (analog `_unique_pdf_name`).
- `process(source, filename, targets, config)` — kopiert wie bisher in alle Targets
  (Konflikt-Checks vorab), dann `_dispose(source, config)`. `ProcessResult.
  original_action` ∈ `{"deleted", "trashed"}`.
- `skip(source, config)` — nur `_dispose(source, config)`, ohne Kopie.

**Skip-Route** `POST /documents/{entry_id}/skip` in `web/routes.py`:

- Entry per `queue.get_by_id`; fehlt → HX-Redirect `/queue`.
- `processor.skip(entry.path, config)` + `queue.remove(entry.path)` +
  `cache.remove(entry.path)` (Teil 5).
- Toast „… übersprungen", HX-Redirect `/queue`.

**UI** — Skip-Button für **alle** Stati (pending, analyzing, ready, error) in
`_queue_list.html` (jede Zeile) und `review.html`. Bestätigungsdialog
(`hx-confirm`) **nur im `delete`-Modus** (permanent); im `trash`-Modus sofort
(wiederherstellbar).

**i18n** — `action.skip`, `confirm.skip`, `toast.skipped`; `original.delete` /
`original.trash` ersetzen `original.move` / `original.delete` / `original.keep`.

**Race (analyzing):** tolerierbar — `queue.remove` macht spätere
`set_ready`/`mark_error` zu No-ops, das Entsorgen ist idempotent genug
(`unlink(missing_ok=True)` bzw. Move ins Trash schlägt bei fehlender Quelle
geräuschlos fehl und wird im Skip-Pfad abgefangen).

## 5. Persistenter Extraktions-Cache, Live-Reload & Re-Analyse

### Ausgangslage

Heute schreibt `extract()` das ODL-JSON in ein `TemporaryDirectory`, parst es zu
`Document` und löscht es. `config_save` setzt bereits `app.state.config` live, und
der Worker liest die Config pro Job frisch — künftig analysierte Dokumente nutzen
sofort die neue Config. Lücke: bereits `ready`-Einträge behalten ihren alten
Vorschlag.

### Cache-Modul (`backend/src/zilpzalp/cache.py`)

Verzeichnis aus `ZILPZALP_PATH_CACHE`, beim Start angelegt. `DocumentCache`:

- Schlüssel = PDF-Dateiname (im Watchfolder eindeutig).
- Pro Dokument `<stem>.json` + `<stem>.md`.
- `load_document(path) -> Document | None` — liest `<stem>.json`, parst via
  `document_from_odl`; `None` ohne Datei.
- `remove(path)` — löscht beide Dateien (idempotent).
- `prune(valid_names)` — entfernt Cache-Dateien ohne zugehöriges Inbox-PDF.

Liegt auf `app.state.cache`, geteilt von Worker und Routes.

### Extractor

`extract(pdf_path, cache_dir) -> Document`:

- `opendataloader_pdf.convert(format=["json", "markdown"], output_dir=tmp)` (ein
  JVM-Lauf, beide Formate).
- Ausgaben deterministisch nach `cache/<stem>.json` und `cache/<stem>.md`
  verschieben; JSON zu `Document` parsen.

Persistentes Schreiben ersetzt das bisherige „Temp löschen" — bewusste Umkehr der
„kein Text auf Platte"-Entscheidung, Voraussetzung für die spätere Preview.

### Worker (`worker.py`)

Zwei Job-Typen:

- **`submit`** (neuer Watcher-/Scan-Fund): **immer** `extract(...)` → Cache
  überschrieben. Löst die Stale-Frage beim Start (Re-Scan extrahiert frisch).
- **`reanalyze`** (nach Config-Save): `cache.load_document(path)`; wenn vorhanden,
  `extract` überspringen, nur `analyze` + `suggest` mit frischer Config
  (≈ instantan). Fehlt der Cache, Fallback auf `extract`.

`reanalyze_all()`: re-queued alle Einträge mit vorhandenem Cache-JSON. Kein
`document`-Feld am `QueueEntry` — der Disk-Cache ist die Persistenz.

### Live-Reload in `config_save`

Nach erfolgreichem Speichern (`app.state.config` gesetzt) → `worker.reanalyze_all()`.
Ein Watcher-Neustart bei Pfadwechsel ist nicht mehr nötig: Pfade kommen aus Env.

### Lifecycle

- Erfolgreiches Ablegen (`_execute`) → `cache.remove(entry.path)`.
- Skip (Teil 4) → `cache.remove(entry.path)`.
- Extraktionsfehler → evtl. Teilausgaben aufräumen.
- Beim Start → `cache.prune` verwaister Dateien.

## 6. Demo & Deployment

### Entrypoint-Seeding der Config

Die Default-Config wird nach `/app/backend/config.default.yaml` eingebacken (nicht
direkt nach `/config`). Ein Entrypoint-Script prüft beim Start: existiert
`$ZILPZALP_CONFIG` nicht, kopiert es die Default-Datei dorthin (Parent-Dir anlegen),
dann `exec uvicorn …`.

Damit funktionieren alle Mount-Fälle: ein leeres **persistentes Volume auf
`/config`** wird beim ersten Start befüllt und UI-Änderungen persistieren; kein
Mount → Container-Layer; Named Volume → wird geseedet.

`Dockerfile.backend`: `COPY backend/config.default.yaml
/app/backend/config.default.yaml`, `COPY` + `ENTRYPOINT` des Scripts; `CMD` bleibt
`uvicorn …` (das Script `exec "$@"`). `config.default.yaml` enthält nur
Domänen-Werte:

```yaml
original_handling: delete
summary_mode: on_conflict
default_pattern: standard
date_format: "%Y-%m-%d"
patterns:
  standard:
    template: "{date}__{sender}_{doctype}_{description}"
```

### Demo-Bereinigung

- `demo/config/` löschen (Config wird geseedet).
- `demo/targets/` löschen (ersetzt durch Outbox-Default unter `/data/outbox`).
- `docker-compose.yml`: das `backend`-Volume-Set auf `- ./demo/data:/data`
  reduzieren; den `ZILPZALP_CONFIG`-Override entfernen.
- `demo/data/inbox/beispiel-rechnung.pdf` bleibt als Demo-PDF; übrige Unterordner
  legt die App beim Start an.
- `.gitignore` straffen (targets-Einträge raus; trash/outbox/cache als generiert
  ignorieren).

## Bekannte Akzeptanzen

- Eine offene Review-Seite pollt nicht; ihr Vorschlag kann bis zur Navigation
  veraltet sein, wenn der Eintrag im Hintergrund neu analysiert wurde.
- `/data/trash` wächst im `trash`-Modus, bis es manuell geleert wird (kein „Trash
  leeren" in der UI — Ausblick).

## Testing

- `test_config.py`: env-basierte `Paths` (Defaults + Overrides); `paths:` in der
  YAML wird ignoriert; Map-Schema; leeres `patterns` / unbekannter
  `default_pattern` → `ConfigError`; Outbox-Default-Synthese ohne targets.
- `test_processor.py`: `delete` löscht das Original; `trash` verschiebt es (mit
  eindeutigem Namen bei Kollision); `skip` entsorgt ohne Kopie; Inbox ist danach
  leer.
- `test_cache.py`: `load_document`/`remove`/`prune`; ohne Datei → `None`.
- `test_extractor.py`: `extract` schreibt `<stem>.json` + `<stem>.md` und parst das
  `Document` (Signatur `cache_dir`).
- `test_worker.py`: `submit` extrahiert immer; `reanalyze` überspringt `extract`;
  `reanalyze_all` nur für gecachte Einträge.
- `test_routes.py`: `/skip` entsorgt Datei + Eintrag + Cache je Modus; fehlender
  Entry → Redirect; `config_save` triggert Re-Analyse ohne erneute Extraktion.
- Bestehende Tests aufs neue Pattern-/Pfad-/Disposal-Modell anpassen.

## i18n und Dokumentation

- **i18n** — `action.skip`, `confirm.skip`, `toast.skipped`, `original.delete`,
  `original.trash` (de/en).
- **Docs** — mkdocs: `patterns`-Map-Schema, `ZILPZALP_PATH_*`-Variablen,
  Outbox-Default, `original_handling: delete|trash`; Hinweis, dass UI-Änderungen
  ohne Neustart wirken und wie man Config über ein `/config`-Volume persistiert.

## Out of scope (YAGNI)

Als Ideen ins [Backlog](../../backlog.md) aufgenommen:

- **Extrahierte Inhalte in der Review-Preview anzeigen** (json + markdown) — das
  Cache-Fundament liegt mit diesem Spec.
- **„Trash leeren"-Aktion in der UI** für den `trash`-Modus.
- **Cache-Wiederverwendung über Neustart** (extract überspringen, Invalidierung
  über Dateigröße + mtime).
- **Manueller Re-Analyse-Button** als Ergänzung zur automatischen Re-Analyse.

Kein Migrationslayer für das alte Listen-/Pfad-/`original_handling`-Schema:
Breaking Change, Beispiele und Doku werden mitgezogen.
