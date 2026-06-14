# Dashboard / Startseite

Route: `GET /` (Vollseite) · Fragment: `GET /dashboard/cards`

Die Einstiegsseite. Sie gibt dem Tool ein vollwertiges Gesicht und zeigt auf einen Blick, was
ansteht — ohne neuen Zustand: alles ist abgeleitete Anzeige des In-Memory-Registers und der Config.

```
ZilpZalp                          [ Übersicht ]  [ Warteschlange ]  [ Konfiguration ]   🌓
──────────────────────────────────────────────────────────────────────────────────
Übersicht
┌─────────────┬─────────────┬─────────────┬─────────────┐
│ ● bereit  2 │ ◐ Analyse 1 │ ○ wartet  1 │ ✕ Fehler  1 │
└─────────────┴─────────────┴─────────────┴─────────────┘
Betrieb
  Watchfolder:   /data/inbox            Original-Handling: move
  Config:        /config/config.yaml    Zusammenfassung:   on_conflict
  Ziele: 2 · Regeln: 1 · Muster: 1
──────────────────────────────────────────────────────────────────────────────────
Zuletzt in der Warteschlange                              [ Alle anzeigen → ]
┌────────────────────┬───────────┬───────────────────────────┬──────────┐
│ rechnung_jan.pdf   │ ● bereit  │ 2026-01-15 · Stadtwerke    │ Prüfen → │
│ scan_002.pdf       │ ◐ Analyse │ —                          │          │
│ kaputt.pdf         │ ✕ Fehler  │ Kein Text im PDF gefunden  │          │
└────────────────────┴───────────┴───────────────────────────┴──────────┘
        (Kacheln und Vorschau aktualisieren sich automatisch)
```

## Bereiche

- **Status-Kacheln** — Zähler je `QueueEntry.status` (`bereit` / `Analyse` / `wartet` / `Fehler`),
  berechnet aus `queue.list()`. Jede Kachel nutzt die zugehörige Status-Farbe.
- **Betrieb** — read-only Anzeige aus `app.state.config`: Watchfolder-Pfad, Config-Pfad,
  `original_handling`, `summary_mode`, Anzahl Ziele/Regeln/Muster. Orientierung, keine Bearbeitung
  (die läuft über [Konfiguration](config.md)).
- **Queue-Vorschau** — die jüngsten Einträge als kompakte Tabelle mit „Prüfen →“ (bei `ready`) und
  „Alle anzeigen →“ zur [Warteschlange](queue.md).

## Verhalten

- **Auto-Aktualisierung:** Kacheln und Vorschau liegen im Fragment `GET /dashboard/cards` und pollen
  sich per HTMX alle 2 s selbst neu, sodass Statuswechsel ohne Reload sichtbar werden.
- **Leerer Zustand:** Sind keine Dokumente vorhanden, zeigen die Kacheln `0` und die Vorschau den
  Hinweis „Keine Dokumente in der Warteschlange.“
