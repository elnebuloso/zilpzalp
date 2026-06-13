# Warteschlange

Route: `GET /` (Vollseite) · Listen-Fragment: `GET /queue`

Die Startseite. Zeigt alle Dokumente, die der Watchfolder aktuell enthält und die noch nicht
bestätigt verarbeitet wurden — der Watchfolder ist Eingang **und** Arbeitsvorrat (Design-Spec §4.2).

```
ZilpZalp                                   [ Warteschlange ]  [ Konfiguration ]
──────────────────────────────────────────────────────────────────────────
Warteschlange (4)
┌────────────────────┬───────────┬───────────────────────────┬──────────┐
│ Datei              │ Status    │ Vorschau                  │ Aktion   │
├────────────────────┼───────────┼───────────────────────────┼──────────┤
│ rechnung_jan.pdf   │ ● bereit  │ 2026-01-15 · Stadtwerke · │ Prüfen → │
│                    │           │ Rechnung                  │          │
│ scan_002.pdf       │ ◐ Analyse │ —                         │          │
│ unbekannt.pdf      │ ○ wartet  │ —                         │          │
│ kaputt.pdf         │ ✕ Fehler  │ Kein Text im PDF gefunden │          │
└────────────────────┴───────────┴───────────────────────────┴──────────┘
                                          (aktualisiert sich automatisch)
```

## Spalten

- **Datei** — Dateiname des Originals im Watchfolder.
- **Status** — Badge gemäß `QueueEntry.status`:
  - `○ wartet` — in der Worker-Schlange, Analyse noch nicht begonnen.
  - `◐ Analyse` — Worker extrahiert/analysiert gerade.
  - `● bereit` — Analyse fertig, ein Vorschlag (`Suggestion`) liegt vor.
  - `✕ Fehler` — Extraktion fehlgeschlagen; die Datei wurde nach `error/` verschoben.
- **Vorschau** — nur bei `bereit`: vorausgewähltes Datum · Absender · Typ aus dem Vorschlag.
  Bei `Fehler`: Kurzgrund (`error_reason`). Sonst `—`.
- **Aktion** — „Prüfen →“ (Link zur Review-View) nur bei `bereit`.

## Verhalten

- **Auto-Aktualisierung:** Das `<tbody>`-Fragment pollt `GET /queue` alle 2 s (HTMX
  `hx-trigger="every 2s"`), sodass `wartet → Analyse → bereit` ohne Reload erscheint.
- **Transiente Banner** oberhalb der Tabelle: Erfolgsmeldung nach einer Verarbeitung
  („`datei.pdf` verarbeitet“) oder transienter Laufzeitfehler an einem Eintrag (Design-Spec §6).
- **Leerer Zustand:** „Keine Dokumente in der Warteschlange.“
- **Fehlereinträge** sind informativ; die Datei liegt bereits in `error/`. Keine Aktion in der UI;
  ein Rescan/Neustart baut die Liste neu auf.
</content>
