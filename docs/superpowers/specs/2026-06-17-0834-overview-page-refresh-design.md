# Overview-Seite — Refresh (Design)

Backlog-Bündel: **#80, #85, #88, #96** (siehe [docs/backlog.md](../../backlog.md)).

**Art:** Feature — ein zusammenhängendes Release. Vier UI-Ideen, die alle auf der
Übersichtsseite (`/`) zusammenkommen, plus die von ihr geteilten Partials/Strings.
Keine neuen Backend-Subsysteme, keine neuen Persistenz- oder Worker-Logik.

## Ziel

Die Übersichtsseite konsistenter und vorhersehbarer machen: gleichmäßiges
Counter-Layout, Betriebsangaben sinnvoll platziert, Statusanzeige analog zur
Queue, jüngste Dokumente zuerst und ein aufgeräumtes Upload-Feedback.

## Scope

Betroffene Dateien:

- [backend/src/zilpzalp/web/static/styles.css](../../../backend/src/zilpzalp/web/static/styles.css) — Counter-Grid
- [backend/src/zilpzalp/web/templates/overview.html](../../../backend/src/zilpzalp/web/templates/overview.html) — Karten-Umbau
- [backend/src/zilpzalp/web/templates/_overview.html](../../../backend/src/zilpzalp/web/templates/_overview.html) — Status-Badge
- [backend/src/zilpzalp/web/routes.py](../../../backend/src/zilpzalp/web/routes.py) — Sortier-Helfer
- [backend/src/zilpzalp/web/static/app.js](../../../backend/src/zilpzalp/web/static/app.js) — Upload-Liste pro Batch leeren
- [backend/src/zilpzalp/web/locales/de.json](../../../backend/src/zilpzalp/web/locales/de.json), [en.json](../../../backend/src/zilpzalp/web/locales/en.json) — Label

Ausdrücklich **nicht** Teil dieses Features (eigenständige Backlog-Einträge):
Fehler-Ordner-Ansicht, Trash leeren, Manueller Re-Analyse-Button, Extrahierte
Inhalte in der Review-Preview, Review-Workflow-Punkte, Doku/GitHub-Links,
Config-Seite.

## Detail

### 1. Counter-Boxen gleichmäßig (#85)

`styles.css` definiert `.counters` heute mit
`grid-template-columns: repeat(auto-fit, minmax(150px, 1fr))`. Bei vier Boxen
ergibt das je nach Viewport 3 nebeneinander und die 4. darunter (3+1).

**Änderung:** Basisregel auf `grid-template-columns: repeat(4, 1fr)`. Die bereits
vorhandene Schmal-Regel (`.counters { grid-template-columns: repeat(2, 1fr); }`
im Media-Query) liefert weiterhin 2×2. Ergebnis: breit 1×4, schmal 2×2.
Reine CSS-Änderung.

### 2. Betriebsangaben unter „Hochladen" (#88)

`.dash-cols` ist bereits ein 2-Spalten-Grid (`grid-template-columns: 1.5fr 1fr`),
enthält in `overview.html` aber **drei** Grid-Kinder (Counter/Liste-Stack,
Upload-Karte, Ops-Karte). Dadurch landet die Ops-Karte in der linken Spalte unter
dem Stack statt rechts unter dem Upload.

**Änderung:** In `overview.html` die Upload-Karte und die Betriebsangaben-Karte in
einen gemeinsamen `<div class="dash-stack">` (zweites Grid-Kind) zusammenfassen.
Danach: links Counter + „Jüngste Dokumente", rechts Upload **über**
Betriebsangaben. Kein CSS nötig — nur Markup-Umhängen. Die Betriebsangaben-Daten
bleiben unverändert (gleiche `info-grid`-Zellen).

### 3. Status „bereit" auf der Übersicht (#80)

In `_overview.html` zeigt die „Jüngste Dokumente"-Liste für `ready`-Einträge nur
den Review-Button, kein Status-Badge — anders als `_queue_list.html`, wo jede
Zeile ein Badge trägt.

