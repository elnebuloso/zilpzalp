# ZilpZalp — Designsystem & Mockups (Meilenstein 5a)

Statische Design-Lieferung als verbindliche Vorlage für die Umsetzung in **5b**. Reine
HTML/CSS-Artefakte, kein Backend. Im Browser öffnen: [`index.html`](index.html) (Cover mit
Seitenindex, Farb-/Typo-/Komponenten-Schau und Theme-Umschalter).

Textliche Beschreibung der Oberfläche: [`../../ui.md`](../../ui.md). Die Umsetzungs-Architektur
(Routen, Worker, Tests) wird in 5b gebrainstormt und geplant — siehe die 5b-Zeile der
[Roadmap](../../roadmap.md).

## Dateien

| Datei | Inhalt |
|---|---|
| `index.html` | Cover, Seitenindex, Designsystem-Schau |
| `dashboard.html` | Übersicht / Startseite |
| `queue.html` | Warteschlange |
| `review.html` | Prüfungsansicht (Datumswahl, Felder, Namensvorschau) |
| `summary.html` | Zusammenfassung & Bestätigung (mit Konfliktzustand) |
| `config.html` | Konfiguration (YAML-Editor, Validierungs-Banner) |
| `design-system.css` | Tokens + Komponenten (die Quelle der Wahrheit) |
| `app.js` | Theme-Umschalter (Vanilla-JS) |

## Aesthetische Richtung

Ruhiges, modernes Utility mit Charakter. Leitmotiv ist der namensgebende **Zilpzalp**
(Chiffchaff), ein kleiner olivgrüner Laubsänger → warmes „Papier" im hellen Thema, tiefes
„Waldtinten"-Grün im dunklen, ein olivgrüner Akzent. Editorial-archivarischer Eindruck durch eine
Serifen-Display-Schrift, getragen von einer humanistischen Grotesk und Monospace für Dateinamen,
Pfade und YAML.

## Designsystem (Tokens in `design-system.css`)

**Schriften**
- Display/Überschriften: **Fraunces** (Serife, charaktervoll)
- Fließtext/UI: **Hanken Grotesk** (humanistische Grotesk)
- Monospace: **IBM Plex Mono** (Dateinamen, Pfade, YAML, Labels)

**Farb-Tokens** (jeweils hell/dunkel über `prefers-color-scheme` + `[data-theme]`)
- Flächen: `--bg`, `--surface`, `--surface-2`, `--border`, `--border-strong`
- Text: `--text`, `--text-muted`
- Akzent: `--accent`, `--accent-deep`, `--accent-weak`, `--accent-contrast`
- Status: `--ok` (bereit), `--analyze` (Analyse), `--wait` (wartet), `--err` (Fehler), je mit
  `*-weak`-Variante für Flächen/Badges

**Form & Tiefe**
- Radien: `--r` (14px), `--r-sm` (9px), `--r-pill`
- Schatten: `--shadow`, `--shadow-lg`; dezente Atmosphäre durch zwei leise Grünschimmer + feines Korn
- Inhaltsbreite: `--maxw` (1080px), zentriert

**Komponenten-Klassen**
- App-Shell: `.topbar`, `.brand`, `.nav` (mit `.active`), `.theme-toggle`
- Struktur: `.page`, `.page-head`, `.eyebrow`, `.lead`, `.card`(`.pad`), `.card-title`
- Übersicht: `.stats` / `.stat` (`.ok`/`.analyze`/`.wait`/`.err`), `.dl`, `.chip(s)`
- Listen: `.table`, `.fname`, `.preview-cell`, `.badge` (Status), `.empty`
- Formular: `.field`, `.input`, `.select`, `.textarea`, `.choice` (Radio/Checkbox-Listen)
- Aktionen: `.btn` (`.btn-primary`/`.btn-ghost`/`.btn-sm`, `disabled`), `.link-arrow`
- Rückmeldung: `.banner` (`.ok`/`.err`), `.preview-name`, `.target-line` (`.conflict`)

## Theme

Standard folgt der Systemvorgabe (`prefers-color-scheme`). Der Umschalter in der Kopfleiste setzt
`data-theme="light|dark"` auf `<html>` und merkt die Wahl in `localStorage` (`app.js`). In 5b wird
dieselbe Mechanik als kleine Vanilla-JS-Datei neben HTMX übernommen.

## Übergang nach 5b

5b wird auf Basis dieser Artefakte **neu gebrainstormed**. Struktur (App-Shell, Seiten, Zustände)
und Designsystem (`design-system.css`) werden in Jinja2-Templates + HTMX überführt; die Mockups
liefern Markup-Vorlage und visuelle Zielmarke. Dynamik (Auto-Aktualisierung von Übersicht und
Warteschlange, Live-Namensvorschau) ist hier statisch dargestellt und wird in 5b per HTMX umgesetzt.
