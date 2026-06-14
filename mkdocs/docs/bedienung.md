# Bedienung

Die gesamte Bedienung läuft über die Weboberfläche unter
<http://localhost:8000>.

## Der Review-Workflow

1. **PDF ablegen.** Lege eine PDF-Datei in den Watchfolder (`./data/inbox`).
   ZilpZalp erkennt sie automatisch und analysiert sie.

2. **Queue ansehen.** Die Startseite zeigt alle wartenden Dokumente. Jeder Eintrag
   steht auf `pending` (bereit zur Prüfung) oder `error` (siehe
   [Fehlerbehebung](fehlerbehebung.md)).

3. **Review öffnen.** Ein Klick auf einen Eintrag öffnet die Detailansicht mit dem
   Vorschlag:
    - **Datum:** alle erkannten Datumskandidaten als Auswahl, jeweils mit Kontext
      (z. B. „Rechnungsdatum"). Eine Vorauswahl kann gesetzt sein; du kannst jederzeit
      einen anderen Kandidaten wählen. Wurde kein Datum gefunden, gibst du es manuell ein.
    - **Absender, Typ, Beschreibung:** vorbefüllt, soweit ZilpZalp sie sicher ableiten
      konnte — frei korrigierbar.
    - **Zielordner:** Auswahl aus den konfigurierten Zielen.
    - **Finaler Dateiname:** wird live aus dem Namensmuster gebildet.

4. **Bestätigen.** Je nach Einstellung `summary_mode` erscheint vorher eine
   Zusammenfassung. Nach der Bestätigung kopiert ZilpZalp die Datei in den Zielordner.

5. **Original.** Das Original im Watchfolder wird gemäß `original_handling` behandelt
   (verschoben, gelöscht oder belassen). Der Eintrag verschwindet aus der Queue.

## Namenskonflikte

Existiert im Zielordner bereits eine Datei mit demselben Namen, **entscheidest du** —
ZilpZalp hängt **kein** automatisches Suffix an und überschreibt nichts ungefragt.

## Konfiguration in der Oberfläche

Die Seite **Konfiguration** zeigt die aktuelle `config.yaml` und erlaubt Änderungen.
Ungültige Eingaben werden mit einer Fehlermeldung abgewiesen; die bisherige Konfiguration
bleibt dann aktiv. Inhaltliche Referenz: [Konfiguration](konfiguration.md).
