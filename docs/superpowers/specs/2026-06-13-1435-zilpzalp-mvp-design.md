# ZilpZalp MVP — Technisches Design

Status: Entwurf zur Freigabe
Datum: 2026-06-13
Grundlage: [docs/vision.md](../../vision.md)

Dieses Dokument überführt die Produktvision in ein umsetzbares technisches Design für
das MVP. Es legt Tech-Stack, Projektstruktur, Komponenten, Datenfluss, Konfiguration,
Fehlerbehandlung und Teststrategie fest und klärt die offenen Fragen aus Abschnitt 18
der Vision.

---

## 1. Getroffene Grundentscheidungen

| Thema | Entscheidung | Begründung |
|---|---|---|
| Backend-Stack | **Python + FastAPI** | Reifes Daten-/Web-Ökosystem; OCR/KI später leicht nachrüstbar |
| PDF-Parsing | **OpenDataLoader PDF** (nur lokaler Strukturmodus) | Liefert eine **strukturierte** Analysegrundlage (Überschriften, Tabellenzellen, Lesereihenfolge, Bounding Boxes) statt flachem Text — adressiert direkt das Hauptrisiko „falsches Datum" (§4.3, Vision 17.1). Apache-2.0, läuft 100 % on-device. Preis: Java-Laufzeit im Image (siehe nächste Zeile). |
| Java-Laufzeit | **Eclipse Temurin 17 JRE (headless)** | OpenDataLoader ist ein Java-Tool; das `pip`-Paket startet pro `convert()` eine JVM (benötigt Java 11+). Temurin = verbreiteter OpenJDK-Build (GPLv2+CE), headless, per Multi-Stage in den Backend-Container kopiert. |
| Web-UI | **Server-rendered, Jinja2 + HTMX** | Kein Build-Step, ein Container, minimaler Stack für ein 1-Nutzer-Tool |
| Konfigurationsspeicher | **YAML-Datei** (`config.yaml`) | Transparent, versionierbar, hand- und UI-editierbar; passt zu Datensparsamkeit |
| Vorschlagslogik MVP | **rein regelbasiert** | Kernnutzen unabhängig von KI (Prinzip 6.2); KI als gekapselter Erweiterungspunkt |
| Login / Zugriffsschutz | **kein Login** | Heimnetz-Ausrichtung; Doku-Hinweis zur Netzverantwortung |
| Hash-Duplikaterkennung | **nicht im MVP** | Komfort, nicht Kern; reduziert MVP-Risiko (streicht Vision 9.8 / 18.5) |
| Python-Tooling | **uv** | Dependency-/venv-Management, `uv run` / `uv sync`; `pyproject.toml` als Quelle der Wahrheit |
| Entwicklungsplattform | **WSL2** | Hinweis: Filesystem-Events auf gemounteten Windows-Pfaden (`/mnt/c`) unzuverlässig — native Linux-Pfade bevorzugen |
| UI-Tests | **Playwright (Skill)** | Browser-getriebene Tests der HTMX-UI |

---

## 2. Projektstruktur (Monorepo, Ordner pro Projektart)

`src` liegt nie auf Root. Auf Root nur Dockerfiles, Compose und Meta-Dateien. Jede
Projektart hat eine eigene, passend benannte `Dockerfile.<name>`.

```
zilpzalp/
├── Dockerfile.backend         # Root: Backend-Image
├── Dockerfile.mkdocs          # Root: Endnutzer-Doku-Site
├── docker-compose.yml         # referenziert die passenden Dockerfiles explizit
├── README.md  LICENSE  CLAUDE.md  .gitattributes  .gitignore
│
├── docs/                      # intern / Devs
│   ├── vision.md
│   ├── superpowers/specs/     # Design-Specs (dieses Dokument)
│   └── ui/                    # sprachliche UI-Seitenbeschreibung (entsteht mit der UI)
│
├── backend/                   # Projektart 1: Python/FastAPI
│   ├── pyproject.toml         # Deps + Tooling (ruff, pytest), uv-verwaltet
│   ├── src/
│   │   └── zilpzalp/
│   │       ├── __init__.py
│   │       ├── main.py        # FastAPI-App, Startup (Watcher starten, Config laden)
│   │       ├── config.py      # YAML laden / validieren / speichern
│   │       ├── watcher.py     # watchdog-Events + initialer Scan
│   │       ├── queue.py       # In-memory-Register der pending Dokumente
│   │       ├── extractor.py   # OpenDataLoader-Adapter: JVM-Aufruf → Document-Modell
│   │       ├── analyzer.py    # Datum / Absender / Typ / Keywords / Beschreibung
│   │       ├── suggestion.py  # Pattern + Regeln → Dateinamen-/Zielordner-Vorschlag
│   │       ├── processor.py   # Copy an Zielordner + Original-Handling
│   │       └── web/
│   │           ├── routes.py
│   │           ├── templates/ # *.html (Jinja2)
│   │           └── static/    # htmx.min.js, style.css
│   └── tests/                 # spiegelt src/zilpzalp/
│
├── mkdocs/                    # Projektart 2: Endnutzer-Doku (mkdocs-material)
│   ├── mkdocs.yml
│   └── docs/                  # install.md, usage.md, configuration.md, troubleshooting.md
│
└── (frontend/)                # Projektart 3: erst bei Bedarf (separates SPA)
```

