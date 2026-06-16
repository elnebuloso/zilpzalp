# Design: Pfade via Env, config.yaml-Verbesserungen, Inbox-Löschen & persistenter Extraktions-Cache

## Problem

Mehrere zusammenhängende Schwachstellen rund um Konfiguration und Dokumenten-Fluss:

1. **Container ohne Config startet nicht.** `Dockerfile.backend` setzt
   `ZILPZALP_CONFIG=/config/config.yaml`, backt aber keine Datei ein. Ein blankes
   Image stürzt beim Start in `load_config` ab.
2. **Pfade sind doppelt und an der falschen Stelle.** `watchfolder`/`error_folder`/
   `processed_folder` stehen in der config.yaml *und* werden über Volume-Mounts in
   `docker-compose.yml` gespiegelt — dieselbe Info an zwei Orten. Pfade sind
   Deployment-/Infrastruktur-Belange, keine Domänen-Config.
3. **Pattern-Schema ist redundant und kollisionsanfällig.** `patterns` ist eine
   Liste mit `name`-Feld, `default_pattern` dupliziert einen rohen Template-String.
4. **Frischer Start ist funktional „tot".** Ohne definiertes Target kann nichts
   abgelegt werden.
5. **`original_handling: keep`** lässt Originale im Watchfolder liegen, ohne dass
   man sie über die UI loswird; bereits analysierte Einträge behalten ihren mit der
   alten Config berechneten Vorschlag, und UI-Config-Änderungen wirken nur teilweise
   ohne Neustart.

## Leitidee: Infrastruktur ↔ Domäne trennen

- **Infrastruktur-Pfade kommen aus Env** (`ZILPZALP_PATH_*`, mit Defaults). Sie
  gehören zum Deployment und sind an die Volume-Mounts gebunden (12-Factor). Die
  App legt sie beim Start an.
- **Domänen-Config bleibt in der config.yaml** (original_handling, summary_mode,
  patterns, default_pattern, date_format, date_patterns, rules, targets) — das, was
  der User über die UI sinnvoll editiert. Eine minimale Datei wird eingebacken und
  ist in der UI sichtbar/überschreibbar.

## 1. Pfade über `ZILPZALP_PATH_*`

Neue Env-Variablen mit Defaults:

| Variable | Default | Zweck |
|---|---|---|
| `ZILPZALP_PATH_INBOX` | `/data/inbox` | Watchfolder |
| `ZILPZALP_PATH_ERROR` | `/data/error` | unlesbare/fehlerhafte PDFs |
| `ZILPZALP_PATH_PROCESSED` | `/data/processed` | Originale nach `move` |
| `ZILPZALP_PATH_CACHE` | `/data/cache` | Extraktions-Cache (Teil 4) |
| `ZILPZALP_PATH_OUTBOX` | `/data/outbox` | Default-Target (Teil 4 unten) |
| `ZILPZALP_CONFIG` | `/config/config.yaml` | Pfad der Domänen-Config (unverändert) |

Änderungen in `backend/src/zilpzalp/config.py`:

- `Paths` (watchfolder, error_folder, processed_folder, cache) wird **aus Env**
  gebaut (`load_paths() -> Paths`), nicht mehr aus der YAML.
- `Config` behält das Feld `paths: Paths`, aber `load_config`/`save_config`
  entfernen ein etwaiges `paths:` aus den YAML-Daten und **injizieren** die
  env-basierten Pfade. Downstream (`processor`, `worker`, `watcher`, `routes`)
  bleibt unverändert, weil `config.paths.X` weiter funktioniert — nur die Quelle
  ändert sich.
- Der bisherige `_check_paths_exist`-Validator entfällt; stattdessen legt die App
  die Verzeichnisse beim Start an (`mkdir(parents=True, exist_ok=True)` für inbox,
  error, processed, cache und das Outbox-Target).

Damit löst sich Problem 1 (Container startet mit Defaults) und 2 (eine Quelle für
Pfade, keine Doppelung).

## 2. Pattern-Schema: Liste → Map

**Vorher** → **Nachher:**

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

- `patterns: dict[str, Pattern]`, `Pattern = { template: str }` (kein `name`-Feld —
  der Schlüssel ist der Name).
- `default_pattern: str` ist ein **Schlüssel-Verweis**, kein Template.
- Validierung (`model_validator`): `patterns` nicht leer **und** `default_pattern`
  muss vorhandener Schlüssel sein — sonst `ConfigError`. Platzhalter-Check über
  `patterns.items()`.
- Lookups → Dict-Zugriff (Fallback `patterns[default_pattern].template`) in
  `suggestion.py` (`_resolve_pattern`) und `web/routes.py` (`_resolve_template`).
