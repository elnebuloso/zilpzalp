# Design: Dev Server + Docker Runtime Data Layout

Date: 2026-06-17
Status: Approved (pending spec review)

## Problem

Several related frictions around running the app locally:

1. **No autonomous app run.** An agent (or developer) cannot reliably start/stop the
   FastAPI app to run manual or Playwright checks. There is no deterministic start that
   waits until the server actually serves, nor a clean stop. The app also defaults its
   runtime paths to `/data/*` and `/config` (absolute root paths), so a plain
   `uv run uvicorn` does not boot on a clean local checkout.
2. **Backend location is not documented in-repo.** The Python project root is `backend/`
   (uv, venv, `pyproject.toml`), but agents must rediscover this each session before
   `cd`-ing in. There is no durable, in-repo statement of this.
3. **`demo/` is confusing and the docs drift from reality.** `demo/` bundles two
   unrelated things — a versioned sample PDF and the docker-compose runtime data mount —
   under a misleading name. README/`installation.md` describe `demo/config` and
   `demo/targets` mounts that the real `docker-compose.yml` does not have (it only mounts
   `./demo/data:/data`).
4. **Port collision.** docker-compose maps host 8000/8001, which collides with a local
   dev server on 8000, so the two stacks cannot coexist.

## Goal

- A deterministic script an agent can call to start/stop the dev server (single uvicorn
  process, no live-reload) on host port **8000**, self-contained on a clean checkout,
  returning only once the server actually serves.
- A clear, symmetric on-disk layout that separates the two runtime areas:
  - `.dev/backend/` — the uv dev server's runtime (hidden, created on the fly, ignored).
  - `docker/backend/` — the docker-compose stack's runtime (visible, checked-in skeleton).
- Move docker-compose host ports off 8000/8001 to **8080/8081** so both stacks coexist.
- Make docker-compose self-documenting by mounting each storage path explicitly.
- Remove `demo/` and bring README/mkdocs docs back in sync with reality.
- Document in-repo where the backend lives.
- Correct the stale backlog lint-fix entry (the fix already landed in `6abc1b7`).

## Non-Goals

- No change to container-internal ports (stay 8000) or env-var path defaults.
- No new dependency (no `make`/`just`); plain POSIX shell + existing `uv`.
- No live-reload. The dev server runs as a single process; restart via `stop`+`start`
  after code changes. (Dropped deliberately to keep stop a portable single-process
  `kill`.)
- No automated screenshot pipeline (see "Unlocked next step").

## Design

### 1. Runtime data layout

Two parallel roots, same `backend/{config,data}` substructure, but deliberately treated
differently because they serve different masters:

```
docker/backend/                     ← compose stack (:8080), VISIBLE, checked-in skeleton
├── config/.gitignore               (content: "*\n!.gitignore")
└── data/
    ├── inbox/.gitignore            (each: "*\n!.gitignore")
    ├── error/.gitignore
    ├── trash/.gitignore
    ├── cache/.gitignore
    └── outbox/.gitignore

.dev/backend/                       ← uv dev server (:8000), HIDDEN, created on the fly
├── config/config.yaml              (seeded by the script from config.default.yaml)
├── data/{inbox,error,trash,cache,outbox}/   (created by the app's _ensure_dirs)
├── devserver.pid
└── devserver.log
```

**Why the asymmetry.** `docker/` is checked in for two reasons: (a) **ownership** — Docker
creates a missing bind-mount source as *root*; pre-creating it avoids root-owned dirs; and
(b) **visibility** — the user hand-touches `docker/backend/data/inbox` to drop PDFs and
edit config. Neither applies to `.dev/`: the script runs as the local user (so `mkdir -p`
yields correctly-owned dirs), and nothing under `.dev/` is touched by hand (tooling/agent
only). So `.dev/` is fully gitignored and created at runtime.

**Why `*` / `!.gitignore` over `.gitkeep`.** A per-dir `.gitignore` containing `*` and
`!.gitignore` is self-contained: it keeps the empty dir tracked AND ignores all runtime
content, in one file, with no central bookkeeping. `.gitkeep` only keeps the dir; runtime
files would still need separate central ignore rules.

**Gotcha (constrains placement).** Git cannot re-include a file whose parent directory is
excluded. So the `*` / `!.gitignore` idiom must live in each **leaf** dir (`config/`,
`data/inbox/`, …) — never in an ancestor like `docker/backend/`, which would exclude the
leaves and break the negation.