**Begründungen:**
- Top-Level `backend/` statt `apps/backend/` — bei wenigen Projektarten unnötige Verschachtelung.
- `src`-Layout — verhindert versehentliche Imports aus dem Arbeitsverzeichnis, sauber paketierbar.
- Templates/static unter `web/` — funktional Teil des Backends, kein eigenes Build-Tooling.
- `frontend/` erst bei Bedarf (YAGNI) — das MVP braucht ihn nicht.
- `Dockerfile.backend` bündelt Python **und** eine Temurin-17-JRE (headless) — OpenDataLoader
  benötigt eine JVM; Details beim Packaging-Meilenstein.

---

## 3. Komponenten

Ein FastAPI-Monolith in einem Container. Intern einzeln testbare Module mit klaren Grenzen.

```
Watcher ──► Queue ──► Extractor ─────► Analyzer ──► SuggestionEngine
(watchdog)  (in-mem)   (OpenDataLoader   (Regeln)     (Pattern+Regel)
                       → Document)
                                                       │
ConfigStore (YAML) ◄── alle Module lesen Config        ▼
                                              Web-UI (Jinja2+HTMX)
                                                       │ Bestätigung
                                                       ▼
                                              Processor (Copy + Original-Handling)
```

| Modul | Verantwortung | Hängt ab von |
|---|---|---|
| `watcher` | Watchfolder beobachten (watchdog + initialer Scan beim Start), neue PDFs melden | config (Pfade) |
| `queue` | In-memory-Register der zu prüfenden Dokumente (Status `pending`/`error`) | — |
| `extractor` | OpenDataLoader-Adapter: PDF → strukturiertes `Document` (JVM-`convert` in Temp-Verzeichnis, JSON zurücklesen, **Temp sofort löschen**); erkennt „kein Text-Element" → Fehler | OpenDataLoader (JVM) |
| `analyzer` | **alle** Datumskandidaten (Regex über die Block-Texte, mit **strukturgestütztem** Kontext/Label), Absender/Typ/Keywords (Regelabgleich), Beschreibungsvorschlag | config (Regeln) |
| `suggestion` | Kandidaten + Naming-Pattern → finaler Dateinamen-Vorschlag + Zielordner-Vorschlag | config |
| `config` | YAML laden/validieren/speichern | Dateisystem |
| `web` | Jinja2+HTMX: Queue-Liste, Review-View, Config-Verwaltung | queue, suggestion, processor, config |
| `processor` | Bei Bestätigung: Copy an Zielordner, Original gemäß Config behandeln | config |

**Kern-Designregel:** `analyzer` und `suggestion` kennen weder Dateisystem noch Web noch die JVM —
reine Funktionen `Document + Config → Vorschlag`. Der einzige Ort mit Dateisystem + JVM ist
`extractor`. Dadurch sind die fehleranfälligsten Teile isoliert und ohne PDF/JVM testbar
(Hand-`Document`-Fixtures).

### 3.1 Dokumentmodell (`Document` / `Block`)

OpenDataLoader liefert die **Rohzutaten**: Textinhalte **und** Layout-Struktur. Es erkennt
**keine** Datumsangaben, Absender oder Dokumenttypen — diese fachliche Erkennung bleibt
vollständig in `analyzer` (deterministisch, KI-frei). Der `extractor` normalisiert ODLs JSON in
ein schlankes, projekteigenes Modell, damit der `analyzer` saubere, dokumentierte Eingaben
bekommt (kein Streuen von ODL-Stringkeys wie `"bounding box"` durch das kritischste Modul):

