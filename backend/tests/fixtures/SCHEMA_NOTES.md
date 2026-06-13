# OpenDataLoader (ODL) JSON Schema – Beobachtungen

Quelle der Wahrheit fuer die Mapping-Konstanten in Tasks 4 & 5. Erfasst aus
`invoice.odl.json`, erzeugt mit `opendataloader-pdf` 2.4.7 aus `invoice.pdf`
(reportlab-generiert). Regenerieren via `tests/fixtures/make_fixtures.py`.

## Top-Level-Struktur: TREE (kein flacher Element-Stream)

Das Top-Level ist ein **Objekt** (dict), nicht eine Liste. Die Dokument-
Elemente haengen am Schluessel **`kids`** (eine Liste). Verschachtelung
erfolgt rekursiv ueber denselben Schluessel `kids`.

Top-Level-Metadaten-Schluessel:

- `file name` (str)
- `number of pages` (int)
- `author` (str)
- `title` (str)
- `creation date` (str, z.B. `D:20260613...`)
- `modification date` (str)
- `kids` (list) – die eigentlichen Inhalts-Elemente

## Feldnamen pro Element (exakt, inkl. Leerzeichen)

| Bedeutung        | EXAKTER Key       | Beispielwert                        |
|------------------|-------------------|-------------------------------------|
| Typ              | `type`            | `paragraph`, `heading`, `table`, `table row`, `table cell` |
| Text             | `content`         | `"Stadtwerke Musterstadt GmbH"`     |
| Seite            | `page number`     | `1`                                 |
| Bounding Box     | `bounding box`    | `[72.0, 797.5, 222.4, 810.2]` (Liste aus 4 floats: x0,y0,x1,y1) |
| Heading-Level    | `heading level`   | `1` (nur bei `type == "heading"`)   |
| Kinder           | `kids`            | Liste verschachtelter Elemente      |

Weitere, fuer das Mapping vermutlich irrelevante Felder pro Element:
`pdfua_tag` (z.B. `P`, `H1`, `Table`, `TD`), `id`, `font`, `font size`,
`text color`. Bei `heading` zusaetzlich `level` (z.B. `"Doctitle"`).

WICHTIG: Die Schluessel enthalten **Leerzeichen** (`page number`,
`bounding box`, `heading level`, `number of rows`, `number of columns`,
`row number`, `column number`, `row span`, `column span`) – beim Mapping
exakt so verwenden.

## Beobachtete `type`-Werte

- `paragraph` – normaler Textabsatz (Text in `content`)
- `heading` – Ueberschrift, zusaetzlich `heading level` (int)
- `table` – Tabelle (siehe unten)
- `table row` – Zeile innerhalb einer Tabelle
- `table cell` – Zelle innerhalb einer Zeile

## TABELLEN-Darstellung (Tabelle WURDE erfasst)

Eine echte Tabelle ist im Fixture enthalten (3 Zeilen x 2 Spalten). Aufbau:

```
table (type="table")
  number of rows: 3
  number of columns: 2
  rows: [                         <-- Schluessel "rows" (NICHT "kids")
    table row (type="table row")
      row number: 1
      cells: [                    <-- Schluessel "cells" (NICHT "kids")
        table cell (type="table cell")
          row number, column number, row span, column span
          kids: [                 <-- Zellinhalt liegt in "kids"
            paragraph
              content: "Rechnungsdatum"
          ]
        table cell ...
          kids: [ paragraph content="15.01.2026" ]
      ]
    table row ...
  ]
```

Merksaetze fuer das Mapping:

- Eine `table` hat ihre Zeilen unter **`rows`** (nicht `kids`),
  plus Zaehler `number of rows` / `number of columns`.
- Eine `table row` hat ihre Zellen unter **`cells`** (nicht `kids`),
  plus `row number`.
- Eine `table cell` traegt `row number`, `column number`, `row span`,
  `column span` und legt ihren eigentlichen Textinhalt (Paragraphen)
  unter **`kids`** ab. Der Text steht also NICHT direkt in der Zelle,
  sondern im `content` der Paragraph-Kinder.

Hinweis: Ein reines Spalten-Layout (zwei Texte auf gleicher y-Hoehe per
`canvas.drawString`) reichte NICHT – ODL fasste das zu einem einzigen
Paragraph zusammen. Erst eine echte reportlab-`Table` mit Gitterlinien
(`GRID`) erzeugte verlaesslich die `table`/`table row`/`table cell`-Struktur.

## Ausgabe-Datei: Naming & Location (fuer Task 6 glob)

`opendataloader_pdf.convert(input_path=['.../invoice.pdf'], output_dir=D,
format='json')` schreibt die JSON-Datei **direkt** nach `D` (kein
Unterordner). Der Dateiname ist der **PDF-Stem + `.json`**:

- Input `invoice.pdf` -> Output `invoice.json`
- `OUTPUT FILES:` = `['invoice.json']`

`pathlib.Path(D).glob('*.json')` findet die Datei direkt – `rglob` war
NICHT noetig. Task 6 kann also `glob('*.json')` (oder `glob(stem + '.json')`)
verwenden.
