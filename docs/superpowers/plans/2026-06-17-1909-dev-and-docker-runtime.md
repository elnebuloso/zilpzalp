# Dev Server + Docker Runtime Data Layout — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give an agent a deterministic `scripts/devserver.sh` to run the backend on host port 8000 for Playwright/manual checks, and reorganise the docker-compose runtime data into a clean, self-documenting `docker/backend/` layout (replacing the confusing `demo/`).

**Architecture:** Two parallel runtime roots with the same `backend/{config,data}` substructure but different git treatment — `docker/backend/` is a visible, checked-in skeleton (bind-mount targets for compose); `.dev/backend/` is hidden, fully gitignored, created on the fly by the dev-server script and the app. docker-compose moves to host ports 8080/8081 and mounts each storage path explicitly. README/mkdocs docs are brought back in sync.

**Tech Stack:** POSIX shell, `uv` + `uvicorn` (FastAPI app `zilpzalp.main:app`), docker-compose, mkdocs-material docs.

## Global Constraints

- Conventional Commits, English (e.g. `feat(dev): add dev server script`). Commit after each task.
- Backend tooling runs from `backend/` (`cd backend && uv run …`). `uv run` may spuriously rewrite `backend/uv.lock` — `git checkout backend/uv.lock` before committing if it appears modified and no dependency changed.
- The dev server is a single uvicorn process — **no `--reload`**. Stop is a plain `kill -TERM <PID>`; no `setsid`/process group.
- Dev server host/port: `127.0.0.1:8000`. Compose host ports: backend **8080**, docs **8081**. Container-internal ports stay 8000.
- Per-dir ignore idiom is exactly two lines — `*` then `!.gitignore` — and lives only in leaf dirs, never an ancestor.
- Do not restore or recreate `demo/` or `backend/config.example.yaml` (both intentionally removed).

---

### Task 1: docker/ runtime skeleton, remove demo/, root .gitignore

**Files:**
- Create: `docker/backend/config/.gitignore`
- Create: `docker/backend/data/inbox/.gitignore`
- Create: `docker/backend/data/error/.gitignore`
- Create: `docker/backend/data/trash/.gitignore`
- Create: `docker/backend/data/cache/.gitignore`
- Create: `docker/backend/data/outbox/.gitignore`
- Delete: `demo/` (whole tree)
- Modify: `.gitignore` (remove demo block, add `/.dev/`)

**Interfaces:**
- Produces: the `docker/backend/{config,data/<sub>}` directories that `docker-compose.yml` (Task 2) bind-mounts, and the `/.dev/` ignore rule that `scripts/devserver.sh` (Task 3) relies on.

- [ ] **Step 1: Create the six skeleton `.gitignore` files**

Each of the six files has the identical two-line content:

```gitignore
*
!.gitignore
```

Create them at these exact paths (the directories are created implicitly):
- `docker/backend/config/.gitignore`
- `docker/backend/data/inbox/.gitignore`
- `docker/backend/data/error/.gitignore`
- `docker/backend/data/trash/.gitignore`
- `docker/backend/data/cache/.gitignore`
- `docker/backend/data/outbox/.gitignore`

- [ ] **Step 2: Remove the demo/ tree**

Run:

```bash
git rm -r demo/
```

Expected: git stages deletion of `demo/data/inbox/beispiel-rechnung.pdf` and `demo/data/inbox/.gitkeep`.

- [ ] **Step 3: Update the root `.gitignore`**

Replace the demo block. Remove these lines (the comment and the eight demo rules):

```gitignore
# Demo: nur das Beispiel-PDF in der Inbox ist versioniert; generierte Ordner nicht.
/demo/data/inbox/*
!/demo/data/inbox/.gitkeep
!/demo/data/inbox/beispiel-rechnung.pdf
/demo/data/error/
/demo/data/processed/
/demo/data/trash/
/demo/data/outbox/
/demo/data/cache/
```

