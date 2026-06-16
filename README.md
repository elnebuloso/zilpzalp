# ZilpZalp

**Self-hosted PDF renamer with a human in the loop.**

ZilpZalp watches a folder, reads incoming PDFs, and suggests clean filenames from
date, sender, and document type — you review, confirm, done. Local, Docker-based,
no cloud.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Latest release](https://img.shields.io/github/v/release/elnebuloso/zilpzalp?sort=semver)](https://github.com/elnebuloso/zilpzalp/releases)
[![Docker image](https://img.shields.io/badge/Docker%20Hub-elnebuloso%2Fzilpzalp--backend-2496ED?logo=docker&logoColor=white)](https://hub.docker.com/r/elnebuloso/zilpzalp-backend)
[![Documentation](https://img.shields.io/badge/docs-mkdocs--material-526CFE)](https://elnebuloso.github.io/zilpzalp/)

> 📖 **Full documentation:** <https://elnebuloso.github.io/zilpzalp/>

## Why ZilpZalp

- **Human in the loop.** ZilpZalp pre-fills only what it knows for sure. The final
  decision is always yours.
- **Every date stays visible.** A document often carries several dates (invoice,
  service, due date). ZilpZalp surfaces *all* detected candidates for you to pick
  from instead of silently choosing one.
- **Data-frugal.** No history, no database. The watched folder is the single source
  of truth; the only persistent setting is `config.yaml`.

## How it works

```
Watchfolder → Analyze (date / sender / type) → Suggest → Review in browser
→ Confirm → Copy to target folder → Original moved / deleted / kept
```

## Quick start

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

## Documentation

End-user documentation is built with
[mkdocs-material](https://squidfunk.github.io/mkdocs-material/) (sources under
[`mkdocs/`](mkdocs/)) and published at <https://elnebuloso.github.io/zilpzalp/>:

- [Installation](https://elnebuloso.github.io/zilpzalp/installation/) — setup with Docker Compose
- [Usage](https://elnebuloso.github.io/zilpzalp/bedienung/) — the browser review workflow
- [Configuration](https://elnebuloso.github.io/zilpzalp/konfiguration/) — `config.yaml` in detail
- [Troubleshooting](https://elnebuloso.github.io/zilpzalp/fehlerbehebung/) — operation and common errors

> The end-user documentation is currently in **German**.

## Security

⚠️ **ZilpZalp has no authentication.** It is designed to run inside a trusted home
network. Do not expose the web UI to the internet unprotected.

## License

Released under the [MIT License](LICENSE).
