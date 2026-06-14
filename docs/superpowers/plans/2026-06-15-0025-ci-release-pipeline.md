# CI-Release-Pipeline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Automatisches, versioniertes Release des Backend-Docker-Images nach Docker Hub — Version aus Conventional Commits via `release-please`, Image-Tag = exakte Semver.

**Architecture:** Ein einziger GitHub-Actions-Workflow auf `push: main`. Job 1 (`release-please`) pflegt einen Release-PR und cuttet beim Merge Tag + Release. Nur wenn dabei ein Release entsteht, laufen Job 2 (Test-Guard: ruff + Unit-Tests) und Job 3 (Docker-Build + Push) im selben Lauf — per Job-`outputs` verkettet, damit die `GITHUB_TOKEN`-Sperre gegen Workflow-Rekursion nicht greift.

**Tech Stack:** GitHub Actions, `release-please` (manifest-Modus, `release-type: python`), `uv`, `ruff`, `pytest`, Docker Buildx, Docker Hub.

Spec: [docs/superpowers/specs/2026-06-15-0025-ci-release-pipeline-design.md](../specs/2026-06-15-0025-ci-release-pipeline-design.md)

---

## File Structure

- Create: `.github/workflows/release.yml` — der Release-Workflow (3 Jobs).
- Create: `release-please-config.json` — release-please-Konfiguration (single package `backend`, python).
- Create: `.release-please-manifest.json` — aktueller Versionsstand pro Paket.
- Modify: `backend/tests/test_i18n.py:4` — ungenutzten `import pytest` entfernen (sonst kippt der ruff-Guard).
- Modify: `docs/backlog.md` — Zeile #5 bei Abschluss auf ✅ + Merge-Commit setzen.

**Validierungsgrenze:** GitHub Actions lässt sich lokal nicht voll ausführen (kein `act`/`actionlint` vorhanden). Pro Task validieren wir Syntax (YAML/JSON parsen) und Logik per Review. Der echte End-to-End-Beweis ist der erste `push` auf `main`: `release-please` öffnet dann einen Release-PR (siehe Task 5).

---

### Task 1: Ruff-Fix in test_i18n.py (Guard-Voraussetzung)

**Files:**
- Modify: `backend/tests/test_i18n.py:4`

- [ ] **Step 1: Ausgangslage als Fehler bestätigen**

Run: `cd backend && uv run ruff check .`
Expected: FAIL — `F401 [*] 'pytest' imported but unused` in `tests/test_i18n.py:4`.

- [ ] **Step 2: Ungenutzten Import entfernen**

In `backend/tests/test_i18n.py` die Zeile `import pytest` (Zeile 4) **und** die unmittelbar folgende Leerzeile löschen, sodass der Importblock so aussieht:

```python
import json
from pathlib import Path

from zilpzalp.web import i18n

LOCALES = Path(i18n.__file__).parent / "locales"
```

- [ ] **Step 3: Ruff grün verifizieren**

Run: `cd backend && uv run ruff check .`
Expected: PASS — `All checks passed!`

- [ ] **Step 4: Unit-Tests laufen (keine Regression)**

Run: `cd backend && uv run pytest -m "not integration"`
Expected: PASS (alle gesammelten Tests grün; `integration`-markierte werden deselektiert).

- [ ] **Step 5: Commit**

```bash
git add backend/tests/test_i18n.py
git commit -m "style(tests): remove unused pytest import in test_i18n"
```

---

### Task 2: release-please-Konfiguration + Manifest

**Files:**
- Create: `release-please-config.json`
- Create: `.release-please-manifest.json`

- [ ] **Step 1: Config-Datei anlegen**

`release-please-config.json` (Repo-Wurzel):

```json
{
  "$schema": "https://raw.githubusercontent.com/googleapis/release-please/main/schemas/config.json",
  "include-component-in-tag": false,
  "packages": {
    "backend": {
      "release-type": "python",
      "package-name": "zilpzalp"
    }
  }
}
```