```python
@dataclass(frozen=True)
class Block:
    kind: Literal["heading", "paragraph", "table", "list", "caption"]
    text: str                      # Plaintext des Blocks
    page: int
    bbox: tuple[float, float, float, float]   # (links, unten, rechts, oben), PDF-Punkte
    level: int | None = None       # nur bei heading: Hierarchieebene
    cells: list[list[str]] | None = None      # nur bei table: Zeilen × Spalten

@dataclass(frozen=True)
class Document:
    blocks: list[Block]            # in korrigierter Lesereihenfolge (ODL XY-Cut++)
```

**Bewusst kein Abstraktions-/Austauschlayer:** Das Modell existiert für saubere Eingaben und
Testbarkeit, nicht um OpenDataLoader theoretisch ersetzbar zu machen — ODL ist eine erstklassige,
gesetzte Abhängigkeit (YAGNI gegen spekulative Austauschbarkeit).

---

## 4. Datenfluss & Zustandsmodell

### 4.1 Datenfluss pro PDF

```
Watchfolder
  │ watcher: live über watchdog-Events; initialer Scan nur beim Start
  ▼
queue: Eintrag "pending" (in-memory)
  ▼
extractor: OpenDataLoader (JVM) → Document; Temp-JSON sofort gelöscht
  ├─ kein Text-Element / korrupt / reiner Scan ohne Textebene ──► error/, Status "error"
  ▼
analyzer: Datumskandidaten (strukturgestütztes Label), Absender, Typ, Keywords, Beschreibung
  ▼
suggestion: Pattern + Regeln → Dateinamen-Vorschlag + Zielordner-Vorschlag
  ▼
Web-UI: erscheint in Queue-Liste; Nutzer öffnet Review-View,
        prüft/korrigiert Felder, wählt Zielordner, sieht finalen Namen
  ▼
[optional] Zusammenfassung (summary_mode: always | on_conflict | never)
  │ Nutzer bestätigt
  ▼
processor: Copy an gewählte Zielordner
  ├─ Namenskonflikt im Ziel ──► Nutzer entscheidet (kein Auto-Suffix)
  ▼
Original im Watchfolder gemäß original_handling behandeln (move/delete/keep)
  ▼
queue: Eintrag entfernt
```

### 4.2 Zustandsmodell — bewusst zustandsarm

- **Pending-Dokumente & Analyseergebnisse leben rein in-memory** (im `queue`-Register).
  Weder Original, Volltext, Vorschläge noch Historie werden auf Platte geschrieben.
- **Quelle der Wahrheit ist der Watchfolder selbst.** Im Normalbetrieb erkennt der `watcher`
  neue Dateien **live über watchdog-Events** — der Container läuft durch, kein manueller
  Neustart nötig. Der initiale Scan beim Start ist nur der Wiederaufbau-Sonderfall
  (was lag schon da / was ist von vor einem Neustart übrig).
- **In-Bearbeitung-Korrekturen** leben im Browser/Request bis zur Bestätigung. Kein
  serverseitiger Entwurf-Speicher.
- **Idempotenz:** Doppelte Erkennung (Event + Scan) wird über den Dateipfad dedupliziert.
- **Konsequenz (gewollt):** Der Watchfolder ist Eingang *und* Arbeitsvorrat. Ein PDF
  verschwindet erst nach bestätigter Verarbeitung oder Verschieben nach `error/`. Ein
  unbestätigtes PDF taucht nach einem Neustart wieder in der Queue auf.

### 4.3 Umgang mit mehreren Datumsangaben (Kernanforderung)

Dokumente enthalten häufig mehrere Datumsangaben (Rechnungs-, Leistungs-, Fälligkeitsdatum,
Zahlungsziel, Erstellungsdatum, Zeiträume). Die Wahl des falschen Datums ist das Hauptrisiko
des Produkts (Vision 17.1). Daraus folgt eine harte Anforderung an `analyzer`, `suggestion`
und die Web-UI:

