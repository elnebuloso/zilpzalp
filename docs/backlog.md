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

## Ideen / später

- **CI-Pipeline (GitHub Actions):** Docker-Image bauen und in den eigenen
  Docker-Hub-Namespace releasen, mit Semantic Versioning (Tags → semver,
  z. B. `vX.Y.Z`). Löst den durchgängigen MVP-Scope-Ausschluss „kein CI/CD"
  ([mvp/roadmap.md](mvp/roadmap.md)) bewusst als Post-MVP-Schritt ab.
- **Helm Chart:** Kubernetes-Deployment per Helm Chart vereinfachen (Backend +
  Doku-Container, Konfiguration und Volumes als Chart-Werte parametrisierbar).
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