In their place add a single line (the dev-server runtime root):

```gitignore
# Local uv dev-server runtime (scripts/devserver.sh) — never versioned.
/.dev/
```

Leave the existing `/data/`, `/config/`, `/targets/` compose-runtime lines untouched.

- [ ] **Step 4: Verify the skeleton is tracked and demo is gone**

Run:

```bash
git add docker/ .gitignore
git status --short
```

Expected: six `A  docker/backend/.../​.gitignore` additions, the `.gitignore` modification (`M`), and the `demo/...` deletions (`D`). No `beispiel-rechnung.pdf` remains under `docker/`.

- [ ] **Step 5: Verify the ignore idiom works**

Run:

```bash
touch docker/backend/data/inbox/scratch.pdf
git status --porcelain docker/backend/data/inbox/
rm docker/backend/data/inbox/scratch.pdf
```

Expected: **no output** from `git status` for the scratch file (it is ignored), while the dir's `.gitignore` stays tracked.

- [ ] **Step 6: Commit**

```bash
git add -A docker/ .gitignore demo/
git commit -m "refactor(docker): replace demo/ with self-documenting docker/backend runtime skeleton"
```

---

### Task 2: docker-compose ports + per-path mounts

**Files:**
- Modify: `docker-compose.yml`

**Interfaces:**
- Consumes: the `docker/backend/{config,data/<sub>}` dirs from Task 1.
- Produces: backend reachable on host `8080`, docs on host `8081`.

- [ ] **Step 1: Update the backend service (port + volumes)**

In `docker-compose.yml`, the `backend` service currently reads:

```yaml
  backend:
    build:
      context: .
      dockerfile: Dockerfile.backend
    image: zilpzalp-backend
    ports:
      - "8000:8000"
    volumes:
      - ./demo/data:/data
    restart: unless-stopped
```

Replace it with:

```yaml
  backend:
    build:
      context: .
      dockerfile: Dockerfile.backend
    image: zilpzalp-backend
    ports:
      - "8080:8000"
    volumes:
      - ./docker/backend/config:/config
      - ./docker/backend/data/inbox:/data/inbox
      - ./docker/backend/data/error:/data/error
      - ./docker/backend/data/trash:/data/trash
      - ./docker/backend/data/cache:/data/cache
      - ./docker/backend/data/outbox:/data/outbox
    restart: unless-stopped
```

- [ ] **Step 2: Update the docs service port**

In the `docs` service, change:

```yaml
    ports:
      - "8001:8000"
```

to:

```yaml
    ports:
      - "8081:8000"
```

Leave the docs `command`, `target`, and `./mkdocs:/docs` volume unchanged.

- [ ] **Step 3: Validate the compose file**

Run:

```bash
docker compose config >/dev/null && echo OK
```

Expected: `OK` (compose parses and resolves the file). If Docker is unavailable in the environment, instead run `python3 -c "import yaml,sys; yaml.safe_load(open('docker-compose.yml'))" && echo "YAML OK"` and note Docker validation was skipped.

- [ ] **Step 4: Commit**

```bash
git add docker-compose.yml
git commit -m "feat(docker): map host ports 8080/8081 and mount each storage path explicitly"
```

---

### Task 3: dev-server script + permissions + CLAUDE.md

**Files:**
- Create: `scripts/devserver.sh`
- Modify: `.claude/settings.json`
- Modify: `CLAUDE.md`

**Interfaces:**
- Consumes: `/.dev/` ignore rule (Task 1); `backend/config.default.yaml` (existing seed); the app's `_ensure_dirs` which creates `data/*` from `ZILPZALP_PATH_*`.
- Produces: `scripts/devserver.sh {start|stop|status|logs}` serving `http://127.0.0.1:8000`.

- [ ] **Step 1: Create `scripts/devserver.sh`**

Exact content:

