# Usage

All operation happens through the web UI at <http://localhost:8000>.

## The review workflow

1. **Drop a PDF.** Put a PDF file into the watchfolder (`./data/inbox`). ZilpZalp
   detects it automatically and analyzes it.

2. **View the queue.** The home page lists all waiting documents. Each entry is either
   `pending` (ready for review) or `error` (see [Troubleshooting](troubleshooting.md)).

3. **Open the review.** Clicking an entry opens the detail view with the suggestion:
    - **Date:** all detected date candidates as a choice, each with context (e.g.
      "invoice date"). A pre-selection may be set; you can pick a different candidate at
      any time. If no date was found, you enter it manually.
    - **Sender, type, description:** pre-filled where ZilpZalp could derive them
      reliably — freely editable.
    - **Target folder:** choose from the configured targets.
    - **Final filename:** built live from the naming pattern.

4. **Confirm.** Depending on the `summary_mode` setting, a summary appears first. After
   confirmation ZilpZalp copies the file into the target folder.

5. **Original.** The original in the watchfolder is handled according to
   `original_handling` (moved, deleted, or kept). The entry disappears from the queue.

## Name conflicts

If a file with the same name already exists in the target folder, **you decide** —
ZilpZalp does **not** append an automatic suffix and never overwrites anything without
asking.

## Configuration in the UI

The **Configuration** page shows the current `config.yaml` and allows changes. Invalid
input is rejected with an error message; the previous configuration then stays active.
Reference for the contents: [Configuration](configuration.md).
