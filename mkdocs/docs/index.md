# ZilpZalp

ZilpZalp ist eine **halb-automatische Dokumentenablage** für den Eigenbetrieb im
Heimnetz. Es beobachtet einen Ordner, liest eingehende PDFs und schlägt einen
sauberen Dateinamen aus Datum, Absender und Dokumenttyp vor — **du prüfst, bestätigst,
fertig**. Lokal, ohne Cloud.

## Kerngedanke

- **Mensch in der Schleife:** ZilpZalp füllt vor, was es sicher weiß. Die endgültige
  Entscheidung triffst immer du.
- **Mehrere Datumsangaben sichtbar:** Ein Dokument enthält oft mehrere Daten
  (Rechnungs-, Leistungs-, Fälligkeitsdatum). ZilpZalp zeigt **alle** erkannten
  Kandidaten zur Auswahl an, statt im Hintergrund eines festzulegen.
- **Datensparsam:** Es entsteht keine Historie und keine Datenbank. Quelle der Wahrheit
  ist der überwachte Ordner selbst; einzige dauerhafte Einstellung ist `config.yaml`.

## Wie es funktioniert

```
Watchfolder → Analyse (Datum/Absender/Typ) → Vorschlag → Review im Browser
→ Bestätigung → Kopie in den Zielordner → Original verschoben/gelöscht/behalten
```

## Loslegen

- [Installation](installation.md) — Einrichtung mit Docker Compose
- [Bedienung](bedienung.md) — der Review-Workflow im Browser
- [Konfiguration](konfiguration.md) — `config.yaml` im Detail
- [Fehlerbehebung](fehlerbehebung.md) — Betrieb und typische Fehlerfälle

!!! warning "Kein Zugriffsschutz"
    ZilpZalp hat **kein Login**. Es ist für den Betrieb im vertrauenswürdigen Heimnetz
    gedacht. Mache die Weboberfläche nicht ungeschützt aus dem Internet erreichbar.
