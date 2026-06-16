# Design: Fallback dates when no date is extracted

## Problem

When a PDF's text contains no recognizable date, `analyze()` returns an empty
`date_candidates` list. `suggest()` then falls back to an empty date string, and
`render_filename()` produces a broken-looking name such as
`__Unbekannt_Dokument_.pdf` (sender/doctype have `Unbekannt`/`Dokument`
fallbacks; the date segment has none). Nothing is preselected in the review UI
for the user to start from.

## Goal

Guarantee that every successfully extracted PDF has at least one date candidate
to preselect and edit, so the filename always carries a real date and the empty
`__…` name no longer occurs. The user can still pick any candidate or enter a
date manually as a last resort.

## Key insight

The three originally-suspected problem areas collapse into one real gap:

- **Review UX** — already complete. The review page lets the user pick any
  candidate *and* type a manual date, and a date is already required before
  confirmation is possible.
- **Filename output** — the broken `__…` name is only a *symptom* of an empty
  candidate list, not a separate issue.
- **Detection/data** — the actual gap: no candidate exists when the text has no
  date.

Adding always-on file-level date candidates (PDF metadata + filesystem mtime)
eliminates the empty-list case, because a real file always has an mtime. The
filename symptom disappears for free.

## Decisions

- Fallback dates are sourced as **PDF metadata first, then file mtime**.
- They are modeled as **always-on candidates**: always appended to the candidate
  list (ranked below text dates), not only injected when text yields nothing.
- The review flow **suggests an editable fallback** (one of these candidates is
  preselected) that the user can accept or override.
- **Manual date entry remains available as the last resort** and stays required
  to confirm. Already implemented; pinned by a regression test.

## Architecture (Approach A)

File-level dates are read in the worker (which already has the source path) and
passed into `analyze()`, which appends and de-duplicates them. This keeps all
candidate-ranking logic in `analyzer.py` and keeps `analyze()` filesystem-free
and unit-testable.

### 1. New candidate source: `file_dates(path)`

New function in `analyzer.py`:

```python
def file_dates(path: Path) -> list[DateCandidate]:
    """File-level fallback dates, always appended after text candidates."""
```

Produces, in this fixed priority order, skipping any unavailable entry:

1. PDF `CreationDate` → label key `pdf_created`
2. PDF `ModDate` → label key `pdf_modified`
3. File mtime (`path.stat().st_mtime`) → label key `file_modified`

- PDF metadata is read with **pypdf** (`PdfReader(path).metadata.creation_date`
  / `.modification_date`, which return `datetime` or `None`).
- Reading metadata is wrapped in try/except: on any pypdf error, fall back to
  mtime alone and never raise — the worker must not lose a document over a
  metadata hiccup.
- `normalized` uses `config.date_format`. `raw`/`snippet` are `None` (these
  dates have no corresponding text to highlight).

### 2. Ranking, dedup, preselection

- `analyze()` builds text candidates as today, then **appends** the
  `file_dates(path)` list passed in by the worker.
- **Dedup by `normalized` value:** a file date is appended only if its
  normalized string is not already present. Text candidates come first and
  always win.
- **Preselection** (`_preselect`) is unchanged: prefer a rule's
  `preferred_label`, otherwise index 0. A text date is preselected whenever one
  exists; only when text yields nothing does the first file date
  (`pdf_created`, else `pdf_modified`, else `file_modified`) get preselected.
- The `idx is None → ""` defensive branch in `suggest()` stays as-is for the
  theoretical empty case.

### 3. Labels & i18n

The synthetic labels are app-generated (unlike text labels, which come from
document content). `DateCandidate` gains a stable `label_key` field
(`pdf_created` / `pdf_modified` / `file_modified`) alongside the existing
free-text `label`. The key is translated at render time via the i18n `t()`
helper, so the backend stays locale-free.

Locale strings to add:

| key            | de              | en              |
|----------------|-----------------|-----------------|
| `pdf_created`  | PDF erstellt    | PDF created     |
| `pdf_modified` | PDF geändert    | PDF modified    |
| `file_modified`| Datei geändert  | File modified   |

### 4. Wiring

- `analyzer.py`: add `file_dates(path)`; add `label_key` field to
  `DateCandidate`; `analyze(document, config, file_dates=...)` appends + dedups.
- `worker._process`: read `file_dates(path)` and pass into `analyze`. The only
  place the path is read for dates.
- `routes.py` / `review.html`: render `label_key` through `t()`; add the three
  keys to `en.json` / `de.json`.
- `pyproject.toml`: move `pypdf>=4.0` from the dev group to runtime
  dependencies.

## Testing

- `file_dates()` unit tests: PDF with both metadata dates; PDF with only mtime
  (no metadata); pypdf raising → falls back to mtime; correct ordering.
- `analyze()` dedup test: a file date equal to a text date is not duplicated;
  file dates are appended after text dates.
- **Regression — the guarantee:** a document with zero text dates still yields a
  non-empty preselected candidate and a filename with a real date segment (no
  leading `__`).
- **Manual-date guarantee:** confirm route with `date_kind="manual"` +
  `date_value` produces the expected filename — locks in the existing last-resort
  path.

## Out of scope (YAGNI)

- No OCR / scanned-image date recovery (such PDFs already go to `error/` via
  `ExtractionError`).
- No new config knobs for fallback behavior — fixed priority order.
- No change to the date-required-to-confirm rule (already enforced).
