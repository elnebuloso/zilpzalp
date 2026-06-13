# Review-View

Route: `GET /review/{id}` · Live-Vorschau: `POST /review/{id}/preview` · Bestätigen:
`POST /review/{id}/confirm`

Die Kernseite: Der Nutzer prüft den Vorschlag, wählt das richtige Datum und bestätigt. `{id}` ist
das stabile Token des `QueueEntry`. Nur für `bereit`-Einträge erreichbar.

```
← Zurück zur Warteschlange
Prüfen: rechnung_jan.pdf
──────────────────────────────────────────────────────────────────────────
Datum (für den Dateinamen wählen)
  (•) 2026-01-15   Rechnungsdatum     [roh: 15.01.2026]
  ( ) 2026-02-14   fällig am          [roh: 14.02.2026]
  ( ) 2026-01-01   Leistungszeitraum  [roh: 01.01.2026]
  ( ) manuell:     [ 2026-__-__ ]
Absender       [ Stadtwerke             ]
Typ            [ Rechnung               ]
Beschreibung   [ Stromabschlag          ]
Muster         [ standard ▾ ]
Zielordner
  [x] Finanzen        /targets/finanzen
  [ ] Versicherungen  /targets/versicherungen
──────────────────────────────────────────────────────────────────────────
Finaler Name:  2026-01-15__Stadtwerke_Rechnung_Stromabschlag.pdf
                                                      [ Bestätigen ]
```

## Datumsauswahl (Kernanforderung, Design-Spec §4.3)

- **Alle** erkannten Datumskandidaten erscheinen als Radio-Liste, jeder mit normalisiertem Datum,
  Label/Kontext und Rohtext. Die UI entfernt, verdichtet oder verbirgt **keine** Kandidaten.
- **Vorauswahl:** Der von `suggestion.preselected_date_index` markierte Kandidat ist gewählt — der
  Wechsel auf jeden anderen ist jederzeit möglich. Die Vorauswahl beeinflusst nie die Menge.
- **Option „manuell“:** ein Radio mit Datumseingabe. Wird auch genutzt, wenn **kein** Kandidat
  gefunden wurde (dann ist die manuelle Eingabe die einzige Datumsoption).

## Felder

- **Absender / Typ / Beschreibung** — Textfelder, vorbefüllt aus dem Vorschlag; frei editierbar.
- **Muster** — Auswahl aus `config.patterns` (plus Default-Muster). Bestimmt die Namensvorlage.
- **Zielordner** — Checkboxen aus `config.targets`; vorgewählt sind die aus `suggestion.target_paths`.
  Mindestens einer muss gewählt sein (sonst lehnt der Processor ab).

## Live-Namensvorschau

Bei jeder Änderung (Datum, Feld, Muster) postet HTMX das Formular an `/review/{id}/preview`. Der
Server rendert den Dateinamen aus gewähltem Datum + Feldern + Muster und liefert nur das
Vorschau-Fragment zurück („Finaler Name: …“). Das Rendering passiert serverseitig — kein
Client-Templating, kein Build-Step.

## Bestätigen

„Bestätigen“ postet das vollständige Formular an `/review/{id}/confirm`. Je nach `summary_mode`
und Konfliktlage folgt die [Zusammenfassung](summary.md) oder die direkte Ausführung.
</content>