- **`analyzer` erkennt Datumsangaben selbstständig** über eine eingebaute Erkennung gängiger
  Formate (z. B. `TT.MM.JJJJ`, `JJJJ-MM-TT`, `T. Monat JJJJ`, zwei-/vierstellige Jahre). Diese
  Erkennung funktioniert **ohne jede Konfiguration** — der Nutzer muss keinen Regex eingeben.
- **`analyzer` sammelt ALLE Datumskandidaten**, nicht nur einen. Jeder Kandidat trägt:
  - das normalisierte Datum (`date_format`-konform),
  - den rohen Treffer-Text aus dem PDF,
  - soweit ableitbar ein Label/Kontext (z. B. „Rechnungsdatum", „fällig am"), **strukturgestützt**
    aus dem `Document`: bei einem Treffer in einer Tabellenzelle die Kopf-/Nachbarzelle derselben
    Zeile, sonst der Text links davor im selben Block bzw. die zugehörige Überschrift. ODLs
    korrigierte Lesereihenfolge verhindert dabei das falsche Zusammenziehen von Label und Datum
    über Spaltengrenzen hinweg (typisch bei mehrspaltigen Rechnungen).
- **Optionaler dedizierter Matcher:** Für Sonderfälle, in denen die eingebaute Erkennung nicht
  greift, kann in der Config ein eigener Datums-Regex mit Label hinterlegt werden
  (`date_patterns`, siehe §5). Diese ergänzen die eingebauten Formate additiv; sie sind
  **optional** und keine Voraussetzung für die Datumserkennung.
- **Die Kandidatenliste wird unverändert bis in die UI durchgereicht.** `suggestion` darf
  einen Kandidaten als vorausgewählt markieren (per Regel `preferred_date` oder Heuristik),
  aber **niemals** Kandidaten entfernen, zusammenfassen oder intransparent eines festlegen.
- **Die Review-View zeigt alle Kandidaten als auswählbare Liste** (z. B. Radio-Buttons), jeweils
  mit normalisiertem Datum und Kontext. Der Nutzer wählt genau das Datum für den Dateinamen.
  Eine Vorauswahl ist erlaubt, der Wechsel auf jeden anderen Kandidaten ist jederzeit möglich.
- **Kein Kandidat gefunden:** Die UI bietet eine manuelle Datumseingabe an.
- **Testabdeckung (verbindlich):** `analyzer`-Tests müssen Dokumente mit *mehreren* Datumsangaben
  abdecken und sicherstellen, dass alle gefunden, korrekt normalisiert und (wo möglich) gelabelt
  werden — sowie dass `preferred_date`/Heuristik nur die Vorauswahl beeinflusst, nie die Menge.

Dies ist eine zentrale Produktanforderung, kein Komfortmerkmal.

---

## 5. Konfiguration (`config.yaml`)

Die einzige dauerhafte Datenhaltung. Liegt im gemounteten Config-Volume.

```yaml
paths:
  watchfolder: /data/inbox
  error_folder: /data/error
  processed_folder: /data/processed   # optional, nur bei original_handling: move

original_handling: move        # move | delete | keep
summary_mode: on_conflict      # always | on_conflict | never

default_pattern: "{date}__{sender}_{doctype}_{description}"
date_format: "%Y-%m-%d"

# Optional: zusätzliche Datums-Matcher für Sonderfälle.
# Die eingebaute Datumserkennung läuft immer und braucht KEINE Konfiguration.
# Einträge hier ERGÄNZEN die eingebauten Formate (additiv), ersetzen sie nicht.
# Die erste Capture-Group liefert den Datumswert; label erscheint als Kontext in der UI
# und ist über rules[].apply.preferred_date referenzierbar.
date_patterns:
  - label: leistungsdatum
    regex: 'Leistungsdatum:\s*(\d{2}\.\d{2}\.\d{4})'

targets:
  - name: Finanzen
    path: /targets/finanzen
    default: false
  - name: Versicherungen
    path: /targets/versicherungen
    default: false

patterns:
  - name: standard
    template: "{date}__{sender}_{doctype}_{description}"

rules:
  - name: Stromrechnung Stadtwerke
    match:                       # alle Bedingungen müssen passen
      sender_contains: "Stadtwerke"
      keywords_any: ["Stromabschlag", "Abschlag"]
    apply:
      sender: "Stadtwerke"
      doctype: "Rechnung"
      description: "Stromabschlag"
      pattern: standard
      preferred_date: rechnungsdatum   # bevorzugtes Datumsfeld
      targets: ["Finanzen"]
```

