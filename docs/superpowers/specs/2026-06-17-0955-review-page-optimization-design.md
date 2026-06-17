# Review-Seite — Optimierung (Design)

Datum: 2026-06-17 · Status: Entwurf

Bündelt drei Backlog-Ideen rund um die Review-Seite in ein Vorhaben. Alle
Änderungen leben auf der Review-Seite bzw. ihren Backend-Routen.

## Ziel

1. **Nahtlos weiterarbeiten + Fehlbestätigung verhindern** — nach „Bestätigen"
   und „Überspringen" direkt das nächste bereite Dokument vorlegen; kein Datum
   vorausgewählt, „Bestätigen" bleibt inaktiv bis aktiv eines gewählt wurde.
2. **Original-Dateiname hervorheben + PDF öffnen** — den ursprünglichen
   Dateinamen optisch hervorheben und per Klick das Original-PDF in einem neuen
   Tab öffnen.
3. **Extrahierte Inhalte anzeigen** — die gecachten Extraktions-Artefakte
   (Markdown, HTML, JSON) in einem Seiten-Drawer lesbar machen.

## Annahmen

- `opendataloader-pdf` (v2) unterstützt `html` als Ausgabeformat. **In der
  Umsetzung verifizieren.** Falls nicht: HTML-Tab und HTML-Cache entfallen,
  Markdown + JSON bleiben. Das Paket ist in der aktuellen Dev-Umgebung nicht
  installiert, daher hier nicht direkt geprüft.
- Beim Start wird ohnehin neu extrahiert (keine Invalidierungslogik), sodass
  nach Deploy für jedes bereite Dokument ein HTML-Cache vorliegt. Fehlende
  Cache-Dateien (Altbestand) werden trotzdem robust als „nicht verfügbar"
  behandelt.

## Abschnitt 1 — Flow: nahtlos weiterarbeiten + Fehlbestätigung verhindern

### Nahtlos weiterarbeiten

Nach erfolgreichem „Ausführen" und nach „Überspringen" wird statt zur `/queue`
direkt das **nächste bereite Dokument** vorgelegt: `HX-Redirect` auf
`/review/{next.id}`.

- „Nächstes" = erstes Entry mit `status == "ready"` und gesetzter `suggestion`
  in der bestehenden newest-first-Sortierung (`_by_mtime_desc`). Das gerade
  verarbeitete Entry ist zu dem Zeitpunkt bereits aus der Queue entfernt.
- Gibt es kein bereites Dokument mehr → `HX-Redirect` auf
  `/queue?flash=…&kind=ok` wie heute.
- Der „abgelegt"/„übersprungen"-Toast wird über den `flash`-Query-Param
  transportiert und auf der Review-Seite angezeigt (das Base-Template rendert
  Toasts unabhängig von der Seite).
- Eine zentrale Helferfunktion (z. B. `_next_ready(queue)`) liefert das nächste
  Entry; `_execute` (deckt Direkt-Ausführen **und** Modal-Ausführen ab) und
  `skip_document` nutzen sie für ihr Redirect-Ziel.

### Fehlbestätigung verhindern

Kein Datumskandidat ist mehr vorausgewählt:

- `review_page` übergibt keinen aktiven Vorauswahl-Index (kein Kandidat erhält
  die `sel`-Klasse).
- Das versteckte `date_value`/`data-selected-date` startet leer.
- Das bestehende JS deaktiviert „Bestätigen", solange kein Datum gesetzt ist
  (`var ok = !!date && targetCount() > 0`, `static/app.js`). Das greift damit
  sofort; der Hinweis-Text (`#confirm-hint`) zeigt „Datum wählen".
- Sender, Doctype, Beschreibung und Zielordner bleiben wie bisher vorbefüllt —
  nur das Datum muss aktiv gewählt werden.
- Kein Datumskandidat im Vorschlag → wie bisher Auswahl per manuellem Datum.

## Abschnitt 2 — Original-Dateiname hervorheben + PDF öffnen

Der Original-Dateiname (heute kleiner Mono-Untertitel in `review.html`) wird zu
einem **hervorgehobenen, klickbaren Element**: Akzentfarbe + Datei-/Extern-Icon.
Klick öffnet das Original-PDF in einem **neuen Tab** (`target="_blank"`,
`rel="noopener"`).

Neue Route:

```
GET /documents/{entry_id}/pdf
→ FileResponse(entry.path, media_type="application/pdf")
  Content-Disposition: inline
```

