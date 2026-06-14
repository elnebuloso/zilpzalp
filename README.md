# zilpzalp

Self-hosted PDF renamer with a human in the loop. Zilpzalp watches a folder, reads incoming PDFs, and suggests clean filenames from date, sender and document type — you review, confirm, done. Docker, local, no cloud.

## Documentation & Quickstart

End-user documentation (installation, usage, configuration, troubleshooting) is built
with mkdocs-material under [`mkdocs/`](mkdocs/) and served as its own container.

```bash
docker compose up -d --build
```

Compose ships with a ready-to-run demo under [`demo/`](demo/) (mounted as the volumes):
a sample invoice already sits in the inbox, so a document shows up in the queue right
away. For real use, edit [`demo/config/config.yaml`](demo/config/config.yaml) and drop
your own PDFs into `demo/data/inbox` (or repoint the volumes in `docker-compose.yml`).

- Web UI: <http://localhost:8000>
- Documentation: <http://localhost:8001>

## Development

### Entwicklung: nächsten Meilenstein bearbeiten

Jeder Meilenstein wird in einer frischen Session geplant und umgesetzt (Tracking: [docs/mvp/roadmap.md](docs/mvp/roadmap.md)). Kopierfertiger Prompt — er erkennt den nächsten Meilenstein selbst, nichts manuell ausfüllen:

````text
Schreibe den Implementierungsplan für den nächsten offenen Meilenstein aus docs/mvp/roadmap.md.

Lies zuerst docs/mvp/roadmap.md und bestimme den nächsten Meilenstein (oberste Zeile mit
Status 📋). Entnimm ihm Name, Scope und die referenzierten §§. Lies die Architektur-Referenz
docs/superpowers/specs/2026-06-13-1435-zilpzalp-mvp-design.md (die genannten §§) sowie den
bereits vorhandenen Code unter backend/src/zilpzalp/, auf dem der Meilenstein aufbaut.

Nutze das superpowers:writing-plans Skill. Bite-sized TDD-Tasks, exakte Pfade, vollständiger
Code/Tests in jedem Schritt. Tech: Python + FastAPI, uv, pytest, src-Layout unter
backend/src/zilpzalp/. Halte dich strikt an den Scope der Roadmap-Zeile und schließe alles
aus, was laut Roadmap erst spätere Meilensteine liefern — frag nach, wenn der Scope unklar ist.

Plan speichern als docs/superpowers/plans/YYYY-MM-DD-HHMM-<kurzname>.md, dann die betreffende
Meilenstein-Zeile in docs/mvp/roadmap.md aktualisieren (Plan-Link, Status 📝).
````

## Optimize `.claude/settings.json`

````shell
/fewer-permission-prompts
````
