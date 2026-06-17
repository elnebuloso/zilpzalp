# Design: Autonomous Dev Server + Backend Location

Date: 2026-06-17
Status: Approved (pending spec review)

## Problem

Two recurring frictions:

1. **No autonomous app run.** An agent (or developer) cannot reliably start/stop the
   FastAPI app to run manual or Playwright checks. There is no deterministic start that
   waits until the server actually serves, nor a clean stop. The app also defaults its
   runtime paths to `/data/*` and `/config` (absolute root paths), so a plain
   `uv run uvicorn` does not boot on a clean local checkout.
2. **Backend location is not documented in-repo.** The Python project root is `backend/`
   (uv, venv, `pyproject.toml`), but agents must discover this each session before
   `cd`-ing in. There is no durable, in-repo statement of this.

## Goal

- A deterministic script an agent can call to start/stop the dev server (single uvicorn
  process, no live-reload) on host port **8000**, self-contained on a clean checkout,
  returning only once the server actually serves.
- Move the docker-compose host port mappings off 8000/8001 to **8080/8081** so the
  compose stack and the local dev server can coexist.
- Document in-repo where the backend lives so agents stop re-discovering it.

## Non-Goals

- No change to container-internal ports (stay 8000).
- No new dependency (no `make`/`just`); plain POSIX shell + existing `uv`.
- No live-reload. The server runs as a single process; restart via `stop`+`start` after
  code changes. (Dropped deliberately to keep stop a portable single-process `kill`.)
- The script does not run Playwright; it only guarantees the server is up. Playwright is
  driven separately (MCP browser tools).

## Design

### 1. Dev-server script — `scripts/devserver.sh`

POSIX `sh` script with subcommands, invoked from repo root:

| Command  | Behavior |
|----------|----------|
| `start`  | Seed config if missing → export dev path env → launch uvicorn in the background → poll health → print URL. Idempotent: if already up (PID file live), no-op. |
| `stop`   | `kill -TERM` the stored **PID**, wait for exit, remove PID file. No-op if not running. |
| `status` | Report up/down, PID, port. |
| `logs`   | Tail the logfile (`tail -f` by default, `-n` honored if passed through). |

Internals:

- **Launch command:** from `backend/`, backgrounded with output to the logfile:
  `uv run uvicorn zilpzalp.main:app --host 127.0.0.1 --port 8000`
  The script `cd`s into `backend/` itself, so callers never need to. Single process
  (no `--reload`), so no supervisor/worker split.
- **Clean stop:** store `$!` (the backgrounded `uv run` PID) in the PID file; stop with
  `kill -TERM <PID>`. `uv run` forwards the signal to its uvicorn child, which shuts down
  cleanly. No `setsid` / process group needed — fully portable.
- **PID + log files:** `.devserver.pid` (stores the PID) and `.devserver.log` at repo
  root. Both gitignored.
- **Health gate:** after launch, poll `http://127.0.0.1:8000/healthz/live` until HTTP 200
  or a ~15s timeout. On timeout: print the last log lines and exit non-zero so failures
  are loud. On success: print `Dev server up at http://127.0.0.1:8000`.
- **Port:** fixed at 8000 (constant near top of script for easy change).

### 2. Self-contained dev config + paths

On `start`, before launch, the script:

- Seeds `backend/config.yaml` (gitignored) from `backend/config.default.yaml` **only if
  absent**. `config.default.yaml` is minimal and has no hardcoded `targets:` block, so
  the app auto-creates a writable default "Outbox" target at `ZILPZALP_PATH_OUTBOX`.
  An existing `config.yaml` is never overwritten.
- Exports the runtime paths to live under the repo's `demo/data/`:
  - `ZILPZALP_CONFIG=<repo>/backend/config.yaml`
  - `ZILPZALP_PATH_INBOX=<repo>/demo/data/inbox`
  - `ZILPZALP_PATH_ERROR=<repo>/demo/data/error`
  - `ZILPZALP_PATH_TRASH=<repo>/demo/data/trash`
  - `ZILPZALP_PATH_CACHE=<repo>/demo/data/cache`
  - `ZILPZALP_PATH_OUTBOX=<repo>/demo/data/outbox`

  All paths absolute (resolved from the script location). The app's `_ensure_dirs`
  creates any missing folders at startup. The `demo/data/*` subfolders (except the
  versioned sample PDF) are already gitignored.