- `rules[].apply.pattern: standard` bleibt Name-Verweis (= Schlüssel).

Mitziehen: `backend/config.example.yaml`, `backend/config.default.yaml`, mkdocs-Doku.

## 3. Default-Target „Outbox"

Definiert die config.yaml eigene `targets`, gewinnen diese. Fehlen sie,
synthetisiert `load_config`/`save_config` **ein** Default-Target:

```python
Target(name="Outbox", path=<ZILPZALP_PATH_OUTBOX>, default=True)
```

Das Outbox-Verzeichnis wird beim Start angelegt. Damit ist ein frisch gestarteter
Container sofort benutzbar (inbox → outbox), ohne dass der User erst Targets
konfigurieren muss. Der Name ist über eigene `targets` in der config.yaml
überschreibbar.

## 4. Inbox-Löschen-Button

`original_handling: keep` bleibt; der Lösch-Button ist sein Gegenstück.

**Route** `POST /documents/{entry_id}/delete` in `web/routes.py`:

- Entry per `queue.get_by_id`; fehlt → HX-Redirect `/queue`.
- `entry.path.unlink(missing_ok=True)` + `queue.remove(entry.path)` +
  `cache.remove(entry.path)` (Teil 5).
- Toast „… wurde gelöscht", HX-Redirect `/queue`.

**UI** — Button für **alle** Stati (pending, analyzing, ready, error) in
`_queue_list.html` (jede Zeile) und `review.html`, mit nativem `hx-confirm`.

**i18n** — `action.delete`, `confirm.delete`, `toast.deleted` (de/en).

**Race (analyzing):** tolerierbar — `queue.remove` macht spätere
`set_ready`/`mark_error` zu No-ops, `unlink(missing_ok=True)` ist idempotent.

## 5. Persistenter Extraktions-Cache, Live-Reload & Re-Analyse

### Ausgangslage

Heute schreibt `extract()` das ODL-JSON in ein `TemporaryDirectory`, parst es zu
`Document` und löscht es wieder. `config_save` setzt bereits `app.state.config`
live, und der Worker liest die Config pro Job frisch — künftig analysierte
Dokumente nutzen also sofort die neue Config. Lücke: bereits `ready`-Einträge
behalten ihren alten Vorschlag.

### Cache-Modul (`backend/src/zilpzalp/cache.py`)

Verzeichnis aus `ZILPZALP_PATH_CACHE` (Default `/data/cache`), beim Start angelegt.

`DocumentCache` über einem Basisverzeichnis:

- Schlüssel = PDF-Dateiname (im Watchfolder eindeutig).
- Pro Dokument `<stem>.json` + `<stem>.md`.
- `load_document(path) -> Document | None` — liest `<stem>.json`, parst via
  `document_from_odl`; `None`, wenn keine Datei existiert.
- `remove(path)` — löscht beide Dateien (idempotent).
- `prune(valid_names)` — entfernt Cache-Dateien ohne zugehöriges Inbox-PDF.

Liegt auf `app.state.cache`, geteilt von Worker (Konstruktor) und Routes.

### Extractor

`extract(pdf_path, cache_dir) -> Document`:

- `opendataloader_pdf.convert(format=["json", "markdown"], output_dir=tmp)` (ein
  JVM-Lauf, beide Formate).
- Die Ausgaben deterministisch nach `cache/<stem>.json` und `cache/<stem>.md`
  verschieben (unabhängig von ODLs interner Benennung).
- JSON zu `Document` parsen und zurückgeben.

Persistentes Schreiben ersetzt das bisherige „Temp löschen" — bewusste Umkehr der
„kein Text auf Platte"-Entscheidung, vertretbar für ein selbst-gehostetes
Einzelnutzer-Tool und Voraussetzung für die spätere Preview.

### Worker (`worker.py`)

Zwei Job-Typen:

- **`submit`** (neuer Watcher-/Scan-Fund): **immer** `extract(...)` → Cache wird
  überschrieben. Löst die Stale-Frage beim Start (Re-Scan extrahiert frisch).
- **`reanalyze`** (nach Config-Save): `cache.load_document(path)`; wenn vorhanden,
  `extract` überspringen und nur `analyze` + `suggest` mit frischer Config
  ausführen (≈ instantan). Fehlt der Cache, Fallback auf `extract`.

`reanalyze_all()`: re-queued alle Einträge mit vorhandenem Cache-JSON (die
erfolgreich extrahierten / `ready`-Einträge). Das früher erwogene `document`-Feld am
`QueueEntry` entfällt — der Disk-Cache ist die Persistenz.

### Live-Reload in `config_save`

Nach erfolgreichem Speichern (`app.state.config` gesetzt) → `worker.reanalyze_all()`.

