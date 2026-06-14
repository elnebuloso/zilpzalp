# CI-Release-Pipeline (GitHub Actions) — Design

**Backlog:** „CI-Pipeline (GitHub Actions)" aus [docs/backlog.md](../../backlog.md) —
Docker-Image bauen und in den eigenen Docker-Hub-Namespace releasen, mit Semantic
Versioning. Löst den MVP-Scope-Ausschluss „kein CI/CD" bewusst als Post-MVP-Schritt ab.

## Ziel

Automatisches, versioniertes Release des Backend-Docker-Images nach Docker Hub.
Die Versionsnummer wird **aus den Conventional Commits berechnet** (nicht von Hand
getaggt), das Image trägt exakt diese Version.

## Grundsatzentscheidungen

| Entscheidung | Wahl | Begründung |
|---|---|---|
| Versionierung | **Auto aus Commits** via `release-please` | Repo fährt bereits strikt Conventional Commits; Version folgt zwingend den Änderungen, Changelog fällt automatisch ab. |
| Tool | **`release-please`** (Google), nicht `semantic-release` | Reines Python/uv-Repo ohne Node-Toolchain. `release-please` ist eine fertige Action, braucht kein npm und bietet ein menschliches Gate (Release-PR). |
| Umfang | **Nur Release** (kein PR/Branch-Quality-Gate) | Bewusst schlank; Tests laufen als Guard erst beim Release. |
| Images | **Nur Backend** (`Dockerfile.backend`) | Docs-Container bleibt lokal/compose. |
| Test-Guard | **Nur Unit-Tests** (`-m "not integration"`) + `ruff` | Schnelles Feedback, keine JVM im CI nötig. Guard läuft nur, wenn ein Release gecuttet wird. |
| Docker-Tags | **Nur exakte Version** `vX.Y.Z` | Kein bewegliches `latest`, keine `X.Y`/`X`-Aliase — jeder Pull ist explizit gepinnt. |
| Plattform | **`linux/amd64`** | Simpel; arm64 später per buildx nachrüstbar. |

## Image-Koordinaten

- Docker-Hub-Namespace: **`elnebuloso`**
- Repository: **`zilpzalp-backend`** (analog zum compose-Image-Namen; lässt Raum für
  ein späteres `zilpzalp-docs`)
- Voller Ref: `elnebuloso/zilpzalp-backend:vX.Y.Z`

## Ablauf (Release-Fluss)

1. Conventional Commits landen auf `main`.
2. `release-please` liest die Commits seit dem letzten Release und hält einen
   **Release-PR** offen — mit berechneter nächster Version
   (`fix:` → patch, `feat:` → minor, `BREAKING CHANGE` → major), aktualisiertem
   `CHANGELOG.md` und gebumpter `pyproject.toml`-Version.
3. Merge des Release-PR → `release-please` setzt das Tag `vX.Y.Z` + GitHub-Release.
4. **Im selben Workflow-Lauf**: Test-Guard → Docker-Build → Push
   `elnebuloso/zilpzalp-backend:vX.Y.Z`.

**Warum ein einziger Workflow (kein getrenntes `on: push: tags`):** Tags, die der
`GITHUB_TOKEN` erzeugt, lösen keine weiteren Workflows aus (GitHub-Sperre gegen
Rekursion). Der Build hängt daher per Job-`outputs` direkt an `release-please` —
kein PAT nötig.

## Workflow: `.github/workflows/release.yml`

Trigger: `on: push: branches: [main]`

Berechtigungen: `contents: write` (Tags/Releases), `pull-requests: write` (Release-PR).

| Job | Bedingung | Inhalt |
|---|---|---|
| `release-please` | immer | `googleapis/release-please-action`; Outputs: `release_created`, `tag_name` |
| `test` (Guard) | `if: release_created` | `astral-sh/setup-uv`, `uv sync` in `backend/`, `uv run ruff check .`, `uv run pytest -m "not integration"` |
| `build-push` | `needs: [release-please, test]` + `if: release_created` | `docker/login-action` (Docker Hub), `docker/build-push-action` mit `context: .`, `file: Dockerfile.backend`, Tag = `needs.release-please.outputs.tag_name`, `platforms: linux/amd64` |

## release-please-Konfiguration (manifest-basiert, single package)

- `release-please-config.json`:
  - Komponente `backend` mit `release-type: python`
  - `include-component-in-tag: false` → saubere Tags `vX.Y.Z` statt `backend-v…`
- `.release-please-manifest.json`: `{ "backend": "0.1.0" }` (Startpunkt =
  aktuelle `pyproject.toml`-Version)
- `release-type: python` bumpt `backend/pyproject.toml` **und** pflegt
  `backend/CHANGELOG.md` automatisch.

## Secrets (Repo → Settings → Secrets → Actions)

- `DOCKERHUB_USERNAME`
- `DOCKERHUB_TOKEN` — Docker-Hub-Access-Token (nicht das Passwort)

## Mitgenommen

- **Ruff-Fix `test_i18n.py`:** Ungenutzter `pytest`-Import (F401,
  [backend/tests/test_i18n.py:4](../../../backend/tests/test_i18n.py#L4)) wird
  entfernt, sonst kippt der Guard beim ersten Release. Eigenes Backlog-Item, eine
  Zeile — wandert in diese Arbeit, damit der Guard von Tag eins grün ist.

## Non-Goals

- Kein `latest`-Tag, keine `X.Y`/`X`-Aliase.
- Kein Multi-Arch (nur amd64).
- Kein Docs-Image im Release.
- Kein PR-/Branch-Quality-Gate (Tests laufen nur beim Release-Cut).
- Kein manuelles Entkoppeln der `pyproject.toml`-Version — sie wird von
  `release-please` automatisch mitgezogen und bleibt synchron.

## Erstlauf-Hinweis

Beim allerersten Lauf öffnet `release-please` einen initialen Release-PR ausgehend
von `0.1.0`. Die vorgeschlagene Version lässt sich im PR vor dem Merge per
`Release-As:`-Footer überstimmen (z. B. Einstieg bei `0.1.0` oder `1.0.0`).
