# Configuration

The file `config.yaml` (mounted at `/config/config.yaml`) is the **only persistent
setting**. It is validated at startup: if a required path is missing or a naming pattern
contains an unknown placeholder, ZilpZalp **does not start** and instead reports the
error clearly.

!!! info "Paths are container paths"
    All paths in `config.yaml` refer to the **inside of the container**
    (`/data/inbox`, `/targets/…`). How these map to host folders is defined in
    `docker-compose.yml` (see [Installation](installation.md)).

## Full example

```yaml
paths:
  watchfolder: /data/inbox
  error_folder: /data/error
  processed_folder: /data/processed   # only needed with original_handling: move

original_handling: move        # move | delete | keep
summary_mode: on_conflict      # always | on_conflict | never

default_pattern: "{date}__{sender}_{doctype}_{description}"
date_format: "%Y-%m-%d"

# Optional: additional date matchers for special cases.
# The built-in date detection ALWAYS runs and needs NO configuration.
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

!!! note
    The example values above (target names, German keywords and date labels) are just
    illustrations — `date_patterns` regexes and `keywords_any` naturally match the
    language of your documents.

## Fields

### `paths`

| Key | Required | Meaning |
|---|---|---|
| `watchfolder` | yes | the watched inbox folder |
| `error_folder` | yes | storage for unreadable PDFs |
| `processed_folder` | only with `original_handling: move` | storage for processed originals |

### `original_handling`

What happens to the original in the watchfolder after successful filing:

- `move` — move it to `processed_folder`
- `delete` — delete it
- `keep` — leave it in the watchfolder

### `summary_mode`

When a summary is shown before confirmation:
`always`, `on_conflict` (only on a name conflict), `never`.

### `date_format`

Format of the date in the filename, as a Python `strftime` pattern
(e.g. `%Y-%m-%d` → `2026-06-14`).

### Naming patterns (`default_pattern`, `patterns`)

Placeholders in the pattern: `{date}`, `{sender}`, `{doctype}`, `{description}`.
`patterns` names reusable patterns that rules reference by name.

### `date_patterns` (optional)

Additional date matchers for special cases. The first capture group provides the date
value, `label` appears as context in the UI. These entries **extend** the built-in
formats (additive) — they do not replace them. Invalid regular expressions are rejected
at load time with a clear message.

### `targets`

List of target folders with `name`, `path`, and `default` (pre-selection in the UI).

### `rules`

An ordered list — **the first matching rule wins**. A rule **does not automate anything
end-to-end**: `apply` only sets suggestions that you confirm or change in the UI.

- `match` — all conditions must hold (e.g. `sender_contains`, `keywords_any`).
- `apply` — values to suggest (`sender`, `doctype`, `description`, `pattern`,
  `targets`) plus `preferred_date`: **pre-selects** one of the detected date candidates
  but never hides the others.
