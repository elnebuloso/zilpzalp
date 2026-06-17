# Installation

ZilpZalp runs as two containers: the **backend** (web UI + processing) and the
**docs site** (this documentation). Both are started via `docker-compose.yml`.

## Requirements

- Docker and Docker Compose v2
- A Linux host (or WSL2). **Note:** On mounted Windows paths (`/mnt/c/…`), filesystem
  events are unreliable — put the watchfolder and target folders on native Linux paths.

## Folders and volumes

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

## Your own documents / production use

For production use, adapt the defaults to your needs:

1. **Adjust the configuration:** edit `docker/backend/config/config.yaml` (written on
   first start) — targets, rules, naming patterns. The paths in it are **container paths**
   (`/data/inbox`, `/targets/finanzen`, …), not host paths — details in
   [Configuration](configuration.md).

2. **Drop in PDFs:** put your own files into `docker/backend/data/inbox`.

3. **Optional custom folders:** instead of `docker/backend/…`, you can mount any host
   paths to the same container paths in `docker-compose.yml`.

## Stop / update

```bash
docker compose down          # stops both containers
docker compose up -d --build # rebuild and start after changes
```

!!! note "Startup behavior"
    On startup ZilpZalp scans the watchfolder once and then picks up new files live via
    filesystem events. An unconfirmed PDF reappears in the queue after a restart — the
    watchfolder is the source of truth.