```sh
#!/bin/sh
# Dev server controller for the ZilpZalp backend (uv + uvicorn).
#
# Runs a single uvicorn process on 127.0.0.1:8000 with isolated runtime data under
# .dev/backend/, so an agent can bring the app up for manual or Playwright checks and
# tear it down cleanly. No --reload (single process => portable `kill` stop).
set -eu

HOST=127.0.0.1
PORT=8000

# Repo root, resolved from this script's location (scripts/devserver.sh -> repo root).
SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
ROOT=$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)

DEV_DIR="$ROOT/.dev/backend"
CONFIG_DIR="$DEV_DIR/config"
CONFIG_FILE="$CONFIG_DIR/config.yaml"
DATA_DIR="$DEV_DIR/data"
PID_FILE="$DEV_DIR/devserver.pid"
LOG_FILE="$DEV_DIR/devserver.log"
HEALTH_URL="http://$HOST:$PORT/healthz/live"

is_running() {
    [ -f "$PID_FILE" ] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null
}

cmd_start() {
    if is_running; then
        echo "Dev server already up (PID $(cat "$PID_FILE")) at http://$HOST:$PORT"
        return 0
    fi

    mkdir -p "$CONFIG_DIR"
    if [ ! -f "$CONFIG_FILE" ]; then
        cp "$ROOT/backend/config.default.yaml" "$CONFIG_FILE"
    fi

    export ZILPZALP_CONFIG="$CONFIG_FILE"
    export ZILPZALP_PATH_INBOX="$DATA_DIR/inbox"
    export ZILPZALP_PATH_ERROR="$DATA_DIR/error"
    export ZILPZALP_PATH_TRASH="$DATA_DIR/trash"
    export ZILPZALP_PATH_CACHE="$DATA_DIR/cache"
    export ZILPZALP_PATH_OUTBOX="$DATA_DIR/outbox"

    cd "$ROOT/backend"
    uv run uvicorn zilpzalp.main:app --host "$HOST" --port "$PORT" >"$LOG_FILE" 2>&1 &
    echo $! >"$PID_FILE"

    # Health gate: poll until live or ~15s timeout.
    i=0
    while [ "$i" -lt 15 ]; do
        if curl -fsS "$HEALTH_URL" >/dev/null 2>&1; then
            echo "Dev server up at http://$HOST:$PORT"
            return 0
        fi
        i=$((i + 1))
        sleep 1
    done

    echo "Dev server failed to become healthy within 15s; last log lines:" >&2
    tail -n 20 "$LOG_FILE" >&2
    cmd_stop >/dev/null 2>&1 || true
    return 1
}

cmd_stop() {
    if ! is_running; then
        rm -f "$PID_FILE"
        echo "Dev server not running"
        return 0
    fi
    pid=$(cat "$PID_FILE")
    kill -TERM "$pid" 2>/dev/null || true
    i=0
    while [ "$i" -lt 10 ] && kill -0 "$pid" 2>/dev/null; do
        i=$((i + 1))
        sleep 1
    done
    rm -f "$PID_FILE"
    echo "Dev server stopped"
}

cmd_status() {
    if is_running; then
        echo "up (PID $(cat "$PID_FILE")) at http://$HOST:$PORT"
    else
        echo "down"
    fi
}

cmd_logs() {
    [ -f "$LOG_FILE" ] || { echo "no log file yet"; return 0; }
    tail -f "$LOG_FILE"
}

case "${1:-}" in
    start)  cmd_start ;;
    stop)   cmd_stop ;;
    status) cmd_status ;;
    logs)   cmd_logs ;;
    *)
        echo "usage: $0 {start|stop|status|logs}" >&2
        exit 2
        ;;
esac
```

- [ ] **Step 2: Make it executable**

Run:

```bash
chmod +x scripts/devserver.sh
```

- [ ] **Step 3: Start the server and verify health**

Run:

```bash
scripts/devserver.sh start
```

