# Endnutzer-Doku + Packaging Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Liefert die deploybaren Artefakte für ZilpZalp — `Dockerfile.backend` (Python + Temurin-JRE), `Dockerfile.mkdocs`, `docker-compose.yml` — plus die Endnutzer-Dokumentationssite unter `mkdocs/` (mkdocs-material).

**Architecture:** Zwei Container-Images, je eigene `Dockerfile.<name>` auf Root (Design-Spec §2). Das Backend-Image baut die uv-verwaltete Python-App in einer Builder-Stage und kopiert eine headless Temurin-17-JRE in die schlanke Runtime-Stage, weil OpenDataLoader das bundled JAR über `java` aus dem PATH startet. Das mkdocs-Image baut die statische Site (`mkdocs build --strict`) und serviert sie über nginx. `docker-compose.yml` verdrahtet beide mit den in der Config (§5) erwarteten Volumes. Die Endnutzer-Doku ist deutsch (wie die übrige Doku und die UI).

**Tech Stack:** Docker (multi-stage), uv, Eclipse Temurin 17 JRE (headless), python:3.12-slim, mkdocs-material (squidfunk), nginx:alpine.

**Scope (strikt, Roadmap-Zeile #6 / Design-Spec §2, §8):** nur die drei Docker-Artefakte + `mkdocs/`. **Ausgeschlossen** (Design-Spec §10): kein CI/CD, keine Build-Automation, kein Deployment, kein Registry/Publishing. Keine Code-Änderungen an `backend/src/` (die App ist aus Meilenstein 1–5 fertig).

**Hinweis zur „TDD"-Form bei Infra/Doku:** Es gibt hier keine pytest-Unit-Tests. Die „failing test → make it pass"-Schleife wird durch **echte, ausführbare Verifikationskommandos** ersetzt:
- mkdocs: `mkdocs build --strict` (bricht bei kaputten Links/Nav/Refs ab)
- Dockerfiles: `docker build …` + Container-Smoke-Test (`/health`, `java -version`)
- Compose: `docker compose config -q` (Schema-Validierung) + `docker compose build`

Jede Task startet mit dem Verifikationskommando, das **fehlschlägt, weil das Artefakt fehlt**, erstellt dann das Artefakt und führt das Kommando erneut zum Erfolg aus.

**Voraussetzungen für den ausführenden Entwickler:**
- `docker` + `docker compose` v2 verfügbar und lauffähig.
- `uv` installiert (für lokale mkdocs-Builds ohne separates venv via `uvx`).
- Netzwerkzugang für `docker build` (Basis-Images, mkdocs-material, uv).
- Arbeitsverzeichnis ist der Repo-Root `zilpzalp/`, sofern nicht anders angegeben.

---

## File Structure

Neue/geänderte Dateien (alle Pfade relativ zum Repo-Root):

| Pfad | Art | Verantwortung |
|---|---|---|
| `.dockerignore` | Create | Hält Build-Kontext schlank/deterministisch (venv, Caches, docs, data raus) |
| `Dockerfile.backend` | Create | Multi-stage Backend-Image: uv-Build + Temurin-JRE + uvicorn-Entrypoint |
| `Dockerfile.mkdocs` | Create | Multi-stage Doku-Image: `mkdocs build` → nginx-Serve |
| `docker-compose.yml` | Create | Verdrahtet `backend` + `docs` mit Volumes/Ports/Env |
| `.gitignore` | Modify | Ignoriert lokale Compose-Laufzeitordner (`/data/`, `/config/`, `/targets/`) |
| `mkdocs/mkdocs.yml` | Create | mkdocs-material-Konfiguration + Navigation |
| `mkdocs/docs/index.md` | Create | Übersicht / Was ist ZilpZalp |
| `mkdocs/docs/installation.md` | Create | Docker-Compose-Installation, Volumes/Mounts |
| `mkdocs/docs/bedienung.md` | Create | Review-Workflow (Queue → Review → Bestätigung) |
| `mkdocs/docs/konfiguration.md` | Create | `config.yaml`-Referenz |
| `mkdocs/docs/fehlerbehebung.md` | Create | Betrieb & typische Fehlerfälle (`error/`, Logs) |
| `README.md` | Modify | Verweis auf die Endnutzer-Doku (Design-Spec §8: „README.md verweist hierauf") |

Reihenfolge der Tasks = Bauabhängigkeit: erst Build-Kontext (`.dockerignore`), dann Backend-Image, dann mkdocs-Site + Image, dann Compose (verbindet beides), zuletzt README-Verweis.

---

## Task 1: Build-Kontext eingrenzen (`.dockerignore`)

Ohne `.dockerignore` würden `.venv/` (hunderte MB), Caches und `docs/` in den Build-Kontext wandern — langsam und nichtdeterministisch. Diese Datei muss vor dem ersten `docker build` existieren.

**Files:**
- Create: `.dockerignore`

- [ ] **Step 1: Verifikation, dass noch keine `.dockerignore` existiert (erwarteter „Fehlschlag")**

Run: `test -f .dockerignore && echo PRESENT || echo MISSING`
Expected: `MISSING`

- [ ] **Step 2: `.dockerignore` anlegen**

Create `.dockerignore`:

```gitignore
# Python / uv
**/.venv/
**/__pycache__/
**/*.py[cod]
**/.pytest_cache/
**/.ruff_cache/

# VCS / IDE
.git/
.gitignore
.gitattributes
.idea/

# Interne Doku & Design (nicht im Laufzeit-Image nötig)
docs/

# Lokale Compose-Laufzeitdaten (niemals ins Image)
data/
config/
targets/

# Build-Artefakte der Doku-Site
mkdocs/site/

# Tests werden zur Laufzeit nicht gebraucht
backend/tests/
```

- [ ] **Step 3: Verifikation, dass die Datei jetzt da ist**

Run: `test -f .dockerignore && echo PRESENT || echo MISSING`
Expected: `PRESENT`

- [ ] **Step 4: Commit**

```bash
git add .dockerignore
git commit -m "build(docker): add .dockerignore to keep build context lean"
```

---

## Task 2: Backend-Image (`Dockerfile.backend`)

Multi-stage: Builder-Stage installiert Dependencies mit uv (`uv sync --frozen --no-dev`) in `/app/backend/.venv`; Runtime-Stage ist `python:3.12-slim`, bekommt die headless Temurin-17-JRE per `COPY --from=eclipse-temurin:17-jre-jammy` (das JAR liegt bereits gebündelt im Paket `opendataloader_pdf`, OpenDataLoader ruft `java` aus dem PATH). Healthcheck nutzt die stdlib (`urllib`), damit kein `curl` ins Image muss.

**Files:**
- Create: `Dockerfile.backend`

- [ ] **Step 1: Verifikation, dass das Backend-Image (noch) nicht baubar ist (erwarteter Fehlschlag)**

Run: `docker build -f Dockerfile.backend -t zilpzalp-backend:test .`
Expected: FAIL mit „failed to read dockerfile" / „Dockerfile.backend: no such file or directory" (Datei existiert noch nicht).

- [ ] **Step 2: `Dockerfile.backend` anlegen**

Create `Dockerfile.backend`:

```dockerfile
# syntax=docker/dockerfile:1

# --- Builder: Dependencies + venv via uv ------------------------------------
FROM python:3.12-slim AS builder

# uv-Binary aus dem offiziellen Image kopieren (kein pip-Bootstrap nötig).
COPY --from=ghcr.io/astral-sh/uv:0.9.0 /uv /uvx /bin/

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=0

WORKDIR /app/backend

# Erst nur Lockfiles/Metadaten kopieren → maximaler Layer-Cache bei Dep-Änderungen.
COPY backend/pyproject.toml backend/uv.lock ./
COPY backend/src ./src

# Reproduzierbare, dev-freie Installation in /app/backend/.venv
RUN uv sync --frozen --no-dev

# --- Runtime: schlankes Python + Temurin-JRE (headless) ---------------------
FROM python:3.12-slim AS runtime

# Headless Temurin-17-JRE aus dem offiziellen Temurin-Image übernehmen.
# OpenDataLoader startet das gebündelte JAR über `java` aus dem PATH.
ENV JAVA_HOME=/opt/java/openjdk
COPY --from=eclipse-temurin:17-jre-jammy /opt/java/openjdk ${JAVA_HOME}

# venv vor System-PATH; Java zusätzlich verfügbar machen.
ENV PATH="/app/backend/.venv/bin:${JAVA_HOME}/bin:${PATH}"

WORKDIR /app/backend

# Anwendung + venv aus der Builder-Stage übernehmen.
COPY --from=builder /app/backend/.venv ./.venv
COPY backend/src ./src

# Config wird als Volume gemountet; Default-Pfad zeigt dorthin.
ENV ZILPZALP_CONFIG=/config/config.yaml

EXPOSE 8000

# Healthcheck ohne curl: stdlib-urllib gegen /health.
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import sys, urllib.request; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=3).status == 200 else 1)"

CMD ["uvicorn", "zilpzalp.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

- [ ] **Step 3: Image bauen — jetzt erfolgreich**

Run: `docker build -f Dockerfile.backend -t zilpzalp-backend:test .`
Expected: SUCCESS, Abschlusszeile `naming to docker.io/library/zilpzalp-backend:test`.

- [ ] **Step 4: Smoke-Test — Java vorhanden und auf PATH**

Run: `docker run --rm zilpzalp-backend:test java -version`
Expected: Ausgabe enthält `openjdk version "17` (auf stderr).

- [ ] **Step 5: Smoke-Test — App startet und `/health` antwortet**

Run:
```bash
# Minimal-Config + Datenordner für einen echten Start bereitstellen.
TMP=$(mktemp -d)
mkdir -p "$TMP/config" "$TMP/inbox" "$TMP/error" "$TMP/processed"
cat > "$TMP/config/config.yaml" <<'YAML'
paths:
  watchfolder: /data/inbox
  error_folder: /data/error
  processed_folder: /data/processed
original_handling: move
summary_mode: on_conflict
default_pattern: "{date}__{sender}_{doctype}_{description}"
date_format: "%Y-%m-%d"
targets:
  - name: Finanzen
    path: /data/processed
    default: true
patterns:
  - name: standard
    template: "{date}__{sender}_{doctype}_{description}"
rules: []
YAML
docker run -d --name zz-health \
  -p 8000:8000 \
  -v "$TMP/config":/config \
  -v "$TMP/inbox":/data/inbox \
  -v "$TMP/error":/data/error \
  -v "$TMP/processed":/data/processed \
  zilpzalp-backend:test
sleep 5
curl -fsS http://127.0.0.1:8000/health; echo
docker rm -f zz-health; rm -rf "$TMP"
```
Expected: `{"status":"ok"}`

- [ ] **Step 6: Commit**

```bash
git add Dockerfile.backend
git commit -m "build(docker): add backend image (uv + Temurin 17 JRE)"
```

---

## Task 3: mkdocs-Site — Gerüst + `mkdocs.yml`

Erst die mkdocs-Konfiguration mit vollständiger Navigation. `mkdocs build --strict` schlägt fehl, sobald die in `nav` referenzierten Seiten noch nicht existieren — das ist der „failing test", den die folgende Task (Inhalte) grün macht. Lokal ohne eigenes venv via `uvx`.

**Files:**
- Create: `mkdocs/mkdocs.yml`

- [ ] **Step 1: Verifikation, dass noch keine mkdocs-Config existiert (erwarteter Fehlschlag)**

Run: `test -f mkdocs/mkdocs.yml && echo PRESENT || echo MISSING`
Expected: `MISSING`

- [ ] **Step 2: `mkdocs/mkdocs.yml` anlegen**

Create `mkdocs/mkdocs.yml`:

```yaml
site_name: ZilpZalp — Dokumentation
site_description: Halb-automatische Dokumentenablage mit Mensch in der Schleife
docs_dir: docs
language: de

theme:
  name: material
  language: de
  palette:
    - media: "(prefers-color-scheme: light)"
      scheme: default
      toggle:
        icon: material/weather-night
        name: Zu dunklem Modus wechseln
    - media: "(prefers-color-scheme: dark)"
      scheme: slate
      toggle:
        icon: material/weather-sunny
        name: Zu hellem Modus wechseln
  features:
    - navigation.instant
    - navigation.top
    - content.code.copy

nav:
  - Übersicht: index.md
  - Installation: installation.md
  - Bedienung: bedienung.md
  - Konfiguration: konfiguration.md
  - Fehlerbehebung: fehlerbehebung.md

markdown_extensions:
  - admonition
  - pymdownx.details
  - pymdownx.superfences
  - tables
```

- [ ] **Step 3: Strict-Build ausführen — schlägt fehl, weil Inhaltsseiten fehlen**

Run: `cd mkdocs && uvx --with mkdocs-material mkdocs build --strict; cd ..`
Expected: FAIL — Meldungen wie `A reference to 'index.md' is included in the 'nav' configuration, which is not found in the documentation files` (für alle fünf Seiten).

- [ ] **Step 4: Commit (Config-Gerüst, Inhalte folgen in Task 4)**

```bash
git add mkdocs/mkdocs.yml
git commit -m "docs(mkdocs): add mkdocs-material config and navigation"
```

---

## Task 4: mkdocs-Site — Inhaltsseiten (deutsch)

Alle fünf in der `nav` referenzierten Seiten anlegen. Danach baut `mkdocs build --strict` ohne Fehler/Warnungen durch. Inhalte spiegeln das Design-Spec (§4 Workflow, §5 Config, §6 Fehlerbehandlung, §2 Volumes).

**Files:**
- Create: `mkdocs/docs/index.md`
- Create: `mkdocs/docs/installation.md`
- Create: `mkdocs/docs/bedienung.md`
- Create: `mkdocs/docs/konfiguration.md`
- Create: `mkdocs/docs/fehlerbehebung.md`

- [ ] **Step 1: `mkdocs/docs/index.md` anlegen**

Create `mkdocs/docs/index.md`:

```markdown
# ZilpZalp

ZilpZalp ist eine **halb-automatische Dokumentenablage** für den Eigenbetrieb im
Heimnetz. Es beobachtet einen Ordner, liest eingehende PDFs und schlägt einen
sauberen Dateinamen aus Datum, Absender und Dokumenttyp vor — **du prüfst, bestätigst,
fertig**. Lokal, ohne Cloud.

## Kerngedanke

- **Mensch in der Schleife:** ZilpZalp füllt vor, was es sicher weiß. Die endgültige
  Entscheidung triffst immer du.
- **Mehrere Datumsangaben sichtbar:** Ein Dokument enthält oft mehrere Daten
  (Rechnungs-, Leistungs-, Fälligkeitsdatum). ZilpZalp zeigt **alle** erkannten
  Kandidaten zur Auswahl an, statt im Hintergrund eines festzulegen.
- **Datensparsam:** Es entsteht keine Historie und keine Datenbank. Quelle der Wahrheit
  ist der überwachte Ordner selbst; einzige dauerhafte Einstellung ist `config.yaml`.

## Wie es funktioniert

```
Watchfolder → Analyse (Datum/Absender/Typ) → Vorschlag → Review im Browser
→ Bestätigung → Kopie in den Zielordner → Original verschoben/gelöscht/behalten
```

## Loslegen

- [Installation](installation.md) — Einrichtung mit Docker Compose
- [Bedienung](bedienung.md) — der Review-Workflow im Browser
- [Konfiguration](konfiguration.md) — `config.yaml` im Detail
- [Fehlerbehebung](fehlerbehebung.md) — Betrieb und typische Fehlerfälle

!!! warning "Kein Zugriffsschutz"
    ZilpZalp hat **kein Login**. Es ist für den Betrieb im vertrauenswürdigen Heimnetz
    gedacht. Mache die Weboberfläche nicht ungeschützt aus dem Internet erreichbar.
```

- [ ] **Step 2: `mkdocs/docs/installation.md` anlegen**

Create `mkdocs/docs/installation.md`:

```markdown
# Installation

ZilpZalp wird als zwei Container betrieben: das **Backend** (Weboberfläche +
Verarbeitung) und die **Doku-Site** (diese Dokumentation). Beide werden über
`docker-compose.yml` gestartet.

## Voraussetzungen

- Docker und Docker Compose v2
- Ein Linux-Host (oder WSL2). **Hinweis:** Auf gemounteten Windows-Pfaden (`/mnt/c/…`)
  sind Dateisystem-Events unzuverlässig — lege Watchfolder/Zielordner auf native
  Linux-Pfade.

## Ordner und Volumes

ZilpZalp arbeitet ausschließlich über gemountete Verzeichnisse. Das Compose-Setup
erwartet relativ zum Repo-Root:

| Host-Ordner | Container-Pfad | Zweck |
|---|---|---|
| `./config` | `/config` | enthält `config.yaml` (einzige dauerhafte Einstellung) |
| `./data/inbox` | `/data/inbox` | **Watchfolder** — hier landen neue PDFs |
| `./data/error` | `/data/error` | unlesbare/fehlerhafte PDFs |
| `./data/processed` | `/data/processed` | verarbeitete Originale (bei `original_handling: move`) |
| `./targets` | `/targets` | Zielordner für die abgelegten Dateien |

## Schritt für Schritt

1. **Ordner und Konfiguration anlegen:**

    ```bash
    mkdir -p config data/inbox data/error data/processed targets/finanzen
    cp backend/config.example.yaml config/config.yaml
    ```

2. **`config/config.yaml` anpassen.** Die Pfade darin sind **Container-Pfade**
   (`/data/inbox`, `/targets/finanzen`, …), nicht Host-Pfade. Details in der
   [Konfiguration](konfiguration.md).

3. **Container bauen und starten:**

    ```bash
    docker compose up -d --build
    ```

4. **Aufrufen:**
    - Weboberfläche: <http://localhost:8000>
    - Diese Dokumentation: <http://localhost:8001>

5. **Status prüfen:**

    ```bash
    docker compose ps
    curl -fsS http://localhost:8000/health
    ```

    Erwartet: `{"status":"ok"}`.

## Stoppen / Aktualisieren

```bash
docker compose down          # stoppt beide Container
docker compose up -d --build # nach Änderungen neu bauen und starten
```

!!! note "Startverhalten"
    Beim Start scannt ZilpZalp den Watchfolder einmalig und nimmt danach neue Dateien
    live über Dateisystem-Events auf. Ein unbestätigtes PDF taucht nach einem Neustart
    wieder in der Queue auf — der Watchfolder ist die Quelle der Wahrheit.
```

- [ ] **Step 3: `mkdocs/docs/bedienung.md` anlegen**

Create `mkdocs/docs/bedienung.md`:

```markdown
# Bedienung

Die gesamte Bedienung läuft über die Weboberfläche unter
<http://localhost:8000>.

## Der Review-Workflow

1. **PDF ablegen.** Lege eine PDF-Datei in den Watchfolder (`./data/inbox`).
   ZilpZalp erkennt sie automatisch und analysiert sie.

2. **Queue ansehen.** Die Startseite zeigt alle wartenden Dokumente. Jeder Eintrag
   steht auf `pending` (bereit zur Prüfung) oder `error` (siehe
   [Fehlerbehebung](fehlerbehebung.md)).

3. **Review öffnen.** Ein Klick auf einen Eintrag öffnet die Detailansicht mit dem
   Vorschlag:
    - **Datum:** alle erkannten Datumskandidaten als Auswahl, jeweils mit Kontext
      (z. B. „Rechnungsdatum"). Eine Vorauswahl kann gesetzt sein; du kannst jederzeit
      einen anderen Kandidaten wählen. Wurde kein Datum gefunden, gibst du es manuell ein.
    - **Absender, Typ, Beschreibung:** vorbefüllt, soweit ZilpZalp sie sicher ableiten
      konnte — frei korrigierbar.
    - **Zielordner:** Auswahl aus den konfigurierten Zielen.
    - **Finaler Dateiname:** wird live aus dem Namensmuster gebildet.

4. **Bestätigen.** Je nach Einstellung `summary_mode` erscheint vorher eine
   Zusammenfassung. Nach der Bestätigung kopiert ZilpZalp die Datei in den Zielordner.

5. **Original.** Das Original im Watchfolder wird gemäß `original_handling` behandelt
   (verschoben, gelöscht oder belassen). Der Eintrag verschwindet aus der Queue.

## Namenskonflikte

Existiert im Zielordner bereits eine Datei mit demselben Namen, **entscheidest du** —
ZilpZalp hängt **kein** automatisches Suffix an und überschreibt nichts ungefragt.

## Konfiguration in der Oberfläche

Die Seite **Konfiguration** zeigt die aktuelle `config.yaml` und erlaubt Änderungen.
Ungültige Eingaben werden mit einer Fehlermeldung abgewiesen; die bisherige Konfiguration
bleibt dann aktiv. Inhaltliche Referenz: [Konfiguration](konfiguration.md).
```

- [ ] **Step 4: `mkdocs/docs/konfiguration.md` anlegen**

Create `mkdocs/docs/konfiguration.md`:

````markdown
# Konfiguration

Die Datei `config.yaml` (gemountet unter `/config/config.yaml`) ist die **einzige
dauerhafte Einstellung**. Sie wird beim Start validiert: Fehlt ein Pflichtpfad oder
enthält ein Namensmuster einen unbekannten Platzhalter, startet ZilpZalp **nicht**,
sondern meldet den Fehler klar.

!!! info "Pfade sind Container-Pfade"
    Alle Pfade in `config.yaml` beziehen sich auf das **Innere des Containers**
    (`/data/inbox`, `/targets/…`). Wie diese auf Host-Ordner abgebildet werden, legt
    `docker-compose.yml` fest (siehe [Installation](installation.md)).

## Vollständiges Beispiel

```yaml
paths:
  watchfolder: /data/inbox
  error_folder: /data/error
  processed_folder: /data/processed   # nur nötig bei original_handling: move

original_handling: move        # move | delete | keep
summary_mode: on_conflict      # always | on_conflict | never

default_pattern: "{date}__{sender}_{doctype}_{description}"
date_format: "%Y-%m-%d"

# Optional: zusätzliche Datums-Matcher für Sonderfälle.
# Die eingebaute Datumserkennung läuft IMMER und braucht KEINE Konfiguration.
date_patterns:
  - label: leistungsdatum
    regex: 'Leistungsdatum:\s*(\d{2}\.\d{2}\.\d{4})'

targets:
  - name: Finanzen
    path: /targets/finanzen
    default: false

patterns:
  - name: standard
    template: "{date}__{sender}_{doctype}_{description}"

rules:
  - name: Stromrechnung Stadtwerke
    match:
      sender_contains: "Stadtwerke"
      keywords_any: ["Stromabschlag", "Abschlag"]
    apply:
      sender: "Stadtwerke"
      doctype: "Rechnung"
      description: "Stromabschlag"
      pattern: standard
      preferred_date: rechnungsdatum
      targets: ["Finanzen"]
```

## Felder

### `paths`

| Schlüssel | Pflicht | Bedeutung |
|---|---|---|
| `watchfolder` | ja | überwachter Eingangsordner |
| `error_folder` | ja | Ablage für unlesbare PDFs |
| `processed_folder` | nur bei `original_handling: move` | Ablage verarbeiteter Originale |

### `original_handling`

Was nach erfolgreicher Ablage mit dem Original im Watchfolder geschieht:

- `move` — in `processed_folder` verschieben
- `delete` — löschen
- `keep` — im Watchfolder belassen

### `summary_mode`

Wann vor der Bestätigung eine Zusammenfassung erscheint:
`always` (immer), `on_conflict` (nur bei Namenskonflikt), `never` (nie).

### `date_format`

Format des Datums im Dateinamen, als Python-`strftime`-Muster
(z. B. `%Y-%m-%d` → `2026-06-14`).

### Namensmuster (`default_pattern`, `patterns`)

Platzhalter im Muster: `{date}`, `{sender}`, `{doctype}`, `{description}`.
`patterns` benennt wiederverwendbare Muster, auf die Regeln per Name verweisen.

### `date_patterns` (optional)

Zusätzliche Datums-Matcher für Sonderfälle. Die erste Capture-Group liefert den
Datumswert, `label` erscheint als Kontext in der Oberfläche. Diese Einträge
**ergänzen** die eingebauten Formate (additiv) — sie ersetzen sie nicht. Ungültige
reguläre Ausdrücke werden beim Laden mit klarer Meldung abgewiesen.

### `targets`

Liste der Zielordner mit `name`, `path` und `default` (Vorauswahl in der Oberfläche).

### `rules`

Geordnete Liste — **die erste passende Regel gewinnt**. Eine Regel **automatisiert
nichts durch**: `apply` setzt nur Vorschläge, die du in der Oberfläche bestätigst oder
änderst.

- `match` — alle Bedingungen müssen zutreffen (z. B. `sender_contains`, `keywords_any`).
- `apply` — vorzuschlagende Werte (`sender`, `doctype`, `description`, `pattern`,
  `targets`) sowie `preferred_date`: **wählt** einen der erkannten Datumskandidaten
  **vor**, verbirgt die übrigen aber nie.
````

- [ ] **Step 5: `mkdocs/docs/fehlerbehebung.md` anlegen**

Create `mkdocs/docs/fehlerbehebung.md`:

````markdown
# Fehlerbehebung

ZilpZalp macht Fehler sichtbar, **ohne** eine fachliche Historie aufzubauen. Es gibt
drei Fehlerarten.

## Unlesbares / leeres PDF

Enthält ein PDF keinen Text (z. B. ein reiner Scan ohne Textebene — **kein OCR im MVP**)
oder ist es korrupt, verschiebt ZilpZalp die Datei in den `error/`-Ordner und markiert
den Queue-Eintrag als `error` mit Kurzgrund.

Der `error/`-Ordner ist die **einzige dauerhafte Fehlerspur** — eine Datei am Rand des
Workflows, kein Protokoll. Prüfe die Datei, behandle sie außerhalb von ZilpZalp und
lege sie ggf. korrigiert erneut in den Watchfolder.

## Technischer Laufzeitfehler

Schlägt z. B. das Kopieren fehl (Zielpfad weg, fehlende Schreibrechte), erscheint der
Fehler **transient** am Queue-Eintrag und wird zusätzlich in die Container-Logs
geschrieben:

```bash
docker compose logs -f backend
```

Transiente Fehler verschwinden bei Neustart/Rescan, da der Zustand neu aus dem
Watchfolder abgeleitet wird.

## Konfigurationsfehler

- **Beim Start:** Ist `config.yaml` ungültig oder fehlt ein Pflichtpfad, startet der
  Backend-Container nicht. Die Ursache steht in den Logs:

    ```bash
    docker compose logs backend
    ```

- **Zur Laufzeit (Änderung in der Oberfläche):** Ungültige Eingaben werden mit
  Validierungsfehler abgewiesen; die bisherige Konfiguration bleibt aktiv.

## Container-Diagnose

```bash
docker compose ps                       # laufen beide Container?
curl -fsS http://localhost:8000/health  # Backend gesund? -> {"status":"ok"}
docker compose logs -f backend          # Live-Logs des Backends
docker compose logs -f docs             # Live-Logs der Doku-Site
```

## Dateien werden nicht erkannt

- Liegt das PDF wirklich im gemounteten Watchfolder (`./data/inbox` → `/data/inbox`)?
- Auf WSL2/Windows: liegt der Ordner auf einem **nativen Linux-Pfad**? Auf `/mnt/c/…`
  sind Dateisystem-Events unzuverlässig.
- Ein Neustart (`docker compose restart backend`) erzwingt einen initialen Scan.

!!! note "Logs sind Betriebsdaten, keine Dokumenthistorie"
    Die Container-Logs (stdout) dienen Betrieb und Debugging. Sie sind bewusst **keine**
    produktseitige Historie der verarbeiteten Dokumente.
````

- [ ] **Step 6: Strict-Build ausführen — jetzt fehler- und warnungsfrei**

Run: `cd mkdocs && uvx --with mkdocs-material mkdocs build --strict; cd ..`
Expected: SUCCESS, endet mit `Documentation built in … seconds`, **keine** WARNING/ERROR-Zeilen.

- [ ] **Step 7: Build-Artefakt nicht committen, dann committen**

```bash
rm -rf mkdocs/site
git add mkdocs/docs/
git commit -m "docs(mkdocs): add end-user documentation pages (de)"
```

---

## Task 5: Doku-Image (`Dockerfile.mkdocs`)

Multi-stage: Build-Stage nutzt das offizielle `squidfunk/mkdocs-material`-Image und baut die statische Site (`mkdocs build --strict`); die Serve-Stage ist `nginx:alpine` mit der Site unter dem Webroot. Statisch ausgeliefert, keine Dev-Server-Laufzeit.

**Files:**
- Create: `Dockerfile.mkdocs`

- [ ] **Step 1: Verifikation, dass das Doku-Image (noch) nicht baubar ist (erwarteter Fehlschlag)**

Run: `docker build -f Dockerfile.mkdocs -t zilpzalp-docs:test .`
Expected: FAIL mit „failed to read dockerfile" (Datei existiert noch nicht).

- [ ] **Step 2: `Dockerfile.mkdocs` anlegen**

Create `Dockerfile.mkdocs`:

```dockerfile
# syntax=docker/dockerfile:1

# --- Build: statische Site mit mkdocs-material erzeugen ----------------------
FROM squidfunk/mkdocs-material:9 AS build

WORKDIR /docs
COPY mkdocs/ ./
# --strict bricht bei kaputten Links/Nav ab → fehlerhafte Doku wird kein Image.
RUN mkdocs build --strict

# --- Serve: statische Auslieferung über nginx -------------------------------
FROM nginx:alpine AS serve
COPY --from=build /docs/site /usr/share/nginx/html
EXPOSE 80
```

- [ ] **Step 3: Image bauen — jetzt erfolgreich**

Run: `docker build -f Dockerfile.mkdocs -t zilpzalp-docs:test .`
Expected: SUCCESS, Abschlusszeile `naming to docker.io/library/zilpzalp-docs:test`.

- [ ] **Step 4: Smoke-Test — Site wird ausgeliefert**

Run:
```bash
docker run -d --name zz-docs -p 8001:80 zilpzalp-docs:test
sleep 2
curl -fsS http://127.0.0.1:8001/ | grep -o "ZilpZalp" | head -1
docker rm -f zz-docs
```
Expected: `ZilpZalp` (die Startseite wird ausgeliefert).

- [ ] **Step 5: Commit**

```bash
git add Dockerfile.mkdocs
git commit -m "build(docker): add mkdocs site image (build + nginx serve)"
```

---

## Task 6: Orchestrierung (`docker-compose.yml`) + `.gitignore`

`docker-compose.yml` verdrahtet beide Images mit den in der Config erwarteten Volumes und Ports und referenziert die `Dockerfile.<name>` explizit (Design-Spec §2). Die lokalen Laufzeitordner (`data/`, `config/`, `targets/`) gehören nicht ins Repo.

**Files:**
- Create: `docker-compose.yml`
- Modify: `.gitignore`

- [ ] **Step 1: Verifikation, dass noch keine Compose-Datei existiert (erwarteter Fehlschlag)**

Run: `docker compose config -q`
Expected: FAIL mit „no configuration file provided: not found".

- [ ] **Step 2: `docker-compose.yml` anlegen**

Create `docker-compose.yml`:

```yaml
services:
  backend:
    build:
      context: .
      dockerfile: Dockerfile.backend
    image: zilpzalp-backend
    ports:
      - "8000:8000"
    environment:
      ZILPZALP_CONFIG: /config/config.yaml
    volumes:
      - ./config:/config
      - ./data/inbox:/data/inbox
      - ./data/error:/data/error
      - ./data/processed:/data/processed
      - ./targets:/targets
    restart: unless-stopped

  docs:
    build:
      context: .
      dockerfile: Dockerfile.mkdocs
    image: zilpzalp-docs
    ports:
      - "8001:80"
    restart: unless-stopped
```

- [ ] **Step 3: Compose-Schema validieren — jetzt erfolgreich**

Run: `docker compose config -q`
Expected: SUCCESS (keine Ausgabe, Exit-Code 0).

- [ ] **Step 4: `.gitignore` um Laufzeitordner ergänzen**

In `.gitignore`, hänge nach der Zeile `backend/config.yaml` an:

```gitignore
# Lokale Compose-Laufzeitordner (nicht versionieren)
/data/
/config/
/targets/
```

- [ ] **Step 5: Verifizieren, dass die Laufzeitordner ignoriert werden**

Run:
```bash
mkdir -p config data/inbox targets
git status --porcelain config data targets
```
Expected: **keine Ausgabe** (alles ignoriert). Danach Testordner entfernen:
`rmdir config data/inbox data targets 2>/dev/null; true`

- [ ] **Step 6: End-to-End — beide Images über Compose bauen**

Run: `docker compose build`
Expected: SUCCESS für `backend` und `docs` (beide Images werden gebaut).

- [ ] **Step 7: Commit**

```bash
git add docker-compose.yml .gitignore
git commit -m "build(docker): add docker-compose wiring backend + docs"
```

---

## Task 7: README auf die Endnutzer-Doku verweisen

Design-Spec §8 fordert: „`README.md` verweist hierauf". Ein kurzer Abschnitt mit Quickstart-Verweis genügt — keine Inhalte duplizieren.

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Quickstart-/Doku-Abschnitt in `README.md` einfügen**

In `README.md`, füge direkt **nach** dem einleitenden Absatz (nach Zeile 3, vor `## Development`) ein:

```markdown

## Documentation & Quickstart

End-user documentation (installation, usage, configuration, troubleshooting) is built
with mkdocs-material under [`mkdocs/`](mkdocs/) and served as its own container.

```bash
mkdir -p config data/inbox data/error data/processed targets/finanzen
cp backend/config.example.yaml config/config.yaml   # then edit the paths
docker compose up -d --build
```

- Web UI: <http://localhost:8000>
- Documentation: <http://localhost:8001>
```

- [ ] **Step 2: Verifizieren, dass der Verweis steht**

Run: `grep -n "mkdocs/" README.md`
Expected: mindestens eine Trefferzeile mit dem Link auf `mkdocs/`.

- [ ] **Step 3: Commit**

```bash
git add README.md
git commit -m "docs: link end-user documentation and quickstart in README"
```

---

## Task 8: Roadmap auf „fertig" setzen

Nach erfolgreicher Umsetzung Meilenstein #6 in `docs/mvp/roadmap.md` abschließen. **Diesen Schritt erst ausführen, wenn alle Tasks 1–7 grün sind und committet wurden.**

**Files:**
- Modify: `docs/mvp/roadmap.md`

- [ ] **Step 1: Finalen Commit-SHA ermitteln**

Run: `git rev-parse --short HEAD`
Expected: ein Kurz-SHA (z. B. `abc1234`) — der letzte Commit aus Task 7.

- [ ] **Step 2: Roadmap-Zeile #6 aktualisieren**

In `docs/mvp/roadmap.md`, ersetze in der Zeile für Meilenstein `| 6 |`:
- die Plan-Spalte `_tbd_` durch
  `[Plan](superpowers/plans/2026-06-14-1718-doku-packaging.md)`
- den Status `📋 geplant` durch `✅ fertig`
- die letzte Spalte `—` durch den Kurz-SHA in Backticks (aus Step 1)

- [ ] **Step 3: Commit**

```bash
git add docs/roadmap.md
git commit -m "docs(6): mark Doku + Packaging milestone complete in roadmap"
```

---

## Self-Review (vom Plan-Autor durchgeführt)

**1. Spec-Abdeckung (Roadmap #6 / Design-Spec §2, §8):**
- `Dockerfile.backend` (Python + Temurin-17-JRE, §2): Task 2 ✅
- `Dockerfile.mkdocs` (§2, §8): Task 5 ✅
- `docker-compose.yml` (referenziert Dockerfiles explizit, Volumes aus §5): Task 6 ✅
- `mkdocs/` mit mkdocs-material, Inhalte Installation/Bedienung/Konfiguration/Betrieb-Fehler (§8): Tasks 3–4 ✅
- „README.md verweist hierauf" (§8): Task 7 ✅
- Build-Kontext/`.dockerignore` (notwendig für §2-Images): Task 1 ✅
- Roadmap-Abschluss (Arbeitsweise): Task 8 ✅

**2. Scope-Ausschluss (§10):** Kein CI/CD, keine Build-Automation, kein Deployment, kein Registry-Push — der Plan liefert nur die Artefakte + lokale Build-/Smoke-Verifikation. Keine Änderungen an `backend/src/`. ✅

**3. Platzhalter-Scan:** Jede Datei ist vollständig ausformuliert; keine TODO/TBD. Verifikationskommandos statt vager „teste das". ✅

**4. Konsistenz:** Image-Namen (`zilpzalp-backend`, `zilpzalp-docs`), Ports (8000 Backend, 8001 Doku), Env (`ZILPZALP_CONFIG=/config/config.yaml`), Volume-Pfade (`/config`, `/data/inbox|error|processed`, `/targets`) sind über Dockerfile, Compose, README und Doku hinweg identisch. `JAVA_HOME=/opt/java/openjdk` entspricht dem Standardpfad des Temurin-Images. Healthcheck und `/health` decken sich mit `main.py:51`. ✅
