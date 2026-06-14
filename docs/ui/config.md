# Konfiguration

Routen: `GET /config` (Editor) · `POST /config` (Validieren + Speichern)

Bearbeitung der einzigen dauerhaften Datenhaltung, der `config.yaml` (Design-Spec §5). Im MVP ein
**Roh-YAML-Editor** — transparent, deckt alle Felder ab und nutzt dieselbe Validierung wie der Start.

```
Konfiguration (config.yaml)
──────────────────────────────────────────────────────────────────────────
┌────────────────────────────────────────────────────────────────────────┐
│ paths:                                                                  │
│   watchfolder: /data/inbox                                              │
│   error_folder: /data/error                                             │
│   processed_folder: /data/processed                                     │
│ original_handling: move                                                 │
│ summary_mode: on_conflict                                               │
│ …                                                                       │
└────────────────────────────────────────────────────────────────────────┘
                                                            [ Speichern ]
```

## Verhalten

- **GET** zeigt den aktuellen `config.yaml`-Rohtext unverändert in einer Textarea.
- **Speichern (POST)** ruft `save_config`: Der Text wird in eine Temp-Datei geschrieben und über die
  bestehende `load_config`-Logik validiert (Pflichtpfade existieren, Pattern-Platzhalter bekannt,
  Datums-Regex kompilieren, `date_format` gültig …).
  - **Erfolg:** Datei wird atomar ersetzt, `app.state.config` neu geladen, Erfolgs-Banner.
  - **Fehler:** Die Validierungsmeldungen erscheinen über dem Editor; die **alte Konfiguration
    bleibt aktiv**, die Datei wird nicht verändert (Design-Spec §6).

```
  ✕ Ungültig:
    - paths.watchfolder '/data/inbox' existiert nicht oder ist kein Verzeichnis
    (alte Konfiguration bleibt aktiv)
```

## Wirkung von Änderungen

Eine neue Config gilt für **neu hinzukommende** Dokumente. Bereits analysierte Warteschlangen-
Einträge behalten ihren Vorschlag (zustandsarm, Design-Spec §4.2); sie werden nicht automatisch neu
analysiert. Wer eine Neubewertung will, legt das PDF erneut in den Watchfolder.
