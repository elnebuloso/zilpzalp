# ZilpZalp

ZilpZalp is a **semi-automatic document filing tool** for self-hosting on your home
network. It watches a folder, reads incoming PDFs, and suggests a clean filename from
date, sender, and document type — **you review, confirm, done**. Local, no cloud.

## Core idea

- **Human in the loop:** ZilpZalp pre-fills what it knows for sure. The final decision
  is always yours.
- **Every date stays visible:** A document often contains several dates (invoice,
  service, due date). ZilpZalp shows **all** detected candidates for you to choose from
  instead of silently picking one in the background.
- **Data-frugal:** No history and no database are created. The watched folder itself is
  the source of truth; the only persistent setting is `config.yaml`.

## How it works

```
Watchfolder → Analysis (date/sender/type) → Suggestion → Review in browser
→ Confirmation → Copy to target folder → Original moved/deleted/kept
```

## Get started

- [Installation](installation.md) — setup with Docker Compose
- [Usage](usage.md) — the review workflow in the browser
- [Configuration](configuration.md) — `config.yaml` in detail
- [Troubleshooting](troubleshooting.md) — operation and common errors

!!! warning "No access protection"
    ZilpZalp has **no login**. It is designed to run inside a trusted home network.
    Do not expose the web UI to the internet unprotected.
