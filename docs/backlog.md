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

## Ideen / später

- **CI-Pipeline (GitHub Actions):** Docker-Image bauen und in den eigenen
  Docker-Hub-Namespace releasen, mit Semantic Versioning (Tags → semver,
  z. B. `vX.Y.Z`). Löst den durchgängigen MVP-Scope-Ausschluss „kein CI/CD"
  ([mvp/roadmap.md](mvp/roadmap.md)) bewusst als Post-MVP-Schritt ab.
- **Mehrsprachigkeit der UI:** Oberflächentexte aus den Templates lösen und über
  einen Übersetzungs-/i18n-Mechanismus bereitstellen (zunächst Deutsch, weitere
  Sprachen ergänzbar), inkl. Sprachauswahl.
- **Helm Chart:** Kubernetes-Deployment per Helm Chart vereinfachen (Backend +
  Doku-Container, Konfiguration und Volumes als Chart-Werte parametrisierbar).
