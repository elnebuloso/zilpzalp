# Konfiguration

Die Datei `config.yaml` (gemountet unter `/config/config.yaml`) ist die **einzige
dauerhafte Einstellung**. Sie wird beim Start validiert: Fehlt ein Pflichtpfad oder
enthält ein Namensmuster einen unbekannten Platzhalter, startet ZilpZalp **nicht**,
sondern meldet den Fehler klar.

!!! info "Pfade sind Container-Pfade"
    Alle Pfade in `config.yaml` beziehen sich auf das **Innere des Containers**
    (`/data/inbox`, `/targets/…`). Wie diese auf Host-Ordner abgebildet werden, legt
    `docker-compose.yml` fest (siehe [Installation](installation.md)).

## Vollständiges Beispiel

```yaml
paths:
  watchfolder: /data/inbox
  error_folder: /data/error
  processed_folder: /data/processed   # nur nötig bei original_handling: move

original_handling: move        # move | delete | keep
summary_mode: on_conflict      # always | on_conflict | never

default_pattern: "{date}__{sender}_{doctype}_{description}"
date_format: "%Y-%m-%d"

# Optional: zusätzliche Datums-Matcher für Sonderfälle.
# Die eingebaute Datumserkennung läuft IMMER und braucht KEINE Konfiguration.
date_patterns:
  - label: leistungsdatum
    regex: 'Leistungsdatum:\s*(\d{2}\.\d{2}\.\d{4})'

targets:
  - name: Finanzen
    path: /targets/finanzen
    default: false

patterns:
  - name: standard
    template: "{date}__{sender}_{doctype}_{description}"

rules:
  - name: Stromrechnung Stadtwerke
    match:
      sender_contains: "Stadtwerke"
      keywords_any: ["Stromabschlag", "Abschlag"]
    apply:
      sender: "Stadtwerke"
      doctype: "Rechnung"
      description: "Stromabschlag"
      pattern: standard
      preferred_date: rechnungsdatum
      targets: ["Finanzen"]
```

## Felder

### `paths`

| Schlüssel | Pflicht | Bedeutung |
|---|---|---|
| `watchfolder` | ja | überwachter Eingangsordner |
| `error_folder` | ja | Ablage für unlesbare PDFs |
| `processed_folder` | nur bei `original_handling: move` | Ablage verarbeiteter Originale |

### `original_handling`

Was nach erfolgreicher Ablage mit dem Original im Watchfolder geschieht:

- `move` — in `processed_folder` verschieben
- `delete` — löschen
- `keep` — im Watchfolder belassen

### `summary_mode`

Wann vor der Bestätigung eine Zusammenfassung erscheint:
`always` (immer), `on_conflict` (nur bei Namenskonflikt), `never` (nie).

### `date_format`

Format des Datums im Dateinamen, als Python-`strftime`-Muster
(z. B. `%Y-%m-%d` → `2026-06-14`).

### Namensmuster (`default_pattern`, `patterns`)

Platzhalter im Muster: `{date}`, `{sender}`, `{doctype}`, `{description}`.
`patterns` benennt wiederverwendbare Muster, auf die Regeln per Name verweisen.

### `date_patterns` (optional)

Zusätzliche Datums-Matcher für Sonderfälle. Die erste Capture-Group liefert den
Datumswert, `label` erscheint als Kontext in der Oberfläche. Diese Einträge
**ergänzen** die eingebauten Formate (additiv) — sie ersetzen sie nicht. Ungültige
reguläre Ausdrücke werden beim Laden mit klarer Meldung abgewiesen.

### `targets`

Liste der Zielordner mit `name`, `path` und `default` (Vorauswahl in der Oberfläche).

### `rules`

Geordnete Liste — **die erste passende Regel gewinnt**. Eine Regel **automatisiert
nichts durch**: `apply` setzt nur Vorschläge, die du in der Oberfläche bestätigst oder
änderst.

- `match` — alle Bedingungen müssen zutreffen (z. B. `sender_contains`, `keywords_any`).
- `apply` — vorzuschlagende Werte (`sender`, `doctype`, `description`, `pattern`,
  `targets`) sowie `preferred_date`: **wählt** einen der erkannten Datumskandidaten
  **vor**, verbirgt die übrigen aber nie.