Bedeutung: Paketpfad `backend/` (enthält `pyproject.toml`), `release-type: python` bumpt `backend/pyproject.toml` und pflegt `backend/CHANGELOG.md`. `include-component-in-tag: false` erzeugt saubere Tags `vX.Y.Z` statt `backend-vX.Y.Z`.

- [ ] **Step 2: Manifest-Datei anlegen**

`.release-please-manifest.json` (Repo-Wurzel) — Startpunkt = aktuelle `pyproject.toml`-Version:

```json
{
  "backend": "0.1.0"
}
```

- [ ] **Step 3: JSON-Syntax beider Dateien verifizieren**

Run: `python -c "import json; json.load(open('release-please-config.json')); json.load(open('.release-please-manifest.json')); print('JSON ok')"`
Expected: `JSON ok`

- [ ] **Step 4: Konsistenz-Check**

Der Paketschlüssel ist in beiden Dateien identisch `backend`, und `0.1.0` entspricht `version` in `backend/pyproject.toml`.

Run: `grep -n '^version' backend/pyproject.toml`
Expected: `version = "0.1.0"`

- [ ] **Step 5: Commit**

```bash
git add release-please-config.json .release-please-manifest.json
git commit -m "ci: add release-please config and manifest for backend"
```

---

### Task 3: Release-Workflow

**Files:**
- Create: `.github/workflows/release.yml`

- [ ] **Step 1: Workflow-Datei anlegen**

`.github/workflows/release.yml`:

```yaml
name: release

on:
  push:
    branches: [main]

permissions:
  contents: write
  pull-requests: write

jobs:
  release-please:
    runs-on: ubuntu-latest
    outputs:
      release_created: ${{ steps.release.outputs.release_created }}
      tag_name: ${{ steps.release.outputs.tag_name }}
    steps:
      - uses: googleapis/release-please-action@v4
        id: release
        with:
          token: ${{ secrets.GITHUB_TOKEN }}

  test:
    needs: release-please
    if: ${{ needs.release-please.outputs.release_created == 'true' }}
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: backend
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v5
      - run: uv sync --frozen
      - run: uv run ruff check .
      - run: uv run pytest -m "not integration"

  build-push:
    needs: [release-please, test]
    if: ${{ needs.release-please.outputs.release_created == 'true' }}
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: docker/setup-buildx-action@v3
      - uses: docker/login-action@v3
        with:
          username: ${{ secrets.DOCKERHUB_USERNAME }}
          password: ${{ secrets.DOCKERHUB_TOKEN }}
      - uses: docker/build-push-action@v6
        with:
          context: .
          file: Dockerfile.backend
          platforms: linux/amd64
          push: true
          tags: elnebuloso/zilpzalp-backend:${{ needs.release-please.outputs.tag_name }}
```

Erläuterungen:
- `release_created`/`tag_name` sind String-Outputs; der `== 'true'`-Vergleich gated Job 2 & 3.
- Test-Job läuft mit `working-directory: backend`, damit `uv sync`/`ruff`/`pytest` die Backend-`pyproject.toml` + `uv.lock` nutzen.
- Build-Job nutzt `context: .` (Repo-Wurzel), weil `Dockerfile.backend` Pfade wie `backend/pyproject.toml` relativ zur Wurzel kopiert.
- Image-Tag = `tag_name` (`vX.Y.Z`) → kein `latest`, nur exakte Version.

- [ ] **Step 2: YAML-Syntax verifizieren**

Run: `python -c "import yaml; yaml.safe_load(open('.github/workflows/release.yml')); print('YAML ok')"`
Expected: `YAML ok`
(Falls `yaml` fehlt: `uv run --with pyyaml python -c "..."`.)

- [ ] **Step 3: Logik-Review gegen Spec**

Prüfen (Augenschein): drei Jobs, korrekte `needs`/`if`-Verkettung, Secrets-Namen `DOCKERHUB_USERNAME`/`DOCKERHUB_TOKEN`, `file: Dockerfile.backend`, Tag-Ausdruck nutzt `needs.release-please.outputs.tag_name`.

