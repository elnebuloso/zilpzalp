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
| 6 | Feature | **Overview-Seite — Refresh** — Counter-Layout (1×4/2×2), Betriebsangaben unter „Hochladen", Status „bereit" in der Liste, jüngste-zuerst-Sortierung + Upload-Feedback (Details: [superpowers/specs/2026-06-17-0834-overview-page-refresh-design.md](superpowers/specs/2026-06-17-0834-overview-page-refresh-design.md)) | ✅ | `809343f` |
| 7 | Feature | **Review-Seite — Optimierung** — nächstes bereites Dokument nach Bestätigen/Überspringen, kein vorgewähltes Datum, Original-Dateiname hervorgehoben + im neuen Tab öffnen, Extraktions-Tabs (Markdown/HTML/JSON, inline ohne Overlay) (Details: [superpowers/specs/2026-06-17-0955-review-page-optimization-design.md](superpowers/specs/2026-06-17-0955-review-page-optimization-design.md)) | ✅ | `e081ffd` |

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
- **„Trash leeren"-Aktion in der UI:** Für den `original_handling: trash`-Modus
  einen Weg schaffen, `/data/trash` über die Oberfläche zu leeren, statt nur im
  Dateisystem (siehe [superpowers/specs/2026-06-17-0009-config-improvements-and-extraction-cache-design.md](superpowers/specs/2026-06-17-0009-config-improvements-and-extraction-cache-design.md)).
- **Cache-Wiederverwendung über Neustart:** Beim Start vorhandenen Extraktions-Cache
  nutzen und `extract` überspringen, mit Invalidierung über Dateigröße + mtime.
  Aktuell wird beim Start bewusst neu extrahiert (keine Invalidierungslogik).
- **Manueller Re-Analyse-Button:** Global und/oder pro Eintrag, als Ergänzung zur
  automatischen Re-Analyse nach Config-Änderung.
- **Screenshots in der mkdocs-Doku via Playwright:** Die mkdocs-Dokumentation mit
  Screenshots der Weboberfläche anreichern, automatisiert über Playwright erzeugt,
  damit sie bei UI-Änderungen reproduzierbar aktualisiert werden können.
- **Betriebsangaben auf der Konfigurationsseite:** Dieselben Betriebsangaben auch auf
  der Seite „Konfiguration" in der rechten Spalte anzeigen, damit man die geparsten
  Daten direkt sieht.
- **Verlinkung zur Dokumentation + GitHub:** Links zur Doku
  (<https://elnebuloso.github.io/zilpzalp/>) und zum GitHub-Repo in der UI einbauen —
  z. B. im Header, ggf. als GitHub-Icon.
- **TestClient-Deprecation beheben:** Die Tests lösen vorbestehende
  httpx/starlette-`TestClient`-Deprecation-Warnings aus (per-request `cookies=`,
  `Using httpx with starlette.testclient is deprecated`). Harmlos heute, werden aber
  mit einem künftigen httpx-Major zu Fehlern — Testaufbau migrieren, damit die
  pytest-Ausgabe wieder warnungsfrei ist.
- **Release-Reihenfolge optimieren — kein Release ohne Docker-Artefakt:** In
  [.github/workflows/release.yml](../../.github/workflows/release.yml) erstellt der
  `release-please`-Job zuerst GitHub-Release **und** Tag; `test` und `build-push`
  laufen erst danach. Schlägt der Docker-Build/-Push (oder der Test) fehl, existiert
  ein veröffentlichtes Release `vX.Y.Z` ohne passendes Image
  `elnebuloso/zilpzalp-backend:vX.Y.Z` — inkonsistenter Zustand. Reihenfolge umdrehen:
  Tests + Docker-Push zuerst, GitHub-Release/Tag erst danach und nur, wenn das Artefakt
  bereitliegt. Umsetzungsideen: release-please nur Release-PR/Manifest verwalten lassen
  (`skip-github-release`) und das GitHub-Release in einem Folgeschritt nach erfolgreichem
  `build-push` erzeugen, oder Tests/Build bereits auf der Release-PR vor dem Merge fahren.
- **HTML-Extraktion am echten PDF verifizieren:** Der Test-Job in der CI mockt
  `opendataloader_pdf.convert`, daher verlässt sich der HTML-Tab des Extraktions-Drawers
  (seit v1.3.0, Umsetzung #7) auf die Annahme, dass die echte Bibliothek HTML ausgibt.
  Fehlt das `.html`-Artefakt, scheitert es weich („Nicht verfügbar"). Beim ersten Lauf
  des Images gegen ein echtes PDF prüfen, ob der HTML-Tab gefüllt wird; falls nicht,
  `"html"` aus der `format`-Liste in [extractor.py](../../backend/src/zilpzalp/extractor.py)
  entfernen und den HTML-Tab ausbauen.
- **Aktionsmodell überarbeiten — Skip ≠ Löschen, eigener Entfernen-Button:** Die
  Bedeutung der Aktionen klarer trennen. Gewünschtes Verhalten:
  - **Überspringen (Review):** springt nur weiter und **belässt das Dokument in der
    Warteschlange** — kein Disponieren des Originals, **kein** `hx-confirm`-Alert.
  - **`original_handling: delete|trash`** wirkt **nur bei bestätigten, umbenannten/abgelegten**
    Dateien (also beim Confirm/Ablegen), nicht beim Überspringen.
  - **Entfernen/Löschen-Button** in der **Warteschlange** und in der **„jüngste
    Dokumente"-Ansicht** (Übersicht): entfernt das Dokument bewusst und disponiert das
    Original **je nach Einstellung** (`trash` oder `delete`).

  Heute falsch: In der Warteschlange ([_queue_list.html](../../backend/src/zilpzalp/web/templates/_queue_list.html))
  steht ein **Überspringen**-Button, der über `skip_document`
  ([web/routes.py](../../backend/src/zilpzalp/web/routes.py)) `skip()`
  ([processor.py](../../backend/src/zilpzalp/processor.py)) das Original gemäß
  `original_handling` disponiert (bei `delete` löscht, mit `hx-confirm`). Dort gehört
  stattdessen ein **Entfernen/Löschen**-Button hin; die Übersicht
  ([_overview.html](../../backend/src/zilpzalp/web/templates/_overview.html)) hat heute gar
  keine Entfernen-Aktion. **Offene Frage:** Wenn ein übersprungenes Dokument in der Queue
  bleibt und die Datei im Watchfolder liegt — wie wird unnötige Dauer-Re-Analyse vermieden
  (Status bleibt einfach „ready", kein Re-Enqueue)?
