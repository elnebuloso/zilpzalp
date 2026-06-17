# ZilpZalp

**Self-hosted PDF renamer with a human in the loop.**

ZilpZalp watches a folder, reads incoming PDFs, and suggests clean filenames from
date, sender, and document type — you review, confirm, done. Local, Docker-based,
no cloud.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Latest release](https://badgen.net/github/release/elnebuloso/zilpzalp/stable)](https://github.com/elnebuloso/zilpzalp/releases)
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

## Documentation

End-user documentation is built with
[mkdocs-material](https://squidfunk.github.io/mkdocs-material/) (sources under
[`mkdocs/`](mkdocs/)) and published at <https://elnebuloso.github.io/zilpzalp/>:

- [Installation](https://elnebuloso.github.io/zilpzalp/installation/) — setup with Docker Compose
- [Usage](https://elnebuloso.github.io/zilpzalp/usage/) — the browser review workflow
- [Configuration](https://elnebuloso.github.io/zilpzalp/configuration/) — `config.yaml` in detail
- [Troubleshooting](https://elnebuloso.github.io/zilpzalp/troubleshooting/) — operation and common errors

## Security

⚠️ **ZilpZalp has no authentication.** It is designed to run inside a trusted home
network. Do not expose the web UI to the internet unprotected.

## Contributing

Contributions are welcome — see [CONTRIBUTING.md](CONTRIBUTING.md) for the
development setup, tests, and commit conventions.

## License

Released under the [MIT License](LICENSE).
