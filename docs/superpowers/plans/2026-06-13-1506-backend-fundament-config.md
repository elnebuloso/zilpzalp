# Backend-Fundament + Config — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Scaffold the `backend/` Python package (uv, src-layout) and implement `config.py`, which loads `config.yaml`, validates it, and aborts startup with a clear error message when the config is invalid.

**Architecture:** A single `Config` Pydantic v2 model owns all validation. `load_config(path)` reads the YAML file, builds the model, and translates any `pydantic.ValidationError`, YAML error, or read error into one readable `ConfigError`. A minimal FastAPI app loads the config in its `lifespan` hook on startup, so an invalid config aborts the boot with that clear message; a `/health` route proves the app runs with a valid config.

**Tech Stack:** Python 3.12, FastAPI, Pydantic v2, PyYAML, uv (tooling/venv), pytest, ruff. src-layout under `backend/src/zilpzalp/`.

**Scope boundary (this milestone only):** uv/pyproject/src-layout scaffold + `config.py` (load + validate + clear startup error) + a minimal FastAPI app with `/health`. **Not in scope:** watcher, queue, extractor, analyzer, suggestion, processor, UI, saving config back to disk. The `rules` block is loaded but kept as an opaque `list[dict]` — its schema is consumed by the analyzer/suggestion engine in Milestone 2, so modeling it now would be speculative.

**Prerequisites & conventions:**
- `uv` is installed (`uv --version` → `0.11.x`). `uv run` auto-syncs the venv from `pyproject.toml` on first use, so no manual `uv sync` is required before commands.
- **All commands below run from the `backend/` directory** unless a path says otherwise.
- Run `uv run ruff check .` before each commit; fix lints before committing.

**Validation rules `config.py` enforces (reference: Design-Spec §5):**
1. File is readable and is valid YAML containing a mapping.
2. `paths.watchfolder` and `paths.error_folder` exist and are directories.
3. `original_handling` ∈ {`move`, `delete`, `keep`}; if `move`, `paths.processed_folder` is required and must be an existing directory.
4. `summary_mode` ∈ {`always`, `on_conflict`, `never`}.
5. `default_pattern` and every `patterns[].template` use only the known placeholders `{date}`, `{sender}`, `{doctype}`, `{description}`.
6. `date_format` contains a strftime directive (a `%`).
7. Every optional `date_patterns[].regex` compiles as a regular expression.

---

## File Structure

| File | Responsibility |
|---|---|
| `backend/pyproject.toml` | Project metadata, runtime deps (fastapi, pydantic, pyyaml), dev deps (pytest, httpx, ruff), build-system (hatchling, src-layout), pytest + ruff config. |
| `backend/.gitignore` additions (repo-root `.gitignore`) | Ignore Python/uv artifacts and the local `config.yaml`. |
| `backend/config.example.yaml` | Documented sample config mirroring Design-Spec §5; copy to `config.yaml` for local runs. |
| `backend/src/zilpzalp/__init__.py` | Package marker + `__version__`. |
| `backend/src/zilpzalp/config.py` | `Config` model, all validators, `ConfigError`, `load_config(path)`. |
| `backend/src/zilpzalp/main.py` | FastAPI app, `lifespan` startup config load, `/health` route, config-path resolution. |
| `backend/tests/conftest.py` | Shared `valid_config` and `write_config` fixtures. |
| `backend/tests/test_smoke.py` | Imports the package (scaffold smoke test). |
| `backend/tests/test_config.py` | All config load/validation tests. |
| `backend/tests/test_main.py` | Startup + `/health` tests. |

---

## Task 1: Scaffold the backend package

**Files:**
- Create: `backend/pyproject.toml`
- Create: `backend/src/zilpzalp/__init__.py`
- Create: `backend/tests/test_smoke.py`
- Create: `backend/config.example.yaml`
- Modify: `.gitignore` (repo root)

- [ ] **Step 1: Create `backend/pyproject.toml`**

```toml
[project]
name = "zilpzalp"
version = "0.1.0"
description = "Halb-automatische Dokumentenablage"
requires-python = ">=3.12"
dependencies = [
    "fastapi>=0.115",
    "pydantic>=2.7",
    "pyyaml>=6.0",
]

[dependency-groups]
dev = [
    "pytest>=8.2",
    "httpx>=0.27",
    "ruff>=0.5",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/zilpzalp"]

[tool.pytest.ini_options]
testpaths = ["tests"]

[tool.ruff]
line-length = 100
src = ["src", "tests"]
```

