# ZilpZalp — Backlog

Tracking der Weiterentwicklung nach der MVP-Bauphase. Die abgeschlossene
MVP-Roadmap bleibt unter [mvp/roadmap.md](mvp/roadmap.md) als Verlauf erhalten.

## Pflege-Regel

So wird dieses Dokument gepflegt (gilt unabhängig von Tooling oder Gedächtnis):

1. **Ideen sammeln:** Neue, noch nicht angegangene Vorhaben kommen als Stichpunkt
   unter „## Ideen / später".
2. **Angehen = in die Tabelle:** Sobald ein Vorhaben begonnen wird, wandert es als
   neue Zeile ans Ende der Tabelle „## Umsetzung" und verschwindet aus der Ideenliste.
3. **Reihenfolge:** Die Zeilenreihenfolge (Spalte `#`, fortlaufend) entspricht der
   Umsetzungsreihenfolge.
4. **Abschluss:** Bei Fertigstellung Status auf ✅ setzen und in der Spalte `Commit`
   den finalen Commit-SHA eintragen — bei einem zusammengeführten Branch den
   **Merge-Commit** (analog zur [Roadmap](mvp/roadmap.md)).

**Spalten der Tabelle:**

- `#` — fortlaufende Nummer = Umsetzungsreihenfolge
- `Art` — `Meilenstein` (großes, mehrteiliges Vorhaben), `Feinschliff` (kleine
  Politur) oder `Feature` (eigenständige Funktion)
- `Thema` — kurze Beschreibung, ggf. mit Link auf Detail-Dokument
- `Status` — 🚧 in Arbeit · ✅ erledigt
- `Commit` — finaler (Merge-)Commit-SHA, der das Vorhaben abschließt; `—` solange offen

## Umsetzung

| # | Art | Thema | Status | Commit |
|---|-----|-------|--------|--------|
| 1 | Meilenstein | **MVP** — Backend-Fundament, Analyse-Kern, Dateioperationen, Ingestion, Web-UI, Doku + Packaging (Details: [mvp/roadmap.md](mvp/roadmap.md)) | ✅ | `eb516c5` |
| 2 | Feinschliff | Demo-/Dummie-Texte aus UI entfernen (Untertitel & Helfertexte knapp & funktional) | ✅ | `65983fa` |
| 3 | Feature | **Mehrsprachigkeit der UI (DE/EN)** — Texte aus Templates/Code lösen, i18n-Mechanismus + Sprachumschalter (Details: [superpowers/specs/2026-06-14-2212-ui-i18n-design.md](superpowers/specs/2026-06-14-2212-ui-i18n-design.md)) | ✅ | `bc3f3c0` |
| 4 | Feature | **Health-Endpunkte für Kubernetes-Probes** — `/healthz/startup`, `/healthz/ready`, `/healthz/live` mit Komponenten-Status; `/health` entfällt (Details: [superpowers/specs/2026-06-14-2348-health-probes-design.md](superpowers/specs/2026-06-14-2348-health-probes-design.md)) | ✅ | `7630595` |
| 5 | Feature | **CI-Release-Pipeline (GitHub Actions)** — Auto-Semver aus Conventional Commits via `release-please`, Backend-Image nach Docker Hub `elnebuloso/zilpzalp-backend:vX.Y.Z` (Details: [superpowers/specs/2026-06-15-0025-ci-release-pipeline-design.md](superpowers/specs/2026-06-15-0025-ci-release-pipeline-design.md)) | ✅ | `75a6378` |

## Ideen / später

- **Helm Chart:** Kubernetes-Deployment des **Backends** per Helm Chart (Doku wird
  bewusst **nicht** ausgerollt). Entscheidungen aus dem Brainstorming:
  - **Distribution:** OCI-Artefakt auf **GHCR** (`oci://ghcr.io/elnebuloso/...`),
    Package muss einmalig manuell auf **public** gestellt werden (GHCR-Default ist privat).
  - **Volumes:** flexibler Passthrough — `volumes`/`volumeMounts` (bzw. `existingClaim`)
    in `values.yaml`, Chart bleibt unopinionated über das Storage-Backend (NFS,
    bestehende PVC, hostPath). Passt zum Watchfolder-Modell (`inbox`/`error`/`processed`/`targets`).
  - **Config:** `config.yaml` per Default aus `values.yaml` in eine ConfigMap gerendert
    und nach `/config/config.yaml` gemountet; `existingConfigMap` als Override.
  - **Release/Versionierung:** Chart als **zweites release-please-Paket** unter eigenem
    Pfad (z. B. `chart/`) mit eigenem SemVer + Changelog. `backend` bleibt prefixlos
    (`v1.4.0`), Chart bekommt Component-Prefix (`chart-v0.1.0`) via per-Paket
    `include-component-in-tag`.
  - **Offene Frage (vor Umsetzung klären):** `appVersion`-Strategie —
    **A)** automatisch an Backend-Releases koppeln (release-please bumpt `appVersion`
    + Chart-Patch-Release; fummelig) vs. **B)** entkoppeln, Image-Tag über
    `values.yaml` (`image.tag`, Fallback `appVersion`) gepinnt; Releases unabhängig (einfacher).
