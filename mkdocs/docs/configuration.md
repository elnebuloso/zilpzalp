# Configuration

The file `config.yaml` (path controlled by the `ZILPZALP_CONFIG` env var, default
`/config/config.yaml`) is the **only persistent setting**. It is validated at startup:
if a naming pattern contains an unknown placeholder, ZilpZalp **does not start** and
instead reports the error clearly.

!!! info "Infra paths come from environment variables"
    Folder paths are **not** part of `config.yaml`. They are set via
    `ZILPZALP_PATH_*` environment variables (see table below).

!!! tip "Volume mount for persistence"
    Mount `/config` as a Docker volume so that UI config edits survive container
    restarts. On first start the entrypoint seeds `/config/config.yaml` from the
    built-in default if the file does not exist yet.

## Infrastructure path variables

| Variable | Default | Meaning |
|---|---|---|
| `ZILPZALP_PATH_INBOX` | `/data/inbox` | Watched folder for incoming PDFs |
| `ZILPZALP_PATH_ERROR` | `/data/error` | Storage for unreadable PDFs |
| `ZILPZALP_PATH_TRASH` | `/data/trash` | Trash bin (used when `originals.when_filed` or `originals.when_removed` is set to `trash`) |
| `ZILPZALP_PATH_OUTBOX` | `/data/outbox` | Default output target ("Outbox") |
| `ZILPZALP_PATH_CACHE` | `/data/cache` | OCR / extraction cache |

## Full example

```yaml
# Infra paths come from ZILPZALP_PATH_* env vars — not from this file.
originals:
  when_filed: delete             # delete | trash — original after a successful filing
  when_removed: trash            # delete | trash — original on deliberate removal
summary_mode: on_conflict        # always | on_conflict | never

default_pattern: standard
date_format: "%Y-%m-%d"

# Optional: additional date matchers for special cases.
# The built-in date detection ALWAYS runs and needs NO configuration.
date_patterns:
  - label: leistungsdatum
    regex: 'Leistungsdatum:\s*(\d{2}\.\d{2}\.\d{4})'

# If this block is omitted, a default "Outbox" target (ZILPZALP_PATH_OUTBOX)
# is created automatically.
targets:
  - name: Finanzen
    path: /targets/finanzen
    default: true

patterns:
  standard:
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

!!! note
    The example values above (target names, German keywords and date labels) are just
    illustrations — `date_patterns` regexes and `keywords_any` naturally match the
    language of your documents.

## Fields

### `originals`

Controls what happens to the original PDF in the inbox for the two disposal situations.
The asymmetry is intentional: after filing a copy already exists in the target folders,
so deleting the original is lossless; on a deliberate removal there is no copy anywhere,
so trashing is the safe default.

```yaml
originals:
  when_filed: delete    # delete | trash
  when_removed: trash   # delete | trash
```

- **`when_filed`** — disposal after a successful **Confirm** (filing): `delete` removes
  the original permanently; `trash` moves it to `ZILPZALP_PATH_TRASH`.
- **`when_removed`** — disposal after a deliberate **Remove**: `trash` moves it to
  `ZILPZALP_PATH_TRASH`; `delete` removes it permanently.

### `summary_mode`

When a summary is shown before confirmation:
`always`, `on_conflict` (only on a name conflict), `never`.

### `date_format`

Format of the date in the filename, as a Python `strftime` pattern
(e.g. `%Y-%m-%d` → `2026-06-14`).

### Naming patterns (`default_pattern`, `patterns`)

Placeholders in the pattern: `{date}`, `{sender}`, `{doctype}`, `{description}`.

`patterns` is a **map** (key → pattern definition). Rules reference patterns by their
key name. `default_pattern` names the key to use when no rule matches.

```yaml
patterns:
  standard:
    template: "{date}__{sender}_{doctype}_{description}"
  compact:
    template: "{date}_{description}"
```

### `date_patterns` (optional)

Additional date matchers for special cases. The first capture group provides the date
value, `label` appears as context in the UI. These entries **extend** the built-in
formats (additive) — they do not replace them. Invalid regular expressions are rejected
at load time with a clear message.

### `targets`

List of target folders, each with `name`, `path`, and `default` (pre-selection in the UI).
If this block is omitted entirely, ZilpZalp synthesises a single "Outbox" target pointing
to `ZILPZALP_PATH_OUTBOX`.

### `rules`

An ordered list — **the first matching rule wins**. A rule **does not automate anything
end-to-end**: `apply` only sets suggestions that you confirm or change in the UI.

- `match` — all conditions must hold (e.g. `sender_contains`, `keywords_any`).
- `apply` — values to suggest (`sender`, `doctype`, `description`, `pattern`,
  `targets`) plus `preferred_date`: **pre-selects** one of the detected date candidates
  but never hides the others.