- [ ] **Step 2: Create `backend/src/zilpzalp/__init__.py`**

```python
__version__ = "0.1.0"
```

- [ ] **Step 3: Create `backend/tests/test_smoke.py`**

```python
def test_package_imports():
    import zilpzalp

    assert zilpzalp.__version__ == "0.1.0"
```

- [ ] **Step 4: Create `backend/config.example.yaml`**

```yaml
# Beispielkonfiguration für ZilpZalp. Für lokale Läufe nach config.yaml kopieren
# und die Pfade an existierende Verzeichnisse anpassen.
paths:
  watchfolder: /data/inbox
  error_folder: /data/error
  processed_folder: /data/processed   # nur erforderlich bei original_handling: move

original_handling: move        # move | delete | keep
summary_mode: on_conflict      # always | on_conflict | never

default_pattern: "{date}__{sender}_{doctype}_{description}"
date_format: "%Y-%m-%d"

# Optional: zusätzliche Datums-Matcher für Sonderfälle (additiv zur eingebauten Erkennung).
date_patterns:
  - label: leistungsdatum
    regex: 'Leistungsdatum:\s*(\d{2}\.\d{2}\.\d{4})'

targets:
  - name: Finanzen
    path: /targets/finanzen
    default: false

patterns:
  - name: standard
    template: "{date}__{sender}_{doctype}_{description}"

rules:
  - name: Stromrechnung Stadtwerke
    match:
      sender_contains: "Stadtwerke"
      keywords_any: ["Stromabschlag", "Abschlag"]
    apply:
      sender: "Stadtwerke"
      doctype: "Rechnung"
      description: "Stromabschlag"
      pattern: standard
      preferred_date: rechnungsdatum
      targets: ["Finanzen"]
```

- [ ] **Step 5: Append Python/uv ignores to repo-root `.gitignore`**

The repo-root `.gitignore` currently contains only `.idea`. Append:

```gitignore
__pycache__/
*.py[cod]
.venv/
.pytest_cache/
.ruff_cache/
backend/config.yaml
```

- [ ] **Step 6: Sync and run the smoke test**

Run (from `backend/`):
```bash
uv run pytest tests/test_smoke.py -v
```
Expected: `uv` resolves/installs deps, then `1 passed`.

- [ ] **Step 7: Lint**

Run (from `backend/`):
```bash
uv run ruff check .
```
Expected: `All checks passed!`

- [ ] **Step 8: Commit**

```bash
git add backend ../.gitignore
git commit -m "chore(backend): scaffold uv/src-layout python package"
```

---

## Task 2: Config model + basic loader

Defines the typed `Config` model (structure, types, enums via `Literal`) and a minimal `load_config` that reads YAML and builds the model. No custom validators or error wrapping yet — those come in later tasks.

**Files:**
- Create: `backend/tests/conftest.py`
- Create: `backend/tests/test_config.py`
- Create: `backend/src/zilpzalp/config.py`

- [ ] **Step 1: Create shared fixtures in `backend/tests/conftest.py`**

```python
import pytest
import yaml


@pytest.fixture
def valid_config(tmp_path):
    """A complete, valid config dict whose paths point at real temp dirs."""
    for sub in ("inbox", "error", "processed", "finanzen"):
        (tmp_path / sub).mkdir()
    return {
        "paths": {
            "watchfolder": str(tmp_path / "inbox"),
            "error_folder": str(tmp_path / "error"),
            "processed_folder": str(tmp_path / "processed"),
        },
        "original_handling": "move",
        "summary_mode": "on_conflict",
        "default_pattern": "{date}__{sender}_{doctype}_{description}",
        "date_format": "%Y-%m-%d",
        "date_patterns": [],
        "targets": [
            {"name": "Finanzen", "path": str(tmp_path / "finanzen"), "default": False}
        ],
        "patterns": [
            {"name": "standard", "template": "{date}__{sender}_{doctype}_{description}"}
        ],
        "rules": [],
    }


@pytest.fixture
def write_config(tmp_path):
    """Write a config dict to <tmp_path>/config.yaml and return its path."""

    def _write(data):
        path = tmp_path / "config.yaml"
        path.write_text(yaml.safe_dump(data), encoding="utf-8")
        return path

    return _write
```