- **Fehler-Ordner-Ansicht in der UI:** Den `error/`-Ordner in der Weboberfläche
  sichtbar machen — mit Fehlergrund je Eintrag und einer „erneut einreihen"-Aktion,
  statt nur im Dateisystem aufzulaufen.
- **Lint-Fehler in `test_i18n.py` beheben:** Ungenutzter Import `pytest`
  ([backend/tests/test_i18n.py:4](../../backend/tests/test_i18n.py#L4)) — vorbestehender
  Ruff-Fehler (F401), unabhängig vom jeweiligen Feature. Entfernen, damit
  `ruff check .` projektweit grün ist.
- **Veralteten Design-Doc korrigieren:** `docs/superpowers/specs/2026-06-14-1459-zilpzalp-web-ui.md:161`
  sagt noch „`/health` bleibt" — seit Backlog #4 überholt (`/health` entfällt, ersetzt durch
  `/healthz/*`). Historisches MVP-Dokument an die aktuelle Realität anpassen oder als überholt markieren.
- **Extrahierte Inhalte in der Review-Preview anzeigen:** Das pro Dokument gecachte
  JSON + Markdown (siehe [superpowers/specs/2026-06-17-0009-config-improvements-and-extraction-cache-design.md](superpowers/specs/2026-06-17-0009-config-improvements-and-extraction-cache-design.md))
  dem User in der Review-Ansicht lesbar machen, damit er die Analyse nachvollziehen
  kann. Fundament (persistierter Extraktions-Cache) ist mit jenem Spec gelegt.
- **„Trash leeren"-Aktion in der UI:** Für den `original_handling: trash`-Modus
  einen Weg schaffen, `/data/trash` über die Oberfläche zu leeren, statt nur im
  Dateisystem (siehe [superpowers/specs/2026-06-17-0009-config-improvements-and-extraction-cache-design.md](superpowers/specs/2026-06-17-0009-config-improvements-and-extraction-cache-design.md)).
- **Cache-Wiederverwendung über Neustart:** Beim Start vorhandenen Extraktions-Cache
  nutzen und `extract` überspringen, mit Invalidierung über Dateigröße + mtime.
  Aktuell wird beim Start bewusst neu extrahiert (keine Invalidierungslogik).
- **Manueller Re-Analyse-Button:** Global und/oder pro Eintrag, als Ergänzung zur
  automatischen Re-Analyse nach Config-Änderung.
- **Status „bereit" auf der Übersichtsseite:** Auf der Übersichtsseite fehlt der
  Status „bereit" analog zur Warteschlangenseite — dort konsistent ergänzen.
- **Screenshots in der mkdocs-Doku via Playwright:** Die mkdocs-Dokumentation mit
  Screenshots der Weboberfläche anreichern, automatisiert über Playwright erzeugt,
  damit sie bei UI-Änderungen reproduzierbar aktualisiert werden können.
- **Counter-Boxen auf der Startseite layouten:** Aktuell stehen 3 Boxen
  nebeneinander, die 4. rutscht darunter. Alle 4 sollen gleichmäßig liegen — je nach
  Viewport 1×4 (breit) bzw. 2×2 (schmaler) statt 3+1.
- **Betriebsangaben auf der Übersichtsseite:** Betriebs-/Laufzeitangaben auf der
  Übersichtsseite in der Spalte „Hochladen" unterhalb von „PDF hochladen" anzeigen.
- **Betriebsangaben auf der Konfigurationsseite:** Dieselben Betriebsangaben auch auf
  der Seite „Konfiguration" in der rechten Spalte anzeigen, damit man die geparsten
  Daten direkt sieht.
- **Verlinkung zur Dokumentation + GitHub:** Links zur Doku
  (<https://elnebuloso.github.io/zilpzalp/>) und zum GitHub-Repo in der UI einbauen —
  z. B. im Header, ggf. als GitHub-Icon.
- **Übersichtsseite — Liste & Upload-Feedback:** Mehrere zusammenhängende Punkte zur
  Dokumentenliste:
  - Neu in der Inbox gefundene Dokumente oben einsortieren, absteigend nach Alter
    (jüngste zuerst).
  - Beim Upload per UI wächst die Liste immer weiter; ein erneuter Upload zeigt nur
    die gerade hochgeladenen Files an — Verhalten klären/beheben.
  - „fertig" ist als Status irreführend — sollte „hochgeladen" heißen.
- **Review-Seite — nahtlos weiterarbeiten + Fehlbestätigung verhindern:** Nach Klick
  auf „Bestätigen" direkt das nächste Dokument vorlegen, damit man ohne Umweg
  weiterarbeiten kann. Damit man nicht stumpf/zu schnell bestätigt und versehentlich
  falsch umbenennt, sollte kein Datum vorausgewählt sein — „Bestätigen" bleibt
  inaktiv, bis aktiv ein Datum gewählt wurde.
- **TestClient-Deprecation beheben:** Die Tests lösen vorbestehende
  httpx/starlette-`TestClient`-Deprecation-Warnings aus (per-request `cookies=`,
  `Using httpx with starlette.testclient is deprecated`). Harmlos heute, werden aber
  mit einem künftigen httpx-Major zu Fehlern — Testaufbau migrieren, damit die
  pytest-Ausgabe wieder warnungsfrei ist.
