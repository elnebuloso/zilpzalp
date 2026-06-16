# MkDocs GitHub Pages Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Die MkDocs-Material-Doku unter `mkdocs/` automatisch als GitHub Page (https://elnebuloso.github.io/zilpzalp/) veröffentlichen, ausgelöst nur bei Änderungen unter `mkdocs/**`.

**Architecture:** Ein eigenständiger GitHub-Actions-Workflow baut die Doku per pip und pusht das Ergebnis mit `mkdocs gh-deploy --force` auf einen `gh-pages`-Branch. Unabhängig vom bestehenden release-please-Flow. Ergänzend wird `site_url` in der mkdocs.yml gesetzt.

**Tech Stack:** GitHub Actions, MkDocs Material 9, Python (pip).

Spec: `docs/superpowers/specs/2026-06-16-1816-mkdocs-github-pages-design.md`

---

### Task 1: `site_url` in mkdocs.yml ergänzen

**Files:**
- Modify: `mkdocs/mkdocs.yml`

- [ ] **Step 1: `site_url` direkt unter `site_description` einfügen**

Die Datei beginnt aktuell mit:

```yaml
site_name: ZilpZalp — Dokumentation
site_description: Halb-automatische Dokumentenablage mit Mensch in der Schleife
docs_dir: docs
```

Daraus wird:

```yaml
site_name: ZilpZalp — Dokumentation
site_description: Halb-automatische Dokumentenablage mit Mensch in der Schleife
site_url: https://elnebuloso.github.io/zilpzalp/
docs_dir: docs
```

- [ ] **Step 2: Build lokal mit --strict verifizieren**

Run: `docker compose run --rm --no-deps docs build --strict`
Expected: Build endet mit `INFO - Documentation built in ...`, kein Fehler. (Der `docs`-Service nutzt `squidfunk/mkdocs-material:9` und mountet `./mkdocs` nach `/docs`.)

- [ ] **Step 3: Commit**

```bash
git add mkdocs/mkdocs.yml
git commit -m "docs(mkdocs): set site_url for github pages"
```

---

### Task 2: GitHub-Actions-Workflow für Pages-Deploy

**Files:**
- Create: `.github/workflows/docs.yml`

- [ ] **Step 1: Workflow-Datei anlegen**

Inhalt von `.github/workflows/docs.yml`:

```yaml
name: docs

on:
  push:
    branches: [main]
    paths:
      - 'mkdocs/**'
  workflow_dispatch:

permissions:
  contents: write

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v6

      - name: Configure Git credentials
        run: |
          git config user.name "github-actions[bot]"
          git config user.email "41898282+github-actions[bot]@users.noreply.github.com"

      - uses: actions/setup-python@v5
        with:
          python-version: 3.x

      - run: echo "cache_id=$(date --utc '+%V')" >> "$GITHUB_ENV"

      - uses: actions/cache@v4
        with:
          key: mkdocs-material-${{ env.cache_id }}
          path: .cache
          restore-keys: |
            mkdocs-material-

      - run: pip install "mkdocs-material>=9,<10"

      - run: mkdocs gh-deploy --force --strict -f mkdocs/mkdocs.yml
```

- [ ] **Step 2: YAML-Syntax verifizieren**

Run: `python -c "import yaml,sys; yaml.safe_load(open('.github/workflows/docs.yml')); print('ok')"`
Expected: `ok`

- [ ] **Step 3: Commit**

```bash
git add .github/workflows/docs.yml
git commit -m "ci(docs): deploy mkdocs to github pages on docs changes"
```

---

### Task 3: Push & einmaliges Aktivieren von Pages

**Files:** keine.

- [ ] **Step 1: Branch-Status prüfen und pushen**

Run: `git status && git push`
Expected: `main` ist mit origin aktuell, Push erfolgreich. (Auf `main` wird gemäß CLAUDE.md autonom committet und gepusht; falls feature-branch genutzt wurde, stattdessen PR.)

- [ ] **Step 2: Workflow-Run beobachten**

Run: `gh run list --workflow=docs.yml`
Expected: Ein Run für `docs` erscheint und endet mit `completed / success`. (Falls der Trigger nicht griff, weil der Push keine `mkdocs/**`-Änderung enthielt: `gh workflow run docs.yml`.)

- [ ] **Step 3: gh-pages-Branch verifizieren**

Run: `git ls-remote --heads origin gh-pages`
Expected: Eine Zeile mit `refs/heads/gh-pages` — der Branch wurde durch `gh-deploy` erstellt.

- [ ] **Step 4: GitHub Pages aktivieren (manuell, durch den User)**

In GitHub: *Settings → Pages → Source = „Deploy from a branch" → Branch `gh-pages` / `root` → Save*.
Danach ist die Doku unter https://elnebuloso.github.io/zilpzalp/ erreichbar (erster Build dauert ein paar Minuten). Dieser Schritt ist nicht per Code automatisierbar.

---

## Self-Review

- **Spec coverage:** Mechanik (Task 2), Trigger mit `mkdocs/**` + `workflow_dispatch` (Task 2), Job-Schritte inkl. pip-Pin `>=9,<10`, Cache, `--force --strict -f` (Task 2), `permissions: contents: write` (Task 2), `site_url` (Task 1), einmaliger Pages-Schritt (Task 3). Alle Spec-Punkte abgedeckt.
- **Placeholder scan:** Keine TBD/TODO; alle Inhalte konkret.
- **Type consistency:** Pfade konsistent (`mkdocs/mkdocs.yml`, `.github/workflows/docs.yml`); Workflow-Name `docs.yml` durchgängig in `gh run list` / `gh workflow run`.