- [ ] **Step 2: Write the failing test in `backend/tests/test_config.py`**

```python
from zilpzalp.config import Config, load_config


def test_load_valid_config(valid_config, write_config):
    path = write_config(valid_config)

    cfg = load_config(path)

    assert isinstance(cfg, Config)
    assert cfg.original_handling == "move"
    assert cfg.summary_mode == "on_conflict"
    assert cfg.date_format == "%Y-%m-%d"
    assert cfg.paths.watchfolder.name == "inbox"
    assert cfg.targets[0].name == "Finanzen"
    assert cfg.patterns[0].template == "{date}__{sender}_{doctype}_{description}"
```

- [ ] **Step 3: Run test to verify it fails**

Run (from `backend/`):
```bash
uv run pytest tests/test_config.py::test_load_valid_config -v
```
Expected: FAIL — `ModuleNotFoundError: No module named 'zilpzalp.config'`.

- [ ] **Step 4: Create `backend/src/zilpzalp/config.py`**

```python
from __future__ import annotations

from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel


class ConfigError(Exception):
    """Raised when config.yaml is missing, unparseable, or invalid."""


class Paths(BaseModel):
    watchfolder: Path
    error_folder: Path
    processed_folder: Path | None = None


class Target(BaseModel):
    name: str
    path: Path
    default: bool = False


class Pattern(BaseModel):
    name: str
    template: str


class DatePattern(BaseModel):
    label: str
    regex: str


class Config(BaseModel):
    paths: Paths
    original_handling: Literal["move", "delete", "keep"]
    summary_mode: Literal["always", "on_conflict", "never"]
    default_pattern: str
    date_format: str
    date_patterns: list[DatePattern] = []
    targets: list[Target] = []
    patterns: list[Pattern] = []
    # rules are consumed by the analyzer/suggestion engine (Milestone 2);
    # kept opaque here on purpose.
    rules: list[dict] = []


def load_config(path: Path) -> Config:
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    return Config(**data)
```

- [ ] **Step 5: Run test to verify it passes**

Run (from `backend/`):
```bash
uv run pytest tests/test_config.py::test_load_valid_config -v
```
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add backend
git commit -m "feat(config): load and parse config.yaml into a typed model"
```

---

## Task 3: Wrap load/parse errors in a clear `ConfigError`

Translate unreadable files, invalid YAML, non-mapping YAML, and Pydantic `ValidationError` into a single readable `ConfigError`.

**Files:**
- Modify: `backend/src/zilpzalp/config.py`
- Test: `backend/tests/test_config.py`

- [ ] **Step 1: Write the failing tests** (append to `backend/tests/test_config.py`)

```python
import pytest

from zilpzalp.config import ConfigError


def test_missing_file_raises_config_error(tmp_path):
    with pytest.raises(ConfigError, match="kann nicht gelesen werden"):
        load_config(tmp_path / "does-not-exist.yaml")


def test_invalid_yaml_raises_config_error(tmp_path):
    path = tmp_path / "config.yaml"
    path.write_text("paths: [unbalanced\n", encoding="utf-8")

    with pytest.raises(ConfigError, match="kein gültiges YAML"):
        load_config(path)


def test_non_mapping_yaml_raises_config_error(tmp_path):
    path = tmp_path / "config.yaml"
    path.write_text("- just\n- a\n- list\n", encoding="utf-8")

    with pytest.raises(ConfigError, match="YAML-Mapping"):
        load_config(path)


def test_invalid_enum_raises_config_error(valid_config, write_config):
    valid_config["original_handling"] = "bogus"
    path = write_config(valid_config)

    with pytest.raises(ConfigError) as exc:
        load_config(path)
    assert "original_handling" in str(exc.value)


def test_missing_required_field_raises_config_error(valid_config, write_config):
    del valid_config["paths"]
    path = write_config(valid_config)

    with pytest.raises(ConfigError) as exc:
        load_config(path)
    assert "paths" in str(exc.value)
