# ZilpZalp — Oberfläche (UI)

Sprachliche, seitenweise Beschreibung der Web-Oberfläche. Sie entsteht mit der UI-Implementierung
(Meilenstein 5) und ist die Referenz für UI-Devs. Architektur und Begründungen stehen im
[Web-UI-Spec](../superpowers/specs/2026-06-14-0108-zilpzalp-web-ui.md) und im
[MVP Design-Spec](../superpowers/specs/2026-06-13-1435-zilpzalp-mvp-design.md).

## Grundlagen

- **Server-rendered, Jinja2 + HTMX**, kein Build-Step. CSS/HTMX liegen vendored unter
  `backend/src/zilpzalp/web/static/`.
- **App-Shell** (`base.html`): durchgängige Kopfleiste mit Produktname, Navigation
  **Übersicht** · **Warteschlange** · **Konfiguration** (aktiver Punkt hervorgehoben) und
  Theme-Umschalter. Alle Seiten erweitern diese Shell.
- **Design-System** (`style.css`): abgestimmte Typografie, Abstände, Farbpalette und Status-Farben;
  wiederkehrende Komponenten (Karten, Tabellen, Buttons, Felder, Badges, Banner) als CSS-Klassen.
  Visuelle Grundrichtung: ruhiges, modernes Utility.
- **Zustandsarm:** Die Oberfläche leitet ihren Inhalt aus dem In-Memory-Register (`queue`) und der
  Config ab. Nichts wird zusätzlich persistiert; nach einem Neustart wird die Liste aus dem
  Watchfolder neu aufgebaut.
- **Sprache:** Deutsch.

## Seitenindex

| Seite | Datei | Route |
|---|---|---|
| Dashboard / Startseite | [dashboard.md](dashboard.md) | `GET /`, Fragment `GET /dashboard/cards` |
| Warteschlange | [queue.md](queue.md) | `GET /queue`, Fragment `GET /queue/rows` |
| Review-View | [review-view.md](review-view.md) | `GET /review/{id}` (+ `/preview`, `/confirm`) |
| Zusammenfassung | [summary.md](summary.md) | nach `POST /review/{id}/confirm`, `POST /review/{id}/execute` |
| Konfiguration | [config.md](config.md) | `GET /config`, `POST /config` |

## Gemeinsame Muster

- **Status-Badges:** `○ wartet` (pending), `◐ Analyse` (analyzing), `● bereit` (ready),
  `✕ Fehler` (error) — überall in derselben Farbe/Form.
- **Transiente Banner & Toasts:** Erfolge und Laufzeitfehler erscheinen oberhalb des Inhalts und
  sind flüchtig — sie verschwinden bei Neustart/Rescan (Design-Spec §6). Es gibt keine
  Verarbeitungshistorie.
- **HTMX-Polling:** Dynamische Fragmente (Dashboard-Kacheln, Warteschlangen-Liste) laden sich alle
  2 Sekunden selbst neu, damit der Übergang `Analyse → bereit` ohne manuellen Reload sichtbar wird.
- **Theme (hell/dunkel):** Farben über CSS-Variablen; Standard folgt `prefers-color-scheme`. Der
  Umschalter in der Kopfleiste setzt `data-theme` auf `<html>` und merkt die Wahl in `localStorage`
  (wenige Zeilen Vanilla-JS). Keine serverseitige Theme-Speicherung.
- **Zustände:** Lade-/Analyse-Indikator, leere Zustände, deaktivierte Buttons (z. B. bei Konflikt),
  klar getrennte primäre vs. sekundäre Aktionen.
- **Bestätigungsschleife:** Keine Aktion verändert Dateien ohne ausdrückliche Bestätigung des
  Nutzers (Design-Spec §5/§8.2).
