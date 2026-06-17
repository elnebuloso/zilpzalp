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
   confirmation ZilpZalp copies the file into all selected target folders and disposes
   the original according to `originals.when_filed` (`delete` or `trash`). The entry
   disappears from the queue. If no further ready document remains, you are returned to
   the overview.

5. **Skip.** Navigation only — jumps to the next ready document and leaves the current
   one untouched in the queue. No file is moved or deleted. If no further ready document
   remains after the current one, you are returned to the overview.

6. **Remove.** Deliberately discards a document. Available from the queue list, the
   overview, and the review page. The original is disposed according to
   `originals.when_removed` (`delete` or `trash`). Before the action executes, the
   button swaps to an inline **Yes / No** confirmation so accidental clicks are
   prevented.

## Name conflicts

If a file with the same name already exists in the target folder, **you decide** —
ZilpZalp does **not** append an automatic suffix and never overwrites anything without
asking.

## Configuration in the UI

The **Configuration** page shows the current `config.yaml` and allows changes. Invalid
input is rejected with an error message; the previous configuration then stays active.
Reference for the contents: [Configuration](configuration.md).

## Upload from the browser

Besides dropping files into the watchfolder on disk, you can upload PDFs directly
from the **Overview** page. Drag one or more PDFs onto the upload area, or click it
to pick files. Each file is uploaded individually with its own progress bar, then
appears in the queue within a couple of seconds — exactly as if it had been placed
in the watchfolder by hand. Only PDF files are accepted; if a file name already
exists in the inbox, the upload is kept under a numbered name such as
`invoice (1).pdf` rather than overwriting the original.