### 2. Dev-server script — `scripts/devserver.sh`

POSIX `sh` script with subcommands, invoked from repo root:

| Command  | Behavior |
|----------|----------|
| `start`  | Create `.dev/backend/config` as needed → seed config if missing → export dev path env → launch uvicorn in the background → poll health → print URL. Idempotent: if already up (PID file live), no-op. |
| `stop`   | `kill -TERM` the stored **PID**, wait for exit, remove PID file. No-op if not running. |
| `status` | Report up/down, PID, port. |
| `logs`   | Tail the logfile (`tail -f` by default). |

Internals:

- **Launch command:** from `backend/`, backgrounded with output to the logfile:
  `uv run uvicorn zilpzalp.main:app --host 127.0.0.1 --port 8000`
  The script `cd`s into `backend/` itself, so callers never need to. Single process
  (no `--reload`), so no supervisor/worker split.
- **Clean stop:** store `$!` (the backgrounded `uv run` PID) in
  `.dev/backend/devserver.pid`; stop with `kill -TERM <PID>`. `uv run` forwards the signal
  to its uvicorn child, which shuts down cleanly. No `setsid` / process group needed —
  fully portable.
- **Config seed:** if `.dev/backend/config/config.yaml` is absent, copy it from
  `backend/config.default.yaml`. An existing file is never overwritten.
- **Env exports** (all absolute, resolved from the repo root):
  - `ZILPZALP_CONFIG=<repo>/.dev/backend/config/config.yaml`
  - `ZILPZALP_PATH_INBOX=<repo>/.dev/backend/data/inbox`
  - `ZILPZALP_PATH_ERROR=<repo>/.dev/backend/data/error`
  - `ZILPZALP_PATH_TRASH=<repo>/.dev/backend/data/trash`
  - `ZILPZALP_PATH_CACHE=<repo>/.dev/backend/data/cache`
  - `ZILPZALP_PATH_OUTBOX=<repo>/.dev/backend/data/outbox`

  The app's `_ensure_dirs` creates the missing `data/*` subdirs at startup; the script does
  not pre-create them.
- **Health gate:** after launch, poll `http://127.0.0.1:8000/healthz/live` until HTTP 200
  or a ~15s timeout. On timeout: print the last log lines and exit non-zero. On success:
  print `Dev server up at http://127.0.0.1:8000`.
- **Inbox seed:** none. The inbox starts empty; a Playwright test that needs a document
  generates one on demand (reportlab is a dev dependency) or uploads via the UI.
- **Port:** fixed at 8000 (constant near the top of the script).

### 3. docker-compose changes

In `docker-compose.yml`:

- backend service port: `"8000:8000"` → `"8080:8000"`
- docs service port: `"8001:8000"` → `"8081:8000"`
- backend service volumes — replace the single `./demo/data:/data` with one explicit
  mount per storage path, so the compose file documents the storage locations:

  ```yaml
      volumes:
        - ./docker/backend/config:/config
        - ./docker/backend/data/inbox:/data/inbox
        - ./docker/backend/data/error:/data/error
        - ./docker/backend/data/trash:/data/trash
        - ./docker/backend/data/cache:/data/cache
        - ./docker/backend/data/outbox:/data/outbox
  ```

Container-internal ports, env-var path defaults (`/data/*`, `/config`), and the mkdocs
`--dev-addr=0.0.0.0:8000` are unchanged. The new `/config` mount also makes the
"mount `/config` for persistence" tip in `configuration.md` actually true.

### 4. Remove `demo/`

- `git rm -r demo/` (drops the versioned sample PDF and the data subtree).
- Replaced by `docker/backend/` (checked-in skeleton, §1) for the compose runtime.

### 5. CLAUDE.md — backend location section

Add a short section to the project `CLAUDE.md` stating:

- The Python backend lives in `backend/` — uv, the venv, and `pyproject.toml` are there.
- Run `uv`, `pytest`, `uvicorn` from `backend/` (e.g. `cd backend && uv run pytest`).
- For a running app (manual or Playwright checks), use
  `scripts/devserver.sh start|stop|status|logs` from the repo root (serves on
  `http://127.0.0.1:8000`).

### 6. Permissions + gitignore

- `.claude/settings.json` `allow`: add `Bash(scripts/devserver.sh *)` and
  `Bash(./scripts/devserver.sh *)`. (`Bash(uv run *)`, `Bash(cd *)`, and the Playwright
  tools are already allowed.)