**Änderung:** In der Overview-Liste das Status-Badge auch für `ready` rendern,
zusätzlich zum Review-Button (Markup analog `_queue_list.html`, Klasse
`STATUS_BADGE['ready']` = `b-ready`, Label `status.ready` = „bereit"/„ready"). Die
übrigen Status (pending/analyzing/error) zeigen weiterhin ihr Badge.

### 4. Liste & Upload-Feedback (#96)

**a) Jüngste zuerst sortieren.** `Queue.list()` liefert Einfügereihenfolge
(Scan-Reihenfolge, neue Watch-Events hinten). Gewünscht ist absteigend nach Alter
(jüngste zuerst).

Gewählter Ansatz (Variante A): Sortierung **nach Datei-mtime absteigend an der
Render-Stelle**, kein Model-Änderung. Ein Helfer (z. B. `_sorted(entries)`) sortiert
`queue.list()` nach `entry.path.stat().st_mtime` absteigend; fehlt die Datei
(stat-Fehler), wandert der Eintrag ans Ende (mtime 0). Eingesetzt in `_recent`
**und** in den Queue-Routen (`queue_page`, `queue_partial`), damit Übersicht und
Queue konsistent dieselbe Reihenfolge zeigen. N ist klein, der `stat()` je Poll
(alle 2 s) ist vernachlässigbar.

Verworfen (Variante B): `added_at`-Zeitstempel auf `QueueEntry`. Stabilere
Entdeckungs-Reihenfolge, aber Model-Änderung plus Zeitquelle — und „nach Alter"
meint die Datei, nicht den Entdeckungszeitpunkt.

**b) Upload-Liste pro Batch leeren.** In `app.js` akkumuliert `#upload-list` heute
Zeilen über alle Uploads einer Session und wird nie geleert.

**Änderung:** In `enqueue()` zu Beginn jeder neuen Auswahl/Drop `#upload-list`
leeren (`list.replaceChildren()` o. ä.), bevor die Zeilen der aktuellen Charge
angelegt werden. Dann zeigt die Liste nur die gerade hochgeladenen Dateien
(inkl. Fehlerzeilen der aktuellen Charge). Rein client-seitig.

**c) „fertig" → „hochgeladen".** Der Status „fertig" ist irreführend (die Datei ist
hochgeladen, die Verarbeitung läuft noch).

**Änderung:** `upload.status.done` in beiden Katalogen: `de` „fertig" →
„hochgeladen", `en` „done" → „uploaded". Keine weitere Code-Änderung (app.js liest
das Label bereits aus `data-label-done`).

## Tests

- **Sortier-Helfer (Unit):** Einträge mit unterschiedlichen mtimes → Reihenfolge
  jüngste zuerst; fehlende Datei landet hinten.
- **Overview-Partial (Route):** `ready`-Eintrag → `/partials/overview` enthält das
  Badge `b-ready` zusätzlich zum Review-Link.
- **Queue-Konsistenz (Route):** `/partials/queue` respektiert dieselbe
  mtime-Sortierung.
- **i18n:** bestehende Katalog-Tests bleiben grün (nur ein Wert geändert).
- **Upload-Batch-Clear:** client-seitig (JS), kein Backend-Test — manuell
  verifizieren (zwei Uploads nacheinander: zweite Charge ersetzt die erste Liste).

## Akzeptanzkriterien

1. Vier Counter liegen breit 1×4, schmal 2×2 — nie 3+1.
2. Betriebsangaben erscheinen rechts unter „PDF hochladen", nicht in der linken
   Spalte.
3. `ready`-Dokumente zeigen auf der Übersicht ein „bereit"-Badge **und** den
   Review-Button.
4. Übersicht und Queue listen Dokumente jüngste-zuerst.
5. Ein erneuter Upload zeigt nur die Dateien der aktuellen Charge.
6. Der Upload-Status heißt „hochgeladen" / „uploaded".