```

- [ ] **Step 2: Run tests to verify they fail**

Run (from `backend/`):
```bash
uv run pytest tests/test_config.py -v -k "config_error"
```
Expected: FAIL — raw `FileNotFoundError` / `yaml.YAMLError` / `pydantic.ValidationError` raised instead of `ConfigError`.

- [ ] **Step 3: Replace `load_config` and add the formatter in `backend/src/zilpzalp/config.py`**

Update the imports line `from pydantic import BaseModel` to:
```python
from pydantic import BaseModel, ValidationError
```

Replace the `load_config` function with:
```python
def load_config(path: Path) -> Config:
    try:
        raw = Path(path).read_text(encoding="utf-8")
    except OSError as exc:
        raise ConfigError(
            f"Konfigurationsdatei {str(path)!r} kann nicht gelesen werden: {exc}"
        )
    try:
        data = yaml.safe_load(raw)
    except yaml.YAMLError as exc:
        raise ConfigError(
            f"Konfigurationsdatei {str(path)!r} ist kein gültiges YAML: {exc}"
        )
    if not isinstance(data, dict):
        raise ConfigError(
            f"Konfigurationsdatei {str(path)!r} muss ein YAML-Mapping enthalten"
        )
    try:
        return Config(**data)
    except ValidationError as exc:
        raise ConfigError(_format_validation_error(path, exc))


def _format_validation_error(path: Path, exc: ValidationError) -> str:
    lines = [f"Konfigurationsdatei {str(path)!r} ist ungültig:"]
    for err in exc.errors():
        loc = ".".join(str(part) for part in err["loc"]) or "(Wurzel)"
        lines.append(f"  - {loc}: {err['msg']}")
    return "\n".join(lines)
```

- [ ] **Step 4: Run tests to verify they pass**

Run (from `backend/`):
```bash
uv run pytest tests/test_config.py -v
```
Expected: PASS (all tests so far).

- [ ] **Step 5: Commit**

```bash
git add backend
git commit -m "feat(config): wrap load and parse failures in a clear ConfigError"
```

---

## Task 4: Validate required paths exist

`watchfolder` and `error_folder` must be existing directories. If `original_handling: move`, `processed_folder` is required and must exist too.

**Files:**
- Modify: `backend/src/zilpzalp/config.py`
- Test: `backend/tests/test_config.py`

- [ ] **Step 1: Write the failing tests** (append to `backend/tests/test_config.py`)

```python
def test_missing_watchfolder_raises(valid_config, write_config):
    valid_config["paths"]["watchfolder"] = "/this/does/not/exist"
    path = write_config(valid_config)

    with pytest.raises(ConfigError, match="watchfolder"):
        load_config(path)


def test_move_without_processed_folder_raises(valid_config, write_config):
    valid_config["original_handling"] = "move"
    del valid_config["paths"]["processed_folder"]
    path = write_config(valid_config)

    with pytest.raises(ConfigError, match="processed_folder ist erforderlich"):
        load_config(path)


def test_keep_without_processed_folder_is_valid(valid_config, write_config):
    valid_config["original_handling"] = "keep"
    del valid_config["paths"]["processed_folder"]
    path = write_config(valid_config)

    cfg = load_config(path)

    assert cfg.original_handling == "keep"
```

- [ ] **Step 2: Run tests to verify they fail**

Run (from `backend/`):
```bash
uv run pytest tests/test_config.py -v -k "watchfolder or processed_folder"
```
Expected: FAIL — `test_missing_watchfolder_raises` and `test_move_without_processed_folder_raises` do not raise (no path validation yet).

- [ ] **Step 3: Add a path-existence model validator to `Config` in `backend/src/zilpzalp/config.py`**

Update the imports line to add `model_validator`:
```python
from pydantic import BaseModel, ValidationError, model_validator
```

Add this method inside the `Config` class (after the field declarations):
```python
    @model_validator(mode="after")
    def _check_paths_exist(self) -> "Config":
        required = [
            ("watchfolder", self.paths.watchfolder),
            ("error_folder", self.paths.error_folder),
        ]
        for label, folder in required:
            if not folder.is_dir():
                raise ValueError(
                    f"paths.{label} {str(folder)!r} existiert nicht oder ist kein Verzeichnis"
                )
        if self.original_handling == "move":
            processed = self.paths.processed_folder
            if processed is None:
                raise ValueError(
                    "paths.processed_folder ist erforderlich, wenn original_handling: move"
                )
            if not processed.is_dir():
                raise ValueError(
                    f"paths.processed_folder {str(processed)!r} existiert nicht "
                    "oder ist kein Verzeichnis"
                )
        return self
