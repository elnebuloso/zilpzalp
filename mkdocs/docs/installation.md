# Installation

ZilpZalp runs as two containers: the **backend** (web UI + processing) and the
**docs site** (this documentation). Both are started via `docker-compose.yml`.

## Requirements

- Docker and Docker Compose v2
- A Linux host (or WSL2). **Note:** On mounted Windows paths (`/mnt/c/…`), filesystem
  events are unreliable — put the watchfolder and target folders on native Linux paths.

## Folders and volumes

ZilpZalp works exclusively through mounted directories. By default the Compose setup
mounts the bundled `demo/` folder (relative to the repo root):

| Host folder | Container path | Purpose |
|---|---|---|
| `./demo/config` | `/config` | contains `config.yaml` (the only persistent setting) |
| `./demo/data/inbox` | `/data/inbox` | **watchfolder** — new PDFs land here |
| `./demo/data/error` | `/data/error` | unreadable/faulty PDFs |
| `./demo/data/trash` | `/data/trash` | originals moved here when `originals.when_filed` or `originals.when_removed` is set to `trash` |
| `./demo/targets` | `/targets` | target folders for filed documents |

## Quick start (demo)

The `demo/` folder is ready to run and already contains a sample invoice in the inbox.
Just build and start:

```bash
docker compose up -d --build
```

Then open:

- Web UI: <http://localhost:8000> — the sample invoice shows up in the queue right away
- This documentation: <http://localhost:8001>

Check status:

```bash
docker compose ps
curl -fsS http://localhost:8000/healthz/live
```

Expected: `{"status":"ok"}`.

## Your own documents / production use

For production use, adapt the demo to your needs:

1. **Adjust the configuration:** edit [`demo/config/config.yaml`](https://github.com/elnebuloso/zilpzalp/blob/main/demo/config/config.yaml)
   (targets, rules, naming patterns). The paths in it are **container paths**
   (`/data/inbox`, `/targets/finanzen`, …), not host paths — details in
   [Configuration](configuration.md).

2. **Drop in PDFs:** put your own files into `demo/data/inbox`.

3. **Optional custom folders:** instead of `demo/`, you can mount any host paths to the
   same container paths in `docker-compose.yml`.

## Stop / update

```bash
docker compose down          # stops both containers
docker compose up -d --build # rebuild and start after changes
```

!!! note "Startup behavior"
    On startup ZilpZalp scans the watchfolder once and then picks up new files live via
    filesystem events. An unconfirmed PDF reappears in the queue after a restart — the
    watchfolder is the source of truth.
