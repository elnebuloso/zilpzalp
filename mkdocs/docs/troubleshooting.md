# Troubleshooting

ZilpZalp makes errors visible **without** building up a domain history. There are three
kinds of errors.

## Unreadable / empty PDF

If a PDF contains no text (e.g. a pure scan with no text layer — **no OCR in the MVP**)
or is corrupt, ZilpZalp moves the file to the `error/` folder and marks the queue entry
as `error` with a short reason.

The `error/` folder is the **only persistent error trace** — a file at the edge of the
workflow, not a log. Inspect the file, handle it outside ZilpZalp, and put it back into
the watchfolder once corrected if needed.

## Technical runtime error

If, for example, copying fails (target path gone, missing write permissions), the error
appears **transiently** on the queue entry and is additionally written to the container
logs:

```bash
docker compose logs -f backend
```

Transient errors disappear on restart/rescan, since the state is re-derived from the
watchfolder.

## Configuration error

- **At startup:** if `config.yaml` is invalid or a required path is missing, the backend
  container does not start. The cause is in the logs:

    ```bash
    docker compose logs backend
    ```

- **At runtime (change in the UI):** invalid input is rejected with a validation error;
  the previous configuration stays active.

## Container diagnostics

```bash
docker compose ps                             # are both containers running?
curl -fsS http://localhost:8000/healthz/live  # backend healthy? -> {"status":"ok"}
docker compose logs -f backend                # live backend logs
docker compose logs -f docs                   # live docs-site logs
```

## Files are not detected

- Is the PDF really in the mounted watchfolder (`./data/inbox` → `/data/inbox`)?
- On WSL2/Windows: is the folder on a **native Linux path**? On `/mnt/c/…` filesystem
  events are unreliable.
- A restart (`docker compose restart backend`) forces an initial scan.

!!! note "Logs are operational data, not document history"
    The container logs (stdout) serve operation and debugging. They are deliberately
    **not** a product-level history of the processed documents.