**Designentscheidungen:**
- **Regeln sind geordnet, erste Übereinstimmung gewinnt** — deterministisch & nachvollziehbar (6.2).
- **`apply` setzt nur Vorschläge** — der Nutzer bleibt in der Bestätigungsschleife (8.2);
  eine Regel automatisiert nichts durch.
- **`preferred_date`** adressiert das Hauptrisiko „falsches Datum" (17.1): die Regel
  **wählt lediglich einen der erkannten Datumskandidaten vor**. Sie ersetzt oder verbirgt die
  übrigen Kandidaten nicht — alle bleiben in der UI auswählbar (siehe §4.3). Greift keine Regel,
  darf eine Heuristik vorauswählen; auch dann bleiben alle Kandidaten sichtbar.
- **`date_patterns` ist optional.** Die Datumserkennung funktioniert ohne diesen Block; er
  ergänzt nur Sonderfälle. Ungültige Regex werden beim Laden mit klarer Meldung abgewiesen,
  ohne die eingebaute Erkennung zu beeinträchtigen.
- **Beim Start validiert `config`** die Datei (Pflichtpfade existieren, Pattern-Platzhalter
  bekannt) und bricht mit klarer Fehlermeldung ab, statt halb zu starten.

---

## 6. Fehlerbehandlung (klärt Vision 18.6)

Ziel: Fehler sichtbar machen, **ohne** eine fachliche Verarbeitungshistorie aufzubauen (Prinzip 11).

| Fehlerart | Behandlung | Persistenz |
|---|---|---|
| **Unlesbares/korruptes PDF, kein Text** (inkl. reiner Scan ohne Textebene — kein OCR im MVP) | Datei → `error/`-Ordner; Queue-Eintrag Status `error` mit Kurzgrund | Nur die Datei in `error/` — keine DB, kein Historien-Log |
| **Technischer Laufzeitfehler** (Copy schlägt fehl, Zielpfad weg, Permission) | nach `stdout` loggen (Container-Logs); in der UI als **transienter** Fehler am Queue-Eintrag | in-memory + Container-Log, keine fachliche Historie |
| **Config-Fehler** (ungültige YAML, fehlender Pfad) | Beim Start: klare Meldung + Abbruch. Zur Laufzeit nach Edit: Validierungsfehler in der UI, alte Config bleibt aktiv | keine |

**Abgrenzung:**
- Container-Logs (stdout) sind Betriebs-/Debug-Ausgaben, **keine** produktseitige Dokumenthistorie.
- Die UI zeigt Fehler **transient** (verschwinden bei Neustart/Rescan), da der Zustand aus dem
  Watchfolder neu abgeleitet wird.
- Der `error/`-Ordner ist die einzige dauerhafte Fehlerspur — eine Datei am Rand des Workflows,
  kein Protokoll.

---

## 7. Teststrategie

> „Pipeline" bezeichnet hier ausschließlich den internen Verarbeitungsfluss, **nicht** CI/CD.

- **Unit-Tests (uv + pytest)**, Schwerpunkt auf den reinen, fehleranfälligen Modulen:
  - `analyzer` — Datumskandidaten (mehrere Formate/Arten, Risiko 17.1), strukturgestützte
    Label-Zuordnung, Absender-/Typ-/Keyword-Abgleich; Eingaben sind **hand­gebaute `Document`-Fixtures**
    (kein PDF, keine JVM im Unit-Test)
  - `suggestion` — Pattern-Rendering, Regelpriorität (erste Übereinstimmung), `preferred_date`, finaler Name
  - `config` — YAML laden/validieren, Fehlerfälle (ungültig, fehlende Pfade)
  - `processor` — Copy + Original-Handling (move/delete/keep) gegen Temp-Verzeichnisse; Namenskonflikt
  - `extractor` — Text-PDF → `Document` (Mapping aus ODL-JSON), „kein Text-Element" → Fehlerpfad,
    Temp-Aufräumen (kleine Fixture-PDFs, echter ODL/JVM-Lauf — als langsamer Integrationszweig
    markiert)
- **Integrationstest des Verarbeitungsflusses:** Fixture-PDF in Temp-Watchfolder → erkannt →
  analysiert → Vorschlag korrekt → simulierte Bestätigung → landet im Zielordner, Original behandelt.