Expected: ends with `Dev server up at http://127.0.0.1:8000` (within ~15s). The files `.dev/backend/config/config.yaml`, `.dev/backend/data/inbox/` (and siblings), `.dev/backend/devserver.pid`, `.dev/backend/devserver.log` now exist.

- [ ] **Step 4: Verify status and idempotent start**

Run:

```bash
scripts/devserver.sh status
scripts/devserver.sh start
```

Expected: `status` prints `up (PID …) at http://127.0.0.1:8000`; the second `start` prints `Dev server already up (PID …)` and does not launch a second process.

- [ ] **Step 5: Stop and verify no orphan**

Run:

```bash
scripts/devserver.sh stop
scripts/devserver.sh status
pgrep -f "uvicorn zilpzalp.main:app" || echo "no orphan"
```

Expected: `Dev server stopped`, then `down`, then `no orphan`.

- [ ] **Step 6: Verify .dev/ is fully ignored, restore uv.lock if needed**

Run:

```bash
git status --porcelain | grep -E "\.dev/" || echo ".dev ignored"
git checkout backend/uv.lock 2>/dev/null || true
```

Expected: `.dev ignored` (nothing under `.dev/` shows up).

- [ ] **Step 7: Add the permission allowlist entries**

In `.claude/settings.json`, inside `permissions.allow`, add these two entries (anywhere in the array, e.g. after the existing `Bash(bash */subagent-driven-development/scripts/*)` line):

```json
      "Bash(scripts/devserver.sh *)",
      "Bash(./scripts/devserver.sh *)",
```

Ensure the JSON stays valid (commas between entries). Verify:

```bash
python3 -c "import json; json.load(open('.claude/settings.json')); print('JSON OK')"
```

Expected: `JSON OK`.

- [ ] **Step 8: Add the backend-location section to CLAUDE.md**

In `CLAUDE.md`, after the `## Working Principles` section (before `## Documentation language`), insert:

```markdown
## Backend & running the app

- The Python backend lives in `backend/` — `uv`, the virtualenv, and `pyproject.toml`
  are all there. Run `uv`, `pytest`, and `uvicorn` from `backend/`
  (e.g. `cd backend && uv run pytest`).
- To run the app for manual or Playwright checks, use the dev-server script from the
  repo root: `scripts/devserver.sh start|stop|status|logs`. It serves on
  <http://127.0.0.1:8000> with isolated runtime data under `.dev/backend/` (gitignored).
```

- [ ] **Step 9: Commit**

```bash
git add scripts/devserver.sh .claude/settings.json CLAUDE.md
git commit -m "feat(dev): add devserver.sh, allowlist it, document backend location"
```

---

### Task 4: Documentation sweep

**Files:**
- Modify: `README.md`
- Modify: `mkdocs/docs/installation.md`
- Modify: `mkdocs/docs/usage.md`
- Modify: `mkdocs/docs/troubleshooting.md`
- Modify: `CONTRIBUTING.md`

**Interfaces:**
- Consumes: the new ports (8080/8081) and `docker/backend/*` paths from Tasks 1–2.

- [ ] **Step 1: README.md — quick start block**

Replace lines 35–50 (the "Quick start" prose, URLs, and "For real use" paragraph). Current:

```markdown
ZilpZalp runs as two containers — the **backend** (web UI + processing) and the
**docs site** — orchestrated by `docker-compose.yml`. The shipped `demo/` folder is
ready to run: a sample invoice already sits in the inbox, so a document shows up in
the queue right away.

```bash
docker compose up -d --build
```

- Web UI: <http://localhost:8000>
- Documentation: <http://localhost:8001>

For real use, edit [`demo/config/config.yaml`](demo/config/config.yaml) and drop your
own PDFs into `demo/data/inbox` — or repoint the volumes in `docker-compose.yml` to
your own host paths. See the
[installation guide](https://elnebuloso.github.io/zilpzalp/installation/) for details.
```