Ein Watcher-Neustart bei Pfadwechsel ist **nicht mehr nötig**: Pfade kommen aus Env
und sind über die UI nicht änderbar.

### Lifecycle

- Erfolgreiches Ablegen (`_execute`) → `cache.remove(entry.path)`.
- Inbox-Löschen (Teil 4) → `cache.remove(entry.path)`.
- Extraktionsfehler → evtl. Teilausgaben aufräumen.
- Beim Start → `cache.prune` verwaister Dateien.

## 6. Demo & Deployment

### Demo-Bereinigung

Mit env-basierten Pfaden (Defaults unter `/data`) und eingebackener Config
vereinfacht sich die lokale docker-compose-Demo auf **einen** Mount:

- `demo/config/` löschen (Config ist eingebacken).
- `demo/targets/` löschen (ersetzt durch Outbox-Default unter `/data/outbox`).
- `docker-compose.yml`: das `backend`-Volume-Set auf `- ./demo/data:/data`
  reduzieren; den `ZILPZALP_CONFIG`-Override entfernen (Default greift).
- `demo/data/inbox/beispiel-rechnung.pdf` bleibt als Demo-PDF; die übrigen
  Unterordner legt die App beim Start an.
- `.gitignore` entsprechend straffen (targets-Einträge raus; outbox/cache als
  generiert ignorieren).

### Eingebackene Config

`Dockerfile.backend` (runtime-Stage): `COPY backend/config.default.yaml
/config/config.yaml`. `config.default.yaml` enthält nur Domänen-Werte (siehe
Teil 2), keine Pfade/Targets.

**Dokumentierter Caveat (kein Blocker):** UI-Config-Änderungen schreiben nach
`/config/config.yaml` und überleben `restart`, gehen aber bei Container-Neubau
verloren, wenn `/config` nicht gemountet ist. Wer Config persistieren will, mountet
`/config` (ein leerer Bind-Mount verdeckt die eingebackene Datei → Start schlägt
fehl; dann eigene config.yaml hinterlegen). Bleibt bei „direkt einbacken"; ein
Entrypoint-Seeding wäre die robustere Alternative, ist hier aber nicht gewählt.

## Bekannte Akzeptanzen

- Eine offene Review-Seite pollt nicht; ihr Vorschlag kann bis zur Navigation
  veraltet sein, wenn der Eintrag im Hintergrund neu analysiert wurde.

## Testing

- `test_config.py`: env-basierte `Paths` (mit Defaults + Overrides); `paths:` in
  der YAML wird ignoriert; Map-Schema lädt; leeres `patterns` / unbekannter
  `default_pattern` → `ConfigError`; Outbox-Default wird synthetisiert, wenn keine
  targets gesetzt sind.
- `test_cache.py`: `load_document`/`remove`/`prune`; `load_document` ohne Datei →
  `None`.
- `test_extractor.py`: `extract` schreibt `<stem>.json` + `<stem>.md` in den Cache
  und parst das `Document` (bestehende Tests an die `cache_dir`-Signatur anpassen).
- `test_worker.py`: `submit` extrahiert immer; `reanalyze` überspringt `extract`
  bei vorhandenem Cache; `reanalyze_all` nur für gecachte Einträge.
- `test_routes.py`: `/delete` entfernt Datei + Eintrag + Cache; fehlender Entry →
  Redirect; `config_save` triggert Re-Analyse ohne erneute Extraktion.
- Bestehende Tests aufs neue Pattern-/Pfad-Modell anpassen.

## i18n und Dokumentation

- **i18n** — `action.delete`, `confirm.delete`, `toast.deleted` (de/en).
- **Docs** — mkdocs: neues `patterns`-Map-Schema, die `ZILPZALP_PATH_*`-Variablen
  und das Outbox-Default-Target dokumentieren; Hinweis, dass UI-Config-Änderungen
  ohne Neustart wirken und wie man Config persistiert.

## Out of scope (YAGNI)

Als Ideen ins [Backlog](../../backlog.md) aufgenommen:

- **Extrahierte Inhalte in der Review-Preview anzeigen** (json + markdown) — das
  persistierte Cache-Fundament liegt mit diesem Spec.
- **Papierkorb/Wiederherstellung beim Inbox-Löschen** statt hartem Löschen.
- **Cache-Wiederverwendung über Neustart** (extract überspringen, Invalidierung
  über Dateigröße + mtime).
- **Manueller Re-Analyse-Button** als Ergänzung zur automatischen Re-Analyse.
- **Entrypoint-Seeding der Config** für robustes Persistieren bei gemountetem
  `/config`.

Kein Migrationslayer für das alte Listen-/Pfad-Schema: Breaking Change, Beispiele
und Doku werden mitgezogen.