```

- [ ] **Step 4: Run tests to verify they pass**

Run (from `backend/`):
```bash
uv run pytest tests/test_config.py -v
```
Expected: PASS (all).

- [ ] **Step 5: Commit**

```bash
git add backend
git commit -m "feat(config): validate required paths exist"
```

---

## Task 5: Validate pattern placeholders

`default_pattern` and every `patterns[].template` may only use the known placeholders `{date}`, `{sender}`, `{doctype}`, `{description}`.

**Files:**
- Modify: `backend/src/zilpzalp/config.py`
- Test: `backend/tests/test_config.py`

- [ ] **Step 1: Write the failing tests** (append to `backend/tests/test_config.py`)

```python
def test_unknown_placeholder_in_default_pattern_raises(valid_config, write_config):
    valid_config["default_pattern"] = "{date}_{unknown}"
    path = write_config(valid_config)

    with pytest.raises(ConfigError, match="unbekannte Platzhalter"):
        load_config(path)


def test_unknown_placeholder_in_pattern_template_raises(valid_config, write_config):
    valid_config["patterns"] = [{"name": "standard", "template": "{date}_{bogus}"}]
    path = write_config(valid_config)

    with pytest.raises(ConfigError, match="bogus"):
        load_config(path)


def test_known_placeholders_are_valid(valid_config, write_config):
    valid_config["default_pattern"] = "{sender}-{doctype}-{description}-{date}"
    path = write_config(valid_config)

    cfg = load_config(path)

    assert cfg.default_pattern == "{sender}-{doctype}-{description}-{date}"
```

- [ ] **Step 2: Run tests to verify they fail**

Run (from `backend/`):
```bash
uv run pytest tests/test_config.py -v -k "placeholder"
```
Expected: FAIL — unknown-placeholder tests do not raise yet.

- [ ] **Step 3: Add placeholder constants and a validator to `backend/src/zilpzalp/config.py`**

Add `import re` to the top of the file (after `from pathlib import Path`):
```python
import re
```

Add these module-level constants below the imports (above `class ConfigError`):
```python
KNOWN_PLACEHOLDERS = {"date", "sender", "doctype", "description"}
_PLACEHOLDER_RE = re.compile(r"\{([^}]*)\}")
```

Add this method inside the `Config` class:
```python
    @model_validator(mode="after")
    def _check_placeholders(self) -> "Config":
        templates = [("default_pattern", self.default_pattern)]
        templates += [
            (f"patterns[{i}].template ({p.name})", p.template)
            for i, p in enumerate(self.patterns)
        ]
        for where, template in templates:
            unknown = set(_PLACEHOLDER_RE.findall(template)) - KNOWN_PLACEHOLDERS
            if unknown:
                raise ValueError(
                    f"{where} enthält unbekannte Platzhalter {sorted(unknown)}; "
                    f"erlaubt sind {sorted(KNOWN_PLACEHOLDERS)}"
                )
        return self
```

- [ ] **Step 4: Run tests to verify they pass**

Run (from `backend/`):
```bash
uv run pytest tests/test_config.py -v
```
Expected: PASS (all).

- [ ] **Step 5: Commit**

```bash
git add backend
git commit -m "feat(config): validate pattern placeholders"
```

---

## Task 6: Validate optional `date_patterns` regex

Each `date_patterns[].regex` must compile. The block is optional — absent or empty is valid.

**Files:**
- Modify: `backend/src/zilpzalp/config.py`
- Test: `backend/tests/test_config.py`

- [ ] **Step 1: Write the failing tests** (append to `backend/tests/test_config.py`)

```python
def test_invalid_date_pattern_regex_raises(valid_config, write_config):
    valid_config["date_patterns"] = [{"label": "broken", "regex": "(unbalanced"}]
    path = write_config(valid_config)

    with pytest.raises(ConfigError, match="ungültiger regulärer Ausdruck"):
        load_config(path)


def test_valid_date_pattern_regex_is_accepted(valid_config, write_config):
    valid_config["date_patterns"] = [
        {"label": "leistungsdatum", "regex": r"Leistungsdatum:\s*(\d{2}\.\d{2}\.\d{4})"}
    ]
    path = write_config(valid_config)

    cfg = load_config(path)

    assert cfg.date_patterns[0].label == "leistungsdatum"