New:

```markdown
ZilpZalp runs as two containers — the **backend** (web UI + processing) and the
**docs site** — orchestrated by `docker-compose.yml`. Compose bind-mounts the runtime
folders under `docker/backend/` (created on first start); the inbox starts empty.

```bash
docker compose up -d --build
```

- Web UI: <http://localhost:8080>
- Documentation: <http://localhost:8081>

For real use, edit `docker/backend/config/config.yaml` (written on first start) and drop
your own PDFs into `docker/backend/data/inbox` — or repoint the volumes in
`docker-compose.yml` to your own host paths. See the
[installation guide](https://elnebuloso.github.io/zilpzalp/installation/) for details.
```

- [ ] **Step 2: installation.md — mount table**

Replace lines 14–23 (intro + table). Current intro says "mounts the bundled `demo/` folder"; the table lists `demo/*` rows incl. the non-existent `demo/config`/`demo/targets`. New:

```markdown
ZilpZalp works exclusively through mounted directories. The Compose setup bind-mounts
each storage path under `docker/backend/` (relative to the repo root); the directories
are created on first start.

| Host folder | Container path | Purpose |
|---|---|---|
| `./docker/backend/config` | `/config` | contains `config.yaml` (the only persistent setting) |
| `./docker/backend/data/inbox` | `/data/inbox` | **watchfolder** — new PDFs land here |
| `./docker/backend/data/error` | `/data/error` | unreadable/faulty PDFs |
| `./docker/backend/data/trash` | `/data/trash` | originals moved here when `originals.when_filed` or `originals.when_removed` is set to `trash` |
| `./docker/backend/data/outbox` | `/data/outbox` | default output target ("Outbox") |
```

- [ ] **Step 3: installation.md — quick start, URLs, healthcheck**

Replace lines 25–46. Current refers to the demo sample and ports 8000/8001. New:

```markdown
## Quick start

Build and start both containers:

```bash
docker compose up -d --build
```

Then open:

- Web UI: <http://localhost:8080> — drop a PDF into `docker/backend/data/inbox` and it appears in the queue
- This documentation: <http://localhost:8081>

Check status:

```bash
docker compose ps
curl -fsS http://localhost:8080/healthz/live
```

Expected: `{"status":"ok"}`.
```

- [ ] **Step 4: installation.md — "Your own documents" section**

Replace lines 48–60. Current refers to `demo/`. New:

```markdown
## Your own documents / production use

For production use, adapt the defaults to your needs:

1. **Adjust the configuration:** edit `docker/backend/config/config.yaml` (written on
   first start) — targets, rules, naming patterns. The paths in it are **container paths**
   (`/data/inbox`, `/targets/finanzen`, …), not host paths — details in
   [Configuration](configuration.md).

2. **Drop in PDFs:** put your own files into `docker/backend/data/inbox`.

3. **Optional custom folders:** instead of `docker/backend/…`, you can mount any host
   paths to the same container paths in `docker-compose.yml`.
```

- [ ] **Step 5: usage.md — port**

In `mkdocs/docs/usage.md` line 3, change `<http://localhost:8000>` to `<http://localhost:8080>`:

```markdown
All operation happens through the web UI at <http://localhost:8080>.
```

- [ ] **Step 6: troubleshooting.md — healthcheck port**

In `mkdocs/docs/troubleshooting.md` line 45, change the curl URL:

```bash
curl -fsS http://localhost:8080/healthz/live  # backend healthy? -> {"status":"ok"}
```

- [ ] **Step 7: CONTRIBUTING.md — ports**

Change lines 27–28:

```markdown
- Web UI: <http://localhost:8080>
- Documentation: <http://localhost:8081>
```

And line 76:

```bash
docker compose up docs   # http://localhost:8081, live-reload
```

- [ ] **Step 8: Verify no stale references remain**