- **UI-Tests mit Playwright (Skill):** Queue-Liste zeigt pending PDF, Review-View rendert
  Felder/Vorschlag, Bestätigung löst Verarbeitung aus, transiente Fehleranzeige.
- **Datensparsamkeit verifizieren:** Test, der sicherstellt, dass nach Verarbeitung nichts außer
  Config + Dateien an Zielorten persistiert (kein Volltext/keine Historie auf Platte).

---

## 8. Dokumentation

| Ort | Zielgruppe | Inhalt |
|---|---|---|
| `docs/vision.md`, `docs/superpowers/specs/` | intern / Devs | Produktvision, Architektur, Entscheidungen |
| `docs/ui.md` | UI-Devs | eine einzige, rein sprachliche Beschreibung der Oberfläche (was der Nutzer sieht, Funktionen, Seitenführung); entsteht mit der UI-Implementierung |
| `mkdocs/` | **Endnutzer** | Installations- & Benutzungs-Doku auf Basis von **squidfunk/mkdocs-material**: Installation (Docker Compose, Volumes/Mounts, Watchfolder/Zielordner/Error-Ordner), Bedienung (Review-Workflow), Konfiguration (`config.yaml`), Betrieb & typische Fehlerfälle. Gebaut/serviert via `Dockerfile.mkdocs`. `README.md` verweist hierauf |

---

## 9. Präzisierung des Erfolgskriteriums (Vision 16.1)

Rein regelbasiert ist ein vollständiger Vorschlag (Datum + Absender + Typ + sinnvolle
Beschreibung) beim **Erstkontakt** mit einem unbekannten Absender kaum erreichbar — die
Beschreibung ist deterministisch am schwersten (Risiko 17.2).

**Präzisierung:** Erfolg bemisst sich am *brauchbaren Startpunkt plus schneller Bestätigung*,
nicht am perfekten Erstvorschlag. Das Tool füllt vor, was es sicher weiß (Datum, ggf. Typ),
der Nutzer ergänzt den Rest in unter 15 Sekunden. Die 80-%-Schwelle bezieht sich auf diesen
brauchbaren Startpunkt. Vision-Abschnitt 16 wird entsprechend angepasst.

---

## 10. Scope-Ausschlüsse dieses Designs

Zusätzlich zu den Nicht-Zielen der Vision (Abschnitt 15):

- **Kein CI/CD, keine Build-Automation, kein Deployment, kein Registry/Publishing.**
  Verantwortung liegt beim Betreiber. Das Design liefert nur `Dockerfile.<subprojekt>` und
  `docker-compose.yml` als Artefakte, nicht deren Automatisierung.
- **Keine Hash-Duplikaterkennung** im MVP (siehe Abschnitt 1).
- **Keine KI-Anbindung** im MVP — nur als gekapselter, später implementierbarer
  Erweiterungspunkt im `analyzer`/`suggestion`-Design vorgesehen.
- **Nur OpenDataLoaders lokaler Strukturmodus.** Der Hybrid-Modus (OCR für reine Scans,
  KI-Tabellen-/Bildverständnis über ein zusätzliches lokales KI-Backend) ist bewusst **nicht** im
  MVP — er bräche die Nicht-Ziele OCR (15, Vision 18.4) und KI (6.2, Vision 18.3) und zöge einen
  zweiten Dienst in den Betrieb. Bleibt späterer Erweiterungspunkt.
- **JVM-Abhängigkeit bewusst akzeptiert.** Eine Temurin-17-JRE im Backend-Image und die
  JVM-Startzeit pro PDF (~1–2 s) sind der bewusst eingegangene Preis für die strukturierte
  Analysegrundlage; für ein 1-Nutzer-Heimtool unkritisch.

---

## 11. Auswirkungen auf die Vision

Folgende Vision-Abschnitte sind durch dieses Design zu aktualisieren:

- **9.8 / 18.5 (Hash-Duplikaterkennung):** aus MVP gestrichen.
- **16.1 (Erfolgskriterium):** präzisiert (Abschnitt 9 hier).
- **18.1 (Login):** entschieden — kein Login.
- **18.2 (Konfigurationsspeicher):** entschieden — YAML.
- **18.3 (KI):** entschieden — MVP rein regelbasiert, KI als Erweiterungspunkt.
- **18.6 (technische Fehlerausgaben):** entschieden — siehe Abschnitt 6.