- Validierung wie bei den übrigen Routen: Entry existiert, sonst Redirect/404.
- Erfüllt zugleich Backlog-Item B („Dateiname hervorheben") und den Wunsch
  „PDF im Browser öffnen".

## Abschnitt 3 — Extraktions-Drawer (Markdown / HTML / JSON)

Ein Button **„Extrahierten Inhalt ansehen"** öffnet ein von rechts
einschiebendes Overlay-Panel (Drawer). Inhalt: drei Tabs plus PDF-Link.

- **Tab-Reihenfolge & Default: Markdown → HTML → JSON.** Markdown ist die
  lesbarste Wiedergabe und damit Default-Tab.
- **Markdown** — Cache-`.md` roh in scrollbarem `<pre>` (Monospace).
- **HTML** — Cache-`.html` in einem **isolierten `<iframe>`** (`sandbox`,
  `srcdoc` oder eigene Route als `src`), damit fremdes Extraktions-HTML weder
  Layout noch JS der App beeinflusst.
- **JSON** — Cache-`.json` pretty-printed in `<pre>`.
- **PDF öffnen** — Link auf die `/pdf`-Route, neuer Tab.

Laden: **lazy** — jeder Tab holt seinen Inhalt beim ersten Öffnen per
htmx-`GET /documents/{entry_id}/extract/{kind}` mit `kind ∈ {markdown, html,
json}`. Fehlt die jeweilige Cache-Datei, antwortet die Route mit einem
„nicht verfügbar"-Hinweis (kein Fehler).

Der HTML-Tab nutzt für die Iframe-Quelle dieselbe Extract-Route
(`kind=html`), die bei direktem Aufruf das HTML als vollständiges Dokument mit
korrekten Headern ausliefert.

## Abschnitt 4 — Backend-Änderungen

- **Extractor** (`extractor.py`): `format=["json", "markdown", "html"]`;
  erzeugtes `*.html` analog zum `.md` nach `<stem>.html` in den Cache
  verschieben. Verifizieren, dass `html` unterstützt wird (siehe Annahmen).
- **Cache** (`cache.py`): `_html()`-Pfad ergänzen; Lese-Helfer für die
  Roh-Texte (`read_markdown`, `read_html`, `read_json_text` o. ä., je `None`
  bei fehlender Datei); `remove()` und `prune()` um `.html` erweitern.
- **Routes** (`web/routes.py`):
  - neue `GET /documents/{id}/pdf` (Inline-PDF)
  - neue `GET /documents/{id}/extract/{kind}` (Drawer-Inhalt, lazy)
  - `_execute` und `skip_document` auf „nächstes bereites Dokument" umstellen
    (gemeinsame `_next_ready`-Helferfunktion)
  - `review_page` ohne Datums-Vorauswahl
- **Templates**: `review.html` (hervorgehobener, klickbarer Original-Name;
  Drawer-Markup + Trigger; keine `sel`-Vorauswahl beim Datum); ggf. neue
  Partials für die Extract-Tabs.
- **JS/CSS** (`static/app.js`, `static/styles.css`): Drawer öffnen/schließen,
  Tab-Wechsel; Drawer- und Tab-Styles. Die Datums-/Confirm-Logik bleibt
  unverändert (greift dank fehlender Vorauswahl automatisch).
- **i18n** (`locales/de.json`, `locales/en.json`): neue Keys für Button,
  Tab-Labels, „nicht verfügbar", „PDF öffnen".

## Tests

- Cache: HTML-Roundtrip (`read_html`), `remove`/`prune` löschen auch `.html`.
- Extractor: schreibt `.html` in den Cache (nutzt vorhandene PDF-Fixture).
- Routes:
  - `/pdf` liefert das PDF inline aus; unbekanntes Entry → erwartetes Verhalten.
  - `/extract/{kind}` liefert je Art den richtigen Inhalt bzw. „nicht
    verfügbar" bei fehlender Datei.
  - confirm/execute und skip leiten auf das nächste bereite Dokument weiter;
    ohne weiteres bereites Dokument auf `/queue`.
  - `review_page` ohne Datums-Vorauswahl (kein Kandidat aktiv, `date_value`
    leer).

## Nicht im Scope

- Markdown→HTML-Rendering einer eigenen Engine (HTML kommt direkt aus der
  Extraktion).
- Cache-Wiederverwendung über Neustart / Invalidierung (eigenes Backlog-Item).
- Manueller Re-Analyse-Button (eigenes Backlog-Item).