- `.gitignore`: remove the entire `demo/` block (8 lines); add a single line `/.dev/`.
  The `docker/backend/**` skeleton is kept by its per-dir `.gitignore` files, so no
  central rule is needed for it.

### 7. Documentation sweep

Bring user-facing docs in sync with the new layout and ports (compose stack → 8080/8081;
the local dev server stays 8000):

- `README.md` — Web UI `:8000`→`:8080`, Documentation `:8001`→`:8081`; replace the
  `demo/config/config.yaml` / `demo/data/inbox` guidance with the new `docker/backend/*`
  paths (drop your own PDF into `docker/backend/data/inbox`).
- `mkdocs/docs/installation.md` — rewrite the mount table to the actual mounts
  (`docker/backend/config` → `/config`, `docker/backend/data/<sub>` → `/data/<sub>`);
  remove the non-existent `demo/config`/`demo/targets` rows and the "already contains a
  sample invoice" claim; URLs `:8000`→`:8080`, `:8001`→`:8081`; healthcheck curl
  `:8000`→`:8080`.
- `mkdocs/docs/usage.md` — `localhost:8000`→`localhost:8080`.
- `mkdocs/docs/troubleshooting.md` — healthcheck curl `:8000`→`:8080`.
- `CONTRIBUTING.md` — Web UI `:8000`→`:8080`, Documentation `:8001`→`:8081`,
  `docker compose up docs` URL `:8001`→`:8081`.

(Match by content during implementation; line numbers shift as edits land.)

### 8. Folded-in cleanup — lint fix (already resolved)

The backlog "Ideen / später" item — unused `pytest` import in `backend/tests/test_i18n.py`
(Ruff F401) — is **already fixed** by commit `6abc1b7` ("style(tests): remove unused pytest
import in test_i18n"). `cd backend && uv run ruff check .` is green project-wide. No code
change remains; only the stale backlog entry needs correcting (see §10).

### 9. Already done

`backend/config.example.yaml` was removed in commit `229f5c0` (dead file; the annotated
example lives solely in `mkdocs/docs/configuration.md`, and `config.default.yaml` is the
single runtime seed). Listed here for completeness; no further action.

### 10. Backlog tracking

Per `docs/backlog.md` upkeep rule, update the backlog:

- add one row to the "## Umsetzung" table for this update (Art: `Feinschliff`, Thema: dev
  server + docker runtime layout, linking this spec), SHA filled on completion; and
- move the now-stale lint-fix item out of "Ideen / später" into the Umsetzung table as
  ✅ done, attributing commit `6abc1b7` (it was resolved earlier; the backlog just never
  recorded it).

## Testing / Verification

- `scripts/devserver.sh start` on a clean checkout boots; `/healthz/live` returns 200;
  `.dev/backend/{config/config.yaml,data/inbox,…}` exist and are gitignored.
- `status` reports up; `stop` brings it down with **no orphaned uvicorn/python process**
  (verify via `pgrep -f uvicorn`). `start` twice is a no-op the second time.
- `docker compose up` exposes backend on `localhost:8080`, docs on `localhost:8081`;
  both coexist with a running dev server on 8000; the `docker/backend/*` host dirs fill in
  and the seeded `config.yaml` appears under `docker/backend/config`.
- `git status` is clean while both stacks run (runtime content ignored; only the
  `.gitignore` skeletons tracked).
- `cd backend && uv run pytest` green and `uv run ruff check .` reports no F401.
  Restore `backend/uv.lock` if `uv run` rewrites it spuriously.

## Risks / Notes

- `uv run` may spuriously rewrite `backend/uv.lock`; restore before committing.
- Single-process + plain `kill -TERM <PID>` is portable (no `setsid`); the trade-off — no
  live-reload — is accepted.
- The `docker/` name can connote "Dockerfiles" in some projects; here it holds compose
  runtime data. Accepted for symmetry with `.dev/`.
- Removing `demo/` changes the documented "ready to run with a sample" onboarding; the docs
  now instruct the user to drop their own PDF. No test depends on the sample PDF.

## Unlocked next step (not in this update)

The backlog item "Screenshots in der mkdocs-Doku via Playwright" (`docs/backlog.md`)
becomes feasible once this update lands — the dev server + Playwright is its prerequisite.
It remains a separate feature with its own spec.