Result: `scripts/devserver.sh start` boots on a clean checkout with zero manual setup,
and the seeded inbox already contains `demo/data/inbox/beispiel-rechnung.pdf` for a
realistic UI state.

### 3. docker-compose port changes

In `docker-compose.yml`, change only the host side of the mappings:

- backend: `"8000:8000"` → `"8080:8000"`
- docs:    `"8001:8000"` → `"8081:8000"`

Container-internal ports and the mkdocs `--dev-addr=0.0.0.0:8000` are unchanged. Host
port 8000 is thereby freed for the uv dev server.

### 4. CLAUDE.md — backend location section

Add a short section to the project `CLAUDE.md` (near the top, e.g. after the working
principles) stating:

- The Python backend lives in `backend/` — uv, the venv, and `pyproject.toml` are there.
- Run `uv`, `pytest`, `uvicorn` from `backend/` (e.g. `cd backend && uv run pytest`).
- For a running app (manual or Playwright checks), use
  `scripts/devserver.sh start|stop|status|logs` from the repo root.

### 5. Permissions + gitignore

- `.claude/settings.json` `allow`: add
  `Bash(scripts/devserver.sh *)` and `Bash(./scripts/devserver.sh *)` so start/stop never
  prompt. (`Bash(uv run *)`, `Bash(cd *)`, and the Playwright tools are already allowed.)
- `.gitignore`: add `/.devserver.pid` and `/.devserver.log`.

### 6. Documentation sweep (port references)

After the compose port change, update the user-facing compose URLs from 8000/8001 to
8080/8081. Affected lines (compose stack only — the local dev server stays 8000):

- `README.md:44` Web UI `localhost:8000` → `localhost:8080`
- `README.md:45` Documentation `localhost:8001` → `localhost:8081`
- `CONTRIBUTING.md:27` Web UI `localhost:8000` → `localhost:8080`
- `CONTRIBUTING.md:28` Documentation `localhost:8001` → `localhost:8081`
- `CONTRIBUTING.md:76` `docker compose up docs # http://localhost:8001` → `:8081`
- `mkdocs/docs/usage.md:3` `localhost:8000` → `localhost:8080`
- `mkdocs/docs/installation.md:36` Web UI `localhost:8000` → `localhost:8080`
- `mkdocs/docs/installation.md:37` docs `localhost:8001` → `localhost:8081`
- `mkdocs/docs/installation.md:43` `curl ... localhost:8000/healthz/live` → `:8080`
- `mkdocs/docs/troubleshooting.md:45` `curl ... localhost:8000/healthz/live` → `:8080`

(Line numbers are indicative as of writing; match by content during implementation.)

## Testing / Verification

- `scripts/devserver.sh start` on a clean checkout boots and `/healthz/live` returns 200.
- `scripts/devserver.sh status` reports up; `stop` brings it down with **no orphaned
  uvicorn/python process** (verify via `pgrep -f uvicorn`).
- `start` twice in a row is a no-op the second time (idempotent).
- `docker compose up` exposes backend on `localhost:8080` and docs on `localhost:8081`,
  and they coexist with a running dev server on 8000.
- `cd backend && uv run pytest` still green (no source changes, but confirm nothing
  regressed). Restore `backend/uv.lock` if `uv run` rewrites it spuriously.

## Risks / Notes

- `uv run` may spuriously rewrite `backend/uv.lock`; restore before committing.
- Single-process + plain `kill -TERM <PID>` is portable (no `setsid`, no process group),
  working on Linux/WSL2 and macOS alike. The trade-off — no live-reload — is accepted; a
  code change requires `stop`+`start`.
