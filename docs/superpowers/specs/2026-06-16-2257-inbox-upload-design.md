# Design: Upload files into the inbox via the UI

## Problem

Today the only way to get a PDF into ZilpZalp is to drop it into the watchfolder
on the host filesystem (or repoint a Docker volume). There is no way to add a
document from the browser. Users want to upload one or more PDFs directly through
the web UI and have them picked up like any other inbox file.

## Goal

Let the user select or drag-and-drop multiple PDFs in the browser and upload them
into the watchfolder, with clear per-file feedback (which file is uploading, a
progress bar, success/error). Uploaded files must flow through the existing
analysis pipeline unchanged.

## Key insight

The watchfolder **is** the inbox. The existing `Watcher` already turns any new
`.pdf` landing there (via `on_created` / `on_moved`) into a `worker.submit` call,
which analyzes it and adds it to the queue. So the upload feature does **not**
touch the queue, worker, or analysis at all — it only has to **land files into
the watchfolder correctly**. The existing pipeline takes over from there.

Hard constraint: the watcher only processes `.pdf` files. Anything else would be
silently ignored, so uploads must be restricted to PDFs on both client and
server.

## Data flow

```
Browser (drop / file picker)
  → POST /upload   (one file per request, sent sequentially)
  → server writes the file atomically into the watchfolder
  → watchdog on_moved fires → worker.submit → entry appears in the queue
  → nav queue count ticks up via the existing 2s polling
```

### Why one file per request

Per-file progress (`XMLHttpRequest.upload.onprogress`) and a "which file is
uploading now" indicator are only possible when each file is its own request. A
single multipart request with all files would yield only one aggregate bar. Files
are uploaded **sequentially**, one after another.

### Atomic write (the "done properly" part)

The server must never let the watcher observe a half-written file. Therefore the
endpoint:

1. Streams the request body to a temporary file **in the watchfolder itself**
   with a non-`.pdf` name, e.g. `.upload-<token>.part` (same filesystem → the
   final rename is atomic; the watcher ignores `.part`).
2. Calls `os.replace(tmp, final)` to move it into place under its final `.pdf`
   name. This move triggers `on_moved`, which the watcher already handles.
3. On any error, the temp file is removed and no `.pdf` ever appears.

The body is streamed to disk, never loaded fully into memory.

## Components

### Server: `POST /upload`

New route in `web/routes.py`. Accepts a multipart form with exactly **one** file
(field name `file`).

1. **Validation** — the filename must end in `.pdf` **and** the first bytes must
   be the `%PDF` magic signature. Extension alone is too weak. On failure return
   `400` with a translated error message.
2. **Filename sanitization** — strip any path components; keep only the base
   name. Reject empty names.
3. **Conflict resolution** — if `inbox/<name>.pdf` already exists, save as
   `<name> (1).pdf`, `<name> (2).pdf`, … (auto-rename, never overwrite, never
   reject). This preserves the "folder is the source of truth, no surprises"
   philosophy and protects unconfirmed documents already in the queue.
4. **Atomic write** — as described above, body streamed.
5. **Response** — `200` with the final filename actually used (so the client can
   show it); `4xx` with an error message otherwise.

The endpoint does not read or mutate the queue; it only deposits a file.

### Client: drop-zone card on the Overview page

A new upload card on `overview.html`, alongside the existing watchfolder /
operations info. Implemented in vanilla JS within the existing `app.js` style (no
build step, no new dependency).

- **Input** — drag & drop **and** click-to-browse (a hidden
  `<input type="file" multiple accept="application/pdf,.pdf">`). Both, because
  users expect both.
- **Sequential uploader** — selected files go into a list; a small uploader sends
  them one at a time via `XMLHttpRequest`.
- **Per-file status row** — filename + status badge
  (`queued` → `uploading …` → `done` / `error`) + a **progress bar** per file,
  driven by `xhr.upload.onprogress`.
- **Client-side filter** — non-PDF selections are rejected immediately with a
  short message (the server still re-validates).
- **After completion** — the nav queue count ticks up automatically via the
  existing 2 s polling; the uploaded file visibly moves into processing. An
  optional toast reports "N files uploaded".

#### Why vanilla XHR and not HTMX here

HTMX can report upload progress (`htmx:xhr:progress`), but sequential, per-file
control with a custom status list is clearer as a small explicit uploader than as
bent HTMX attributes. It stays consistent with the existing `app.js`.

## Error handling

- Non-PDF (extension or magic bytes): rejected client-side and, defensively,
  server-side with `400`.
- Network / server error mid-upload: that file's row shows `error`; the
  sequential uploader continues with the remaining files.
- Name conflict: resolved silently by the `(n)` suffix; not an error.
- Partial write / crash: the `.part` temp file never becomes a `.pdf`, so no
  half-file enters the pipeline.

## Testing

Endpoint tests alongside the existing `tests/test_routes.py`:

- A valid PDF lands in the watchfolder and is reported with its final name.
- A non-PDF (bad extension or missing `%PDF` magic) returns `400` and writes
  nothing.
- A name collision produces a `(1)` suffix without touching the original.
- No `.part` file remains after a successful upload.

## i18n and documentation

- **i18n** — new keys in `de.json` / `en.json`: drop-zone label, status labels
  (`queued` / `uploading` / `done` / `error`), and error messages.
- **Docs** — a short "Upload from the browser" section added to the mkdocs usage
  page (English).

## Out of scope (YAGNI)

- Parallel uploads (sequential is the explicit choice).
- File-size limits / quotas (self-hosted, single user; the body is streamed so
  RAM is not a concern).
- Resume / chunking of interrupted uploads.
