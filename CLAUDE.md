# Agent Guide: ZilpZalp Development

Trivial tasks (one-liners, obvious fixes): just do it.

## Working Principles

- **Think before coding.** State assumptions; if uncertain or ambiguous, ask before
  implementing — don't pick silently. Once the approach is agreed, work autonomously.
- **Simplicity first.** Minimum code that solves the problem. No speculative features,
  abstractions, or error handling for impossible cases. If 200 lines could be 50, rewrite.
- **Surgical changes.** Touch only what the request requires. Match existing style, don't
  refactor what isn't broken. Remove orphans your change creates; mention pre-existing
  dead code, don't delete it unasked.

## Backend & running the app

- The Python backend lives in `backend/` — `uv`, the virtualenv, and `pyproject.toml`
  are all there. Run `uv`, `pytest`, and `uvicorn` from `backend/`
  (e.g. `cd backend && uv run pytest`).
- To run the app for manual or Playwright checks, use the dev-server script from the
  repo root: `scripts/devserver.sh start|stop|status|logs`. It serves on
  <http://127.0.0.1:8000> with isolated runtime data under `.dev/backend/` (gitignored).

## Documentation language

- `README.md` and the mkdocs documentation under `mkdocs/` are written in English.

## Git

- Conventional Commits, English. Example: `fix(auth): handle expired tokens on refresh`
- Stage and commit changes independently after each completed, coherent work step.
- Ask before pushing.
- Never force-push, amend pushed commits, or hard-reset.

## Superpowers skill file naming

- Use `YYYY-MM-DD-HHMM-<short-topic>.md` for Superpowers skill `specs` and `plans` so same-day files sort correctly.
- Do not use `YYYY-MM-DD-<short-topic>.md`.

### example

- `specs/superpowers/specs/2026-06-13-1430-user-authentication.md`
- `docs/superpowers/plans/2026-06-13-1430-user-authentication.md`
