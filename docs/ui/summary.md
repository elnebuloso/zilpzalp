# Zusammenfassung & Bestätigung

Routen: `POST /review/{id}/confirm` (Entscheidung) · `POST /review/{id}/execute` (Ausführung)

Der letzte Schritt vor dem Schreiben von Dateien. Ob die Zusammenfassung erscheint, hängt von
`summary_mode` und einem Namenskonflikt ab.

```
Zusammenfassung — bitte bestätigen
──────────────────────────────────────────────────────────────────────────
Quelle:      rechnung_jan.pdf
Neuer Name:  [ 2026-01-15__Stadtwerke_Rechnung_Stromabschlag.pdf ]
Kopieren nach:
   ✓ /targets/finanzen/2026-01-15__…​.pdf
   ✕ /targets/versicherungen/2026-01-15__…​.pdf  — existiert bereits! (Konflikt)
Original:    wird nach /data/processed verschoben (move)

  ⚠ Namenskonflikt — bitte Namen ändern.
                       [ Abbrechen ]   [ Ausführen ]
```

## Wann erscheint die Zusammenfassung?

`/confirm` berechnet den finalen Namen und die Zielpfade und führt eine **Dry-Run-Konfliktprüfung**
mit denselben Vorbedingungen wie `processor.process` aus (Zieldatei vorhanden? bei
`original_handling: move` auch das `processed`-Ziel?).

- `summary_mode: always` → Zusammenfassung immer.
- `summary_mode: on_conflict` → Zusammenfassung nur bei Konflikt.
- `summary_mode: never` → keine Zusammenfassung, sofern kein Konflikt vorliegt.
- **Ein Konflikt erzwingt die Zusammenfassung immer**, unabhängig vom Modus.

Liegt kein Konflikt vor und der Modus verlangt keine Zusammenfassung, führt `/confirm` direkt aus.

## Inhalt

- **Quelle** — Originaldatei.
- **Neuer Name** — editierbares Feld; hier löst der Nutzer einen Konflikt durch Umbenennen.
- **Kopieren nach** — je Zielordner der volle Zielpfad; Konflikte rot markiert (`✕ … existiert bereits!`).
- **Original** — die Aktion gemäß `original_handling` (verschieben/löschen/behalten).

## Konfliktbehandlung (Design-Spec §4.1)

- **Kein Auto-Suffix.** Bei Konflikt ist „Ausführen“ gesperrt, bis der Nutzer den Namen ändert oder
  abbricht.
- „Ausführen“ postet an `/execute` → `processor.process(...)`.
  - **Erfolg:** Eintrag aus der Warteschlange entfernt, zurück zur Liste mit Erfolgs-Banner.
  - **`FileConflictError`** (Race seit der Vorprüfung): zurück zur Zusammenfassung mit
    Konfliktmarkierung.
  - **Sonstiger Laufzeitfehler** (Zielpfad weg, Permission): nach `stdout` geloggt, an der Liste als
    transienter Fehler angezeigt (Design-Spec §6).
- **Abbrechen** führt zurück zur Review-View, ohne etwas zu schreiben.
