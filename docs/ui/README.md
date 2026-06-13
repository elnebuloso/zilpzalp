# ZilpZalp — Oberfläche (UI)

Sprachliche, seitenweise Beschreibung der Web-Oberfläche. Sie entsteht mit der UI-Implementierung
(Meilenstein 5) und ist die Referenz für UI-Devs. Architektur und Begründungen stehen im
[Web-UI-Spec](../superpowers/specs/2026-06-14-0108-zilpzalp-web-ui.md) und im
[MVP Design-Spec](../superpowers/specs/2026-06-13-1435-zilpzalp-mvp-design.md).

## Grundlagen

- **Server-rendered, Jinja2 + HTMX**, kein Build-Step. CSS/HTMX liegen vendored unter
  `backend/src/zilpzalp/web/static/`.
- **Ein Layout** (`base.html`) mit Kopf-Navigation: **Warteschlange** · **Konfiguration**.
- **Zustandsarm:** Die Oberfläche leitet ihren Inhalt aus dem In-Memory-Register (`queue`) ab.
  Nichts wird zusätzlich persistiert; nach einem Neustart wird die Liste aus dem Watchfolder
  neu aufgebaut.
- **Sprache:** Deutsch.

## Seitenindex

| Seite | Datei | Route |
|---|---|---|
| Warteschlange | [queue.md](queue.md) | `GET /`, Fragment `GET /queue` |
| Review-View | [review-view.md](review-view.md) | `GET /review/{id}` (+ `/preview`, `/confirm`) |
| Zusammenfassung | [summary.md](summary.md) | nach `POST /review/{id}/confirm`, `POST /review/{id}/execute` |
| Konfiguration | [config.md](config.md) | `GET /config`, `POST /config` |

## Gemeinsame Muster

- **Status-Badges:** `○ wartet` (pending), `◐ Analyse` (analyzing), `● bereit` (ready),
  `✕ Fehler` (error).
- **Transiente Banner:** Erfolge und Laufzeitfehler erscheinen oberhalb des Inhalts und sind
  flüchtig — sie verschwinden bei Neustart/Rescan (Design-Spec §6). Es gibt keine
  Verarbeitungshistorie.
- **HTMX-Polling:** Das Warteschlangen-Fragment lädt sich alle 2 Sekunden selbst neu, damit der
  Übergang `Analyse → bereit` ohne manuellen Reload sichtbar wird.
- **Bestätigungsschleife:** Keine Aktion verändert Dateien ohne ausdrückliche Bestätigung des
  Nutzers (Design-Spec §5/§8.2).
</content>