- [ ] **Step 4: Commit**

```bash
git add .github/workflows/release.yml
git commit -m "ci: add release-please-driven docker release workflow"
```

---

### Task 4: Push + Backlog-Vorbereitung

**Files:** —

- [ ] **Step 1: Branch pushen**

```bash
git push
```

- [ ] **Step 2: Voraussetzungen für den ersten Lauf dokumentieren (an den User melden, nicht ausführen)**

Der User muss vor dem ersten echten Release in GitHub anlegen:
- Repo-Secrets `DOCKERHUB_USERNAME` und `DOCKERHUB_TOKEN` (Docker-Hub-Access-Token).
- Docker-Hub-Repository `elnebuloso/zilpzalp-backend`.

Diese Schritte kann der Agent nicht durchführen — explizit als offene Aktion an den User übergeben.

---

### Task 5: End-to-End-Verifikation (nach Merge auf main)

**Files:**
- Modify: `docs/backlog.md`

Hinweis: Diese Verifikation erfolgt **nach** dem Merge dieser Arbeit auf `main` und erfordert die in Task 4 genannten Secrets/Repos. Sie ist Teil des Abschlusses, kein lokaler Schritt.

- [ ] **Step 1: ersten release-please-Lauf prüfen**

Nach dem Push auf `main`: im GitHub-Actions-Tab läuft `release` → Job `release-please` öffnet einen Release-PR (Titel z. B. „chore(main): release 0.x.y") mit Changelog-Vorschlag. Die Jobs `test`/`build-push` werden in diesem Lauf übersprungen (`release_created == false`).

- [ ] **Step 2: optional Startversion festlegen**

Falls die vorgeschlagene Version nicht passt, im Release-PR per Footer `Release-As: 0.1.0` (oder gewünschte Version) im letzten Commit steuern.

- [ ] **Step 3: Release-PR mergen und Build beobachten**

Merge des Release-PR → neuer `release`-Lauf: `release-please` setzt Tag `vX.Y.Z`, dann laufen `test` (ruff + Unit-Tests) und `build-push`. Erwartetes Ergebnis: Image `elnebuloso/zilpzalp-backend:vX.Y.Z` liegt auf Docker Hub.

- [ ] **Step 4: Backlog abschließen**

In `docs/backlog.md` Zeile #5: Status auf ✅, Spalte `Commit` = Merge-Commit-SHA dieser Pipeline-Arbeit eintragen. Commit:

```bash
git add docs/backlog.md
git commit -m "docs(backlog): mark CI-Release-Pipeline done"
git push
```

---

## Self-Review

**Spec coverage:**
- Auto-Semver aus Conventional Commits → Task 2 (release-please python) + Task 3 (Job 1). ✓
- Nur Backend-Image, `Dockerfile.backend` → Task 3 (build-push). ✓
- Test-Guard nur Unit-Tests + ruff → Task 3 (Job 2). ✓
- Nur exakte Version `vX.Y.Z`, kein `latest` → Task 3 (Tag-Ausdruck), Task 2 (`include-component-in-tag: false`). ✓
- Single Workflow wg. GITHUB_TOKEN-Sperre → Task 3 (`needs`/`outputs`). ✓
- pyproject-Version automatisch gebumpt → Task 2 (`release-type: python`). ✓
- Ruff-Fix `test_i18n.py` mitgenommen → Task 1. ✓
- Secrets/Docker-Hub-Repo als User-Aktion → Task 4. ✓
- Erstlauf-/Release-As-Hinweis → Task 5. ✓

**Placeholder scan:** Keine TBD/TODO; jeder Code-Step zeigt vollständigen Inhalt.

**Type/Name consistency:** Paketschlüssel `backend` identisch in config + manifest; Output-Namen `release_created`/`tag_name` identisch zwischen Job-Definition und `needs`-Referenzen; Secrets-Namen identisch zwischen Workflow und Task-4-Doku; Image-Repo `elnebuloso/zilpzalp-backend` identisch zwischen Spec, Workflow und Backlog-Zeile.
