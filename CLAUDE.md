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

## Git

- Conventional Commits, English. Example: `fix(auth): handle expired tokens on refresh`
- Commit und Push selbstständig, sobald ein Arbeitsschritt abgeschlossen ist.
- Never force-push, amend pushed commits, or hard-reset.

# Superpowers skill file naming

Use `YYYY-MM-DD-HHMM-<short-topic>.md` for Superpowers skill `specs` and `plans` so same-day files sort correctly.

# example
specs/superpowers/specs/2026-06-13-1430-user-authentication.md
docs/superpowers/plans/2026-06-13-1430-user-authentication.md

Do not use `YYYY-MM-DD-<short-topic>.md`.