Run:

```bash
grep -rn "demo/" README.md CONTRIBUTING.md mkdocs/docs/ || echo "no demo/ refs"
grep -rn "localhost:8000\|localhost:8001" README.md CONTRIBUTING.md mkdocs/docs/ || echo "no stale ports"
```

Expected: `no demo/ refs` and `no stale ports`.

- [ ] **Step 9: Commit**

```bash
git add README.md CONTRIBUTING.md mkdocs/docs/
git commit -m "docs: sync ports (8080/8081) and docker/backend paths, drop demo/ references"
```

---

### Task 5: Backlog tracking

**Files:**
- Modify: `docs/backlog.md`

**Interfaces:**
- Consumes: this plan's spec link; the resolved-lint commit `6abc1b7`.

- [ ] **Step 1: Add the two Umsetzung rows**

In `docs/backlog.md`, append to the "## Umsetzung" table (after row `| 8 | …`):

```markdown
| 9 | Feinschliff | **Lint-Fix `test_i18n.py`** — ungenutzter `pytest`-Import entfernt, `ruff check .` projektweit grün (war bereits umgesetzt, nur nicht im Backlog erfasst) | ✅ | `6abc1b7` |
| 10 | Feinschliff | **DEV-Server + Docker-Runtime-Layout** — `scripts/devserver.sh` (Port 8000), `.dev/` vs `docker/backend/`-Struktur, compose-Ports 8080/8081 + Einzel-Mounts, `demo/` entfernt, Docs-Sync (Details: [superpowers/specs/2026-06-17-1909-dev-and-docker-runtime-design.md](superpowers/specs/2026-06-17-1909-dev-and-docker-runtime-design.md)) | 🚧 | — |
```

- [ ] **Step 2: Remove the stale lint idea from "Ideen / später"**

Delete this bullet from the "## Ideen / später" list:

```markdown
- **Lint-Fehler in `test_i18n.py` beheben:** Ungenutzter Import `pytest`
  ([backend/tests/test_i18n.py:4](../../backend/tests/test_i18n.py#L4)) — vorbestehender
  Ruff-Fehler (F401), unabhängig vom jeweiligen Feature. Entfernen, damit
  `ruff check .` projektweit grün ist.
```

- [ ] **Step 3: Commit**

```bash
git add docs/backlog.md
git commit -m "docs(backlog): track dev-server/docker-runtime work; record resolved lint fix"
```

- [ ] **Step 4 (on full completion): fill in row 10's SHA**

After this branch is merged, set row 10's Status to ✅ and its Commit to the merge SHA, per the backlog upkeep rule.

---

## Self-Review

**Spec coverage:**
- §1 runtime layout → Task 1 (skeleton + idiom + ignore) and Task 3 (`.dev/` on the fly). ✅
- §2 dev-server script → Task 3. ✅
- §3 compose ports + mounts → Task 2. ✅
- §4 remove demo/ → Task 1. ✅
- §5 CLAUDE.md section → Task 3 Step 8. ✅
- §6 permissions + gitignore → Task 3 Step 7 (permissions), Task 1 Step 3 (`/.dev/`). ✅
- §7 docs sweep → Task 4. ✅
- §8 lint already resolved → no code task; recorded in Task 5. ✅
- §9 config.example already removed → no task (done in `229f5c0`). ✅
- §10 backlog tracking → Task 5. ✅

**Placeholder scan:** No TBD/TODO; every file edit shows exact before/after text and every command shows expected output.

**Type/path consistency:** `scripts/devserver.sh` env paths (`.dev/backend/data/<sub>`, `.dev/backend/config/config.yaml`) match the compose host paths' sibling structure under `docker/backend/`; health URL/port (`127.0.0.1:8000`) consistent across script and CLAUDE.md; compose host ports (8080/8081) consistent across compose, README, installation, usage, troubleshooting, CONTRIBUTING.
