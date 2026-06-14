# ZilpZalp — Roadmap

Lebendes Tracking-Dokument für die MVP-Umsetzung. Jeder Meilenstein wird in einer
eigenen, frischen Session bearbeitet:

1. (falls nötig) **Spec** für den Meilenstein schreiben — verfeinert das master Design-Spec
2. **Plan** schreiben (bite-sized TDD-Tasks, `superpowers:writing-plans`)
3. **Umsetzen** (`superpowers:subagent-driven-development` oder `executing-plans`)
4. In dieser Roadmap als **fertig** markieren und Spec/Plan **mit Commit-SHA** verlinken

Architektur-Referenz für alle Meilensteine ist das master Design-Spec. Einzelne
Meilenstein-Specs sind optional — nur anlegen, wenn ein Meilenstein über die Architektur-
Referenz hinaus Detailentscheidungen braucht.

**Status-Legende:** 📋 geplant · ✍️ Spec in Arbeit · 📝 Plan in Arbeit · 🚧 Umsetzung · ✅ fertig

---

## Fundament-Dokumente

| Dokument | Pfad | Status | Commit |
|---|---|---|---|
| Produktvision | [docs/vision.md](vision.md) | ✅ fertig | `37a9eac` |
| MVP Design-Spec (Architektur-Referenz) | [docs/superpowers/specs/2026-06-13-1435-zilpzalp-mvp-design.md](superpowers/specs/2026-06-13-1435-zilpzalp-mvp-design.md) | ✅ fertig | `fdd181f` |

---

## Meilensteine

Reihenfolge = Bauabhängigkeit. Jeder Meilenstein liefert für sich lauffähige, testbare Software.

| # | Meilenstein | Scope | Spec | Plan | Status | Commit (fertig) |
|---|---|---|---|---|---|---|
| 1 | **Backend-Fundament + Config** | uv/pyproject/src-Layout, `config.py` (YAML laden + validieren), Startup-Validierung | — (Design-Spec §2, §5) | [Plan](superpowers/plans/2026-06-13-1506-backend-fundament-config.md) | ✅ fertig | `c6d7478` |
| 2 | **Analyse-Kern** | `extractor` (OpenDataLoader-Adapter: JVM→`Document`-Modell, Temp-Cleanup, „kein Text-Element"→Fehler), `analyzer` (**alle** Datumskandidaten mit strukturgestütztem Label, Absender/Typ/Keywords/Beschreibung), `suggestion` (Pattern+Regeln, `preferred_date`, Regelpriorität) | — (Design-Spec §3, §3.1, §4.3, §5) | [Plan](superpowers/plans/2026-06-13-1642-analyse-kern.md) | ✅ fertig | `70dc613` |
| 3 | **Dateioperationen** | `processor` (Copy an Zielordner, Original-Handling move/delete/keep, Namenskonflikt) | — (Design-Spec §4.1, §6) | [Plan](superpowers/plans/2026-06-14-0006-dateioperationen.md) | ✅ fertig | `3c6651e` |
| 4 | **Ingestion** | `watcher` (watchdog-Events + initialer Scan), `queue` (in-memory Register, Pfad-Dedup) | — (Design-Spec §4) | [Plan](superpowers/plans/2026-06-14-0038-ingestion.md) | ✅ fertig | `400e9bc` |
| 5a | **UI-Design & Beschreibung** | `docs/ui.md` (vollständige UI-Beschreibung) · Designsystem + statische HTML/CSS-Mockups je Seite (hell/dunkel) → `docs/ui/design/` | [docs/ui.md](ui.md) | [Mockups](ui/design/) | ✅ fertig | `0ffb1ad` |
| 5b | **Web-UI-Umsetzung** | FastAPI-Routen, Jinja2+HTMX, Worker + Queue-/Config-Erweiterung, Playwright-Tests. **Vorgehen: erst Design brainstormen (auf Basis von 5a), dann Umsetzungsplan, dann umsetzen** | _tbd (entsteht im 5b-Brainstorm)_ | _tbd (Plan nach Brainstorm)_ | 📋 geplant | — |
| 6 | **Endnutzer-Doku + Packaging** | `mkdocs/` (mkdocs-material), `Dockerfile.backend`, `Dockerfile.mkdocs`, `docker-compose.yml` | — (Design-Spec §2, §8) | _tbd_ | 📋 geplant | — |

> **Scope-Ausschluss (gilt durchgängig):** kein CI/CD, keine Build-Automation, kein
> Deployment, kein Registry/Publishing — Verantwortung beim Betreiber (Design-Spec §10).

---

## Vision-Anpassungen (aus Design-Spec §11)

Die folgenden Vision-Abschnitte wurden in Commit `9723008` mit den MVP-Design-Entscheidungen
synchronisiert.

| Vision-Abschnitt | Änderung | Status |
|---|---|---|
| 9.8 / 18.5 (Hash-Duplikaterkennung) | aus MVP gestrichen | ✅ fertig |
| 16.1 (Erfolgskriterium) | präzisiert: brauchbarer Startpunkt + schnelle Bestätigung | ✅ fertig |
| 18.1 (Login) | entschieden: kein Login | ✅ fertig |
| 18.2 (Konfigurationsspeicher) | entschieden: YAML | ✅ fertig |
| 18.3 (KI) | entschieden: MVP rein regelbasiert, KI als Erweiterungspunkt | ✅ fertig |
| 18.6 (technische Fehlerausgaben) | entschieden: stdout-Logs + transiente UI + `error/`-Ordner | ✅ fertig |

---

## Arbeitsweise in frischen Sessions

- **Plan schreiben:** „Schreibe den Plan für Meilenstein N aus der Roadmap." → Agent liest
  `docs/roadmap.md` + Design-Spec, schreibt `docs/superpowers/plans/YYYY-MM-DD-HHMM-<name>.md`,
  trägt den Plan-Link + Status `📝`/`🚧` in die Roadmap ein.
- **Nach Umsetzung:** Status auf `✅` setzen und Spec/Plan-Zeile mit dem finalen Commit-SHA
  ergänzen.

Eine kopierfertige Prompt-Vorlage für frische Sessions steht in der [README](../README.md).
