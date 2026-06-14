# ZilpZalp — Backlog

Tracking der Weiterentwicklung nach der MVP-Bauphase. Die abgeschlossene
MVP-Roadmap bleibt unter [mvp/roadmap.md](mvp/roadmap.md) als Verlauf erhalten.

**Pflege-Regel:** Neue Vorhaben sammeln sich unten unter „Ideen / später".
Sobald ein Vorhaben angegangen wird, wandert es als neue Zeile in die Tabelle
„Umsetzung" und verschwindet aus der Ideenliste. Die Reihenfolge der Zeilen
entspricht der Umsetzungsreihenfolge. Bei Abschluss: Status auf ✅ setzen und
den finalen (Merge-)Commit-SHA eintragen.

**Status:** 🚧 in Arbeit · ✅ erledigt

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
