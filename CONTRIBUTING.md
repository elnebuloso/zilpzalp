# Contributing to ZilpZalp

Thanks for your interest in improving ZilpZalp! Contributions of all kinds are
welcome — bug reports, fixes, documentation, and features.

For anything beyond a small fix, please **open an issue first** so we can align on
the approach before you invest time.

## Development setup

**Prerequisites:** Python ≥ 3.12, [uv](https://docs.astral.sh/uv/), and Docker
(for the full stack and integration tests).

Install backend dependencies:

```bash
cd backend
uv sync
```

Run the full app locally (backend + docs site):

```bash
docker compose up -d --build
```

- Web UI: <http://localhost:8080>
- Documentation: <http://localhost:8081>

## Tests & linting

These are the same checks CI runs — please make sure they pass before opening a PR:

```bash
cd backend
uv run ruff check .                  # lint
uv run pytest -m "not integration"   # fast unit tests
```

The full suite includes **integration tests** that need a real JVM (OpenDataLoader)
and are slow:

```bash
uv run pytest                        # everything, including integration
```

## Commit conventions

We use [Conventional Commits](https://www.conventionalcommits.org/) in English, e.g.:

```
fix(watcher): handle PDFs with missing metadata
feat(naming): support custom date patterns
docs(readme): clarify quick start
```

Releases are automated with
[release-please](https://github.com/googleapis/release-please): your commit types
drive the next version and the changelog, so choose `feat:` / `fix:` deliberately.
Note that releases only fire for commits touching `backend/` — changes to docs, CI,
or Docker config do not trigger a release.

## Pull requests

1. Create a branch from `main`.
2. Keep PRs focused — one topic per PR.
3. Make sure lint and tests pass.
4. Open the PR against `main` with a clear description of what and why.

## Documentation changes

End-user docs live under [`mkdocs/`](mkdocs/) and are built with
[mkdocs-material](https://squidfunk.github.io/mkdocs-material/). Preview locally:

```bash
docker compose up docs   # http://localhost:8081, live-reload
```

Pushes to `main` that touch `mkdocs/**` deploy automatically to GitHub Pages
(<https://elnebuloso.github.io/zilpzalp/>).

## For maintainers: milestone workflow

Each milestone is planned and implemented in a fresh session (tracking:
[`docs/mvp/roadmap.md`](docs/mvp/roadmap.md)). Copy-paste prompt — it detects the
next open milestone on its own, nothing to fill in manually:

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

## License

By contributing, you agree that your contributions are licensed under the
[MIT License](LICENSE).