def test_missing_date_patterns_block_is_valid(valid_config, write_config):
    del valid_config["date_patterns"]
    path = write_config(valid_config)

    cfg = load_config(path)

    assert cfg.date_patterns == []
```

- [ ] **Step 2: Run tests to verify they fail**

Run (from `backend/`):
```bash
uv run pytest tests/test_config.py -v -k "date_pattern"
```
Expected: FAIL — `test_invalid_date_pattern_regex_raises` does not raise yet.

- [ ] **Step 3: Add a regex field validator to `DatePattern` in `backend/src/zilpzalp/config.py`**

Update the imports line to add `field_validator`:
```python
from pydantic import BaseModel, ValidationError, field_validator, model_validator
```

Add this method inside the `DatePattern` class:
```python
    @field_validator("regex")
    @classmethod
    def _regex_compiles(cls, value: str) -> str:
        try:
            re.compile(value)
        except re.error as exc:
            raise ValueError(f"ungültiger regulärer Ausdruck {value!r}: {exc}")
        return value
```

- [ ] **Step 4: Run tests to verify they pass**

Run (from `backend/`):
```bash
uv run pytest tests/test_config.py -v
```
Expected: PASS (all).

- [ ] **Step 5: Commit**

```bash
git add backend
git commit -m "feat(config): validate optional date_patterns regex"
```

---

## Task 7: Validate `date_format`

`date_format` must contain a strftime directive (a `%`), otherwise the rendered filename would have no date.

**Files:**
- Modify: `backend/src/zilpzalp/config.py`
- Test: `backend/tests/test_config.py`

- [ ] **Step 1: Write the failing tests** (append to `backend/tests/test_config.py`)

```python
def test_date_format_without_directive_raises(valid_config, write_config):
    valid_config["date_format"] = "no-directive-here"
    path = write_config(valid_config)

    with pytest.raises(ConfigError, match="strftime-Direktive"):
        load_config(path)


def test_date_format_with_directive_is_valid(valid_config, write_config):
    valid_config["date_format"] = "%d.%m.%Y"
    path = write_config(valid_config)

    cfg = load_config(path)

    assert cfg.date_format == "%d.%m.%Y"
```

- [ ] **Step 2: Run tests to verify they fail**

Run (from `backend/`):
```bash
uv run pytest tests/test_config.py -v -k "date_format"
```
Expected: FAIL — `test_date_format_without_directive_raises` does not raise yet.

- [ ] **Step 3: Add a `date_format` field validator to `Config` in `backend/src/zilpzalp/config.py`**

Add this method inside the `Config` class:
```python
    @field_validator("date_format")
    @classmethod
    def _date_format_has_directive(cls, value: str) -> str:
        if "%" not in value:
            raise ValueError(
                f"date_format {value!r} enthält keine strftime-Direktive (z. B. %Y-%m-%d)"
            )
        return value
```

- [ ] **Step 4: Run tests to verify they pass**

Run (from `backend/`):
```bash
uv run pytest tests/test_config.py -v
```
Expected: PASS (all).

- [ ] **Step 5: Lint, then commit**

Run (from `backend/`):
```bash
uv run ruff check .
```
Expected: `All checks passed!`

```bash
git add backend
git commit -m "feat(config): validate date_format directive"
```

---

## Task 8: FastAPI app — load config on startup, `/health` route

A minimal FastAPI app loads and validates the config in its `lifespan` hook. A valid config boots the app and serves `/health`; an invalid config aborts startup by propagating `ConfigError` (the clear message). The config path comes from the `ZILPZALP_CONFIG` env var, defaulting to `config.yaml`.

**Files:**
- Create: `backend/src/zilpzalp/main.py`
- Create: `backend/tests/test_main.py`

- [ ] **Step 1: Write the failing tests in `backend/tests/test_main.py`**

```python
import pytest
from fastapi.testclient import TestClient

from zilpzalp.config import ConfigError
from zilpzalp.main import CONFIG_ENV, app


def test_health_with_valid_config(valid_config, write_config, monkeypatch):
    path = write_config(valid_config)
    monkeypatch.setenv(CONFIG_ENV, str(path))

    with TestClient(app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_config_available_on_app_state(valid_config, write_config, monkeypatch):
    path = write_config(valid_config)
    monkeypatch.setenv(CONFIG_ENV, str(path))

    with TestClient(app):
        assert app.state.config.original_handling == "move"


def test_startup_aborts_on_invalid_config(valid_config, write_config, monkeypatch):
    valid_config["original_handling"] = "bogus"
    path = write_config(valid_config)
    monkeypatch.setenv(CONFIG_ENV, str(path))

    with pytest.raises(ConfigError):
        with TestClient(app):
            pass
```

- [ ] **Step 2: Run tests to verify they fail**

Run (from `backend/`):
```bash
uv run pytest tests/test_main.py -v
```
Expected: FAIL — `ModuleNotFoundError: No module named 'zilpzalp.main'`.

- [ ] **Step 3: Create `backend/src/zilpzalp/main.py`**

```python
from __future__ import annotations

import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI

from zilpzalp.config import load_config

CONFIG_ENV = "ZILPZALP_CONFIG"
DEFAULT_CONFIG_PATH = "config.yaml"


def get_config_path() -> Path:
    return Path(os.environ.get(CONFIG_ENV, DEFAULT_CONFIG_PATH))


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.config = load_config(get_config_path())
    yield


app = FastAPI(title="ZilpZalp", lifespan=lifespan)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
```

- [ ] **Step 4: Run tests to verify they pass**

Run (from `backend/`):
```bash
uv run pytest tests/test_main.py -v
```
Expected: PASS (3 tests).

- [ ] **Step 5: Run the full suite and lint**

Run (from `backend/`):
```bash
uv run pytest -v
uv run ruff check .
```
Expected: all tests PASS; `All checks passed!`.

- [ ] **Step 6: Manual smoke check (optional but recommended)**

Run (from `backend/`):
```bash
ZILPZALP_CONFIG=config.example.yaml uv run uvicorn zilpzalp.main:app --port 8000
```
Expected: startup **aborts** with a clear `ConfigError` because `config.example.yaml` points at `/data/inbox` etc. which do not exist locally — this demonstrates startup validation. (To see it boot, copy the example to `config.yaml`, edit the paths to existing dirs, then `uv run uvicorn zilpzalp.main:app` and open `http://localhost:8000/health`.)

- [ ] **Step 7: Commit**

```bash
git add backend
git commit -m "feat(backend): load config at FastAPI startup with /health route"
```

---

## Self-Review

**Spec coverage (Design-Spec §2 & §5, Roadmap M1):**
- §2 src-layout `backend/src/zilpzalp/`, `pyproject.toml`, `tests/` mirroring src → Task 1.
- §2 `config.py` present, `main.py` present (Startup, Config laden) → Tasks 2–8. (watcher/queue/etc. are deferred to later milestones, per scope.)
- §5 required paths exist → Task 4. Conditional `processed_folder` for `move` → Task 4.
- §5 enums `original_handling` / `summary_mode` → Task 2 (Literal) + Task 3 (clear error).
- §5 pattern placeholders known → Task 5.
- §5 `date_format` valid → Task 7.
- §5 `date_patterns` optional, invalid regex rejected with clear message, built-in detection unaffected → Task 6 (regex compile; no built-in detection exists yet, so "unaffected" holds trivially).
- §5 "Beim Start validiert config … bricht mit klarer Fehlermeldung ab" → Task 3 (ConfigError formatting) + Task 8 (startup abort).
- Roadmap M1 "uv/pyproject/src-Layout, config.py, Startup-Validierung" → fully covered.
- Tooling: uv → Task 1; pytest/ruff → Task 1 config + per-task runs.

**Out of scope, intentionally not implemented:** `rules` schema modeling (Milestone 2), config saving/writing (Milestone 5 UI), target-path existence and rule→pattern/target referential checks (deferred — not listed in §5's startup checks; revisit when the suggestion engine consumes them).

**Placeholder scan:** No TBD/TODO; every code and test step contains complete content.

**Type consistency:** `Config`, `Paths`, `Target`, `Pattern`, `DatePattern`, `ConfigError`, `load_config`, `_format_validation_error`, `KNOWN_PLACEHOLDERS`, `_PLACEHOLDER_RE` are defined in Task 2/3/5 and reused consistently. `main.py` uses `load_config` and `CONFIG_ENV` exactly as exported. Fixtures `valid_config` / `write_config` (conftest) are used uniformly across `test_config.py` and `test_main.py`.
