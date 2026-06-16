# Config/Pfade/Disposal/Cache Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Infrastruktur-Pfade nach `ZILPZALP_PATH_*` (Env) verlagern, `patterns` zur Map machen, `original_handling` auf `delete|trash` vereinheitlichen (für Ablegen *und* Skip), einen persistenten json+markdown-Extraktions-Cache mit automatischer Re-Analyse einführen und die Container-Config per Entrypoint seeden.

**Architecture:** Pfade kommen aus Env-Variablen mit Defaults unter `/data` und werden beim Start angelegt; die config.yaml enthält nur noch Domänen-Werte. Ein Original verlässt die Inbox per Ablegen oder Skip — in beiden Fällen entscheidet `original_handling`. Der Worker extrahiert PDFs über OpenDataLoader in einen Disk-Cache (`<stem>.json` + `<stem>.md`); eine Config-Änderung re-analysiert offene Dokumente aus dem Cache ohne erneute Extraktion.

**Tech Stack:** Python 3.12, FastAPI, Pydantic v2, PyYAML, watchdog, opendataloader-pdf, Jinja2/HTMX, pytest, ruff, uv.

## Global Constraints

- Python `>=3.12`; alle Befehle aus `backend/` via `uv run …`.
- Tests: `uv run pytest`; Lint: `uv run ruff check .` (line-length 100).
- **`uv run` schreibt `backend/uv.lock` ohne Dep-Änderung neu** — vor jedem Commit prüfen und ggf. zurücksetzen: `git checkout -- uv.lock`.
- Conventional Commits, Deutsch. Add/Commit/Push selbstständig nach jedem Task; nie force-push/amend/hard-reset; nie `git rebase -i`/`git add -i`.
- README/mkdocs auf Englisch; In-Code-Kommentare/Doku-Strings im Bestand sind Deutsch — Stil beibehalten.
- Keine neuen Dependencies. `opendataloader-pdf>=2.0` ist vorhanden und kann `format=["json","markdown"]`.
- Breaking Change am Config-Schema ist gewollt; kein Migrationslayer. Beispiele/Doku werden mitgezogen.

---

### Task 1: Pfade aus Env + Verzeichnis-Erstellung beim Start

**Files:**
- Modify: `backend/src/zilpzalp/config.py` (Paths-Modell, `load_paths`, `outbox_path`, `load_config`/`save_config` Pfad-Injektion, `_check_paths_exist` entfernen)
- Modify: `backend/src/zilpzalp/main.py` (`_ensure_dirs` in `lifespan`)
- Modify: `backend/tests/conftest.py` (env-basierte Pfade)
- Modify: `backend/tests/test_config.py` (Pfad-Tests an Env anpassen)
- Modify: `backend/tests/test_processor.py` (Inline-Config auf Env umstellen)

**Interfaces:**
- Produces: `load_paths() -> Paths` mit Feldern `watchfolder, error_folder, trash, cache` (alle `Path`); `outbox_path() -> Path`. `Config.paths` bleibt `Paths`, wird aber aus Env injiziert. Env-Variablen: `ZILPZALP_PATH_INBOX|ERROR|TRASH|CACHE|OUTBOX` mit Defaults `/data/inbox|error|trash|cache|outbox`.
- Consumes: nichts.

> Hinweis: `original_handling` bleibt in diesem Task noch `Literal["move","delete","keep"]` und `patterns` noch `list[Pattern]` — diese ändern Task 2 und 3. Hier wird nur das Pfad-Modell umgestellt.

- [ ] **Step 1: conftest auf env-basierte Pfade umstellen**

Ersetze in `backend/tests/conftest.py` den gesamten Inhalt durch:

```python
import pytest
import yaml


@pytest.fixture(autouse=True)
def env_paths(tmp_path, monkeypatch):
    """Point all ZILPZALP_PATH_* at fresh temp dirs and create them, so every
    test runs against a writable, isolated /data layout."""
    mapping = {
        "ZILPZALP_PATH_INBOX": tmp_path / "inbox",
        "ZILPZALP_PATH_ERROR": tmp_path / "error",
        "ZILPZALP_PATH_TRASH": tmp_path / "trash",
        "ZILPZALP_PATH_CACHE": tmp_path / "cache",
        "ZILPZALP_PATH_OUTBOX": tmp_path / "outbox",
    }
    for var, path in mapping.items():
        path.mkdir(parents=True, exist_ok=True)
        monkeypatch.setenv(var, str(path))
    return mapping


@pytest.fixture
def valid_config(tmp_path):
    """A complete, valid domain config dict. Paths come from env (env_paths)."""
    (tmp_path / "finanzen").mkdir(exist_ok=True)
    return {
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

- [ ] **Step 2: Failing test für env-Pfade schreiben**

Ersetze in `backend/tests/test_config.py` die Tests `test_missing_watchfolder_raises`, `test_move_without_processed_folder_raises`, `test_keep_without_processed_folder_is_valid`, `test_missing_error_folder_raises`, `test_move_with_nonexistent_processed_folder_raises` (Zeilen 68–109) durch:

```python
def test_paths_come_from_env_not_yaml(valid_config, write_config, env_paths):
    valid_config["paths"] = {"watchfolder": "/ignored/in/yaml"}  # must be ignored
    path = write_config(valid_config)

    cfg = load_config(path)

    assert cfg.paths.watchfolder == env_paths["ZILPZALP_PATH_INBOX"]
    assert cfg.paths.error_folder == env_paths["ZILPZALP_PATH_ERROR"]
    assert cfg.paths.trash == env_paths["ZILPZALP_PATH_TRASH"]
    assert cfg.paths.cache == env_paths["ZILPZALP_PATH_CACHE"]


def test_paths_use_defaults_when_env_unset(valid_config, write_config, monkeypatch):
    for var in ("INBOX", "ERROR", "TRASH", "CACHE"):
        monkeypatch.delenv(f"ZILPZALP_PATH_{var}", raising=False)
    from pathlib import Path
    from zilpzalp.config import load_paths

    paths = load_paths()
    assert paths.watchfolder == Path("/data/inbox")
    assert paths.trash == Path("/data/trash")
```

`test_load_valid_config` Zeile 16 (`assert cfg.paths.watchfolder.name == "inbox"`) bleibt gültig — der env-Ordner heißt `inbox`.

Ersetze `test_missing_required_field_raises_config_error` (Zeilen 51–57), das `del valid_config["paths"]` macht (Key existiert nicht mehr → KeyError), durch ein noch erforderliches Domänen-Feld:

```python
def test_missing_required_field_raises_config_error(valid_config, write_config):
    del valid_config["original_handling"]
    path = write_config(valid_config)

    with pytest.raises(ConfigError) as exc:
        load_config(path)
    assert "original_handling" in str(exc.value)
```

- [ ] **Step 3: Test ausführen, Fehlschlag bestätigen**

Run: `uv run pytest tests/test_config.py -q`
Expected: FAIL (z. B. `Config` verlangt `paths` aus YAML / `Paths` hat kein `trash`).

- [ ] **Step 4: config.py auf env-Pfade umstellen**

In `backend/src/zilpzalp/config.py`: ersetze die `Paths`-Klasse (Zeilen 20–23) durch:

```python
DEFAULT_PATHS = {
    "inbox": "/data/inbox",
    "error": "/data/error",
    "trash": "/data/trash",
    "cache": "/data/cache",
    "outbox": "/data/outbox",
}


class Paths(BaseModel):
    watchfolder: Path
    error_folder: Path
    trash: Path
    cache: Path


def load_paths() -> Paths:
    env = os.environ.get
    return Paths(
        watchfolder=Path(env("ZILPZALP_PATH_INBOX", DEFAULT_PATHS["inbox"])),
        error_folder=Path(env("ZILPZALP_PATH_ERROR", DEFAULT_PATHS["error"])),
        trash=Path(env("ZILPZALP_PATH_TRASH", DEFAULT_PATHS["trash"])),
        cache=Path(env("ZILPZALP_PATH_CACHE", DEFAULT_PATHS["cache"])),
    )


def outbox_path() -> Path:
    return Path(os.environ.get("ZILPZALP_PATH_OUTBOX", DEFAULT_PATHS["outbox"]))
```

Entferne den `_check_paths_exist`-Validator vollständig (Zeilen 73–95).

In `load_config` (vor `Config(**data)`): füge nach dem Mapping-Check ein:

```python
    data.pop("paths", None)  # paths come from env, never from YAML
    data["paths"] = load_paths()
```

In `save_config` (vor `Config(**data)`): dieselben zwei Zeilen einfügen.

- [ ] **Step 5: ensure_dirs in main.py**

In `backend/src/zilpzalp/main.py`: ergänze nach `config = load_config(config_path)` in `lifespan`:

```python
    _ensure_dirs(config)
```

und füge oberhalb von `lifespan` hinzu (Import `outbox_path` mit aufnehmen: `from zilpzalp.config import load_config, outbox_path`):

```python
def _ensure_dirs(config) -> None:
    for folder in (
        config.paths.watchfolder,
        config.paths.error_folder,
        config.paths.trash,
        config.paths.cache,
        outbox_path(),
    ):
        folder.mkdir(parents=True, exist_ok=True)
```

- [ ] **Step 6: test_processor auf Env umstellen**

In `backend/tests/test_processor.py` ersetze die Helfer `_config` (Zeilen 9–28). Die `move`/`keep`-Fälle bleiben in diesem Task gültig (Literal ändert erst Task 3):

```python
def _config(tmp_path: Path, original_handling: str = "keep", extra: str = ""):
    """Build a validated Config; paths come from env (env_paths fixture)."""
    cfg = tmp_path / "config.yaml"
    cfg.write_text(
        f"""
original_handling: {original_handling}
summary_mode: never
default_pattern: "{{date}}__{{sender}}_{{doctype}}_{{description}}"
date_format: "%Y-%m-%d"
patterns:
  - name: standard
    template: "{{date}}__{{sender}}_{{doctype}}_{{description}}"
{extra}
""",
        encoding="utf-8",
    )
    return load_config(cfg)
```

`_source` schreibt nach `tmp_path / "inbox"` — der Ordner existiert dank `env_paths`. In `test_move_relocates_original_to_processed` und `test_move_conflict_in_processed_raises_before_copy` zeigt `processed` jetzt auf `tmp_path / "processed"`, der **nicht** mehr existiert. Ersetze in beiden Tests `tmp_path / "processed"` durch `Path(config.paths.processed_folder)` ist obsolet — diese zwei Tests entfernt Task 3. Für **diesen** Task: lege in beiden Tests den Ordner explizit an mit `(tmp_path / "processed").mkdir(exist_ok=True)` als erste Zeile, damit `move` weiter validiert. (Hinweis: `Paths` hat kein `processed_folder` mehr → `move` würde beim Laden scheitern. Markiere beide `test_move_*`-Tests mit `@pytest.mark.skip(reason="move/processed wird in Task 3 durch trash ersetzt")`.)

- [ ] **Step 7: Tests grün**

Run: `uv run pytest tests/test_config.py tests/test_processor.py tests/test_main.py -q`
Expected: PASS (move-Tests skipped).

- [ ] **Step 8: Volle Suite + Lint**

Run: `uv run pytest -q && uv run ruff check .`
Expected: PASS (ggf. weitere `paths`-Referenzen in anderen Tests anpassen: in `test_processor` keine mehr; `test_routes`/`test_worker` nutzen `cfg.paths.watchfolder`/`error_folder`, die weiter existieren).

- [ ] **Step 9: Commit**

```bash
git checkout -- uv.lock 2>/dev/null || true
git add backend/src/zilpzalp/config.py backend/src/zilpzalp/main.py backend/tests/conftest.py backend/tests/test_config.py backend/tests/test_processor.py
git commit -m "refactor(config): infra-Pfade aus ZILPZALP_PATH_* statt config.yaml"
```

---

### Task 2: `patterns` als Map + `default_pattern` als Schlüssel-Verweis

**Files:**
- Modify: `backend/src/zilpzalp/config.py` (`Pattern`, Validierung, Platzhalter-Check)
- Modify: `backend/src/zilpzalp/suggestion.py:22-27` (`_resolve_pattern`)
- Modify: `backend/src/zilpzalp/web/routes.py:169-173` (`_resolve_template`)
- Modify: `backend/src/zilpzalp/web/templates/review.html:62-63` (Pattern-Schleife)
- Modify: `backend/tests/conftest.py` (patterns als Map)
- Modify: `backend/tests/test_config.py` (Pattern-Tests)

**Interfaces:**
- Consumes: Task 1.
- Produces: `Config.patterns: dict[str, Pattern]`, `Pattern = {template: str}` (kein `name`-Feld). `default_pattern: str` muss ein Schlüssel sein. `_resolve_pattern(config, name)` und `_resolve_template(config, name)` geben `config.patterns[name].template` zurück, Fallback `config.patterns[config.default_pattern].template`.

- [ ] **Step 1: conftest patterns auf Map**

In `backend/tests/conftest.py`, `valid_config`: ersetze den `patterns`-Eintrag durch:

```python
        "patterns": {
            "standard": {"template": "{date}__{sender}_{doctype}_{description}"}
        },
```

- [ ] **Step 2: Failing tests schreiben**

In `backend/tests/test_config.py`: ersetze `test_load_valid_config`s Pattern-Assertion (Zeile 18) durch:

```python
    assert cfg.patterns["standard"].template == "{date}__{sender}_{doctype}_{description}"
```

Ersetze `test_unknown_placeholder_in_default_pattern_raises` und `test_unknown_placeholder_in_pattern_template_raises` und `test_known_placeholders_are_valid` und `test_empty_placeholder_raises_clear_message` (die `default_pattern` als Template behandeln) durch:

```python
def test_unknown_placeholder_in_pattern_template_raises(valid_config, write_config):
    valid_config["patterns"] = {"standard": {"template": "{date}_{bogus}"}}
    valid_config["default_pattern"] = "standard"
    path = write_config(valid_config)

    with pytest.raises(ConfigError, match="bogus"):
        load_config(path)


def test_empty_placeholder_raises_clear_message(valid_config, write_config):
    valid_config["patterns"] = {"standard": {"template": "{date}_{}"}}
    valid_config["default_pattern"] = "standard"
    path = write_config(valid_config)

    with pytest.raises(ConfigError, match="leerer Platzhalter"):
        load_config(path)


def test_empty_patterns_raises(valid_config, write_config):
    valid_config["patterns"] = {}
    path = write_config(valid_config)

    with pytest.raises(ConfigError, match="patterns"):
        load_config(path)


def test_default_pattern_must_reference_existing_key(valid_config, write_config):
    valid_config["default_pattern"] = "doesnotexist"
    path = write_config(valid_config)

    with pytest.raises(ConfigError, match="default_pattern"):
        load_config(path)
```

Ändere `test_load_valid_config`s `default_pattern` (über `valid_config`): setze in dem Test vor `load_config` `valid_config["default_pattern"] = "standard"` — oder besser: ändere die conftest `valid_config` `default_pattern` direkt auf `"standard"`:

In `backend/tests/conftest.py`, `valid_config`: ändere `"default_pattern": "{date}__{sender}_{doctype}_{description}"` zu `"default_pattern": "standard"`.

Passe `test_known_placeholders_are_valid` an → entfällt (default_pattern ist kein Template mehr); ersetze durch:

```python
def test_pattern_template_known_placeholders_valid(valid_config, write_config):
    valid_config["patterns"] = {"x": {"template": "{sender}-{doctype}-{description}-{date}"}}
    valid_config["default_pattern"] = "x"
    path = write_config(valid_config)

    cfg = load_config(path)

    assert cfg.patterns["x"].template == "{sender}-{doctype}-{description}-{date}"
```

- [ ] **Step 3: Test ausführen, Fehlschlag bestätigen**

Run: `uv run pytest tests/test_config.py -q`
Expected: FAIL (`patterns` ist noch `list`).

- [ ] **Step 4: config.py Pattern-Map implementieren**

In `backend/src/zilpzalp/config.py`: ersetze `class Pattern` (Zeilen 32–34) durch:

```python
class Pattern(BaseModel):
    template: str
```

Ändere im `Config`-Modell `patterns: list[Pattern] = []` zu `patterns: dict[str, Pattern] = {}`.

Ersetze den `_check_placeholders`-Validator-Körper so, dass er `default_pattern` als Schlüssel prüft und Platzhalter nur über Templates laufen:

```python
    @model_validator(mode="after")
    def _check_patterns(self) -> "Config":
        if not self.patterns:
            raise ValueError("patterns darf nicht leer sein")
        if self.default_pattern not in self.patterns:
            raise ValueError(
                f"default_pattern {self.default_pattern!r} verweist auf kein "
                f"definiertes Pattern; verfügbar: {sorted(self.patterns)}"
            )
        for name, pattern in self.patterns.items():
            found = set(_PLACEHOLDER_RE.findall(pattern.template))
            if "" in found:
                raise ValueError(f"patterns.{name}: leerer Platzhalter {{}}")
            unknown = found - KNOWN_PLACEHOLDERS
            if unknown:
                raise ValueError(
                    f"patterns.{name} enthält unbekannte Platzhalter {sorted(unknown)}; "
                    f"erlaubt sind {sorted(KNOWN_PLACEHOLDERS)}"
                )
        return self
```

- [ ] **Step 5: Lookups + Template anpassen**

`backend/src/zilpzalp/suggestion.py` `_resolve_pattern` (Zeilen 22–27):

```python
def _resolve_pattern(config: Config, pattern_name: str | None) -> str:
    if pattern_name and pattern_name in config.patterns:
        return config.patterns[pattern_name].template
    return config.patterns[config.default_pattern].template
```

`backend/src/zilpzalp/web/routes.py` `_resolve_template` (Zeilen 169–173):

```python
def _resolve_template(config: Config, pattern_name: str) -> str:
    if pattern_name and pattern_name in config.patterns:
        return config.patterns[pattern_name].template
    return config.patterns[config.default_pattern].template
```

`backend/src/zilpzalp/web/templates/review.html` Pattern-Schleife (Zeilen 62–63):

```html
              {% for name, p in config.patterns.items() %}
              <option value="{{ name }}" data-template="{{ p.template }}" {% if name == suggestion.pattern_name %}selected{% endif %}>{{ name }} — {{ p.template }}</option>
              {% endfor %}
```

- [ ] **Step 5b: Inline-Configs auf Map umstellen**

Alle Tests, die eine Config **nicht** über die conftest-`valid_config` bauen, verwenden noch Listen-Patterns und einen Template-`default_pattern` → nach diesem Task ungültig. Stelle sie um:

In `backend/tests/test_processor.py`, Helfer `_config`: ersetze den YAML-Block-Teil
```
default_pattern: "{{date}}__{{sender}}_{{doctype}}_{{description}}"
date_format: "%Y-%m-%d"
patterns:
  - name: standard
    template: "{{date}}__{{sender}}_{{doctype}}_{{description}}"
```
durch
```
default_pattern: standard
date_format: "%Y-%m-%d"
patterns:
  standard:
    template: "{{date}}__{{sender}}_{{doctype}}_{{description}}"
```

Prüfe ebenso `backend/tests/test_suggestion.py` und `backend/tests/test_analysis_pipeline.py` mit `grep -n "default_pattern\|patterns" tests/test_suggestion.py tests/test_analysis_pipeline.py`; jede Liste `patterns:`/jeden Template-`default_pattern` analog auf Map + Schlüssel-Verweis umstellen.

- [ ] **Step 6: Tests grün**

Run: `uv run pytest -q`
Expected: PASS (volle Suite — sie deckt test_processor/test_suggestion/test_routes mit ab).

- [ ] **Step 7: Volle Suite + Lint, Commit**

```bash
uv run pytest -q && uv run ruff check .
git checkout -- uv.lock 2>/dev/null || true
git add backend/src/zilpzalp/config.py backend/src/zilpzalp/suggestion.py backend/src/zilpzalp/web/routes.py backend/src/zilpzalp/web/templates/review.html backend/tests/conftest.py backend/tests/test_config.py
git commit -m "feat(config): patterns als Map mit default_pattern als Schlüssel-Verweis"
```

---

### Task 3: `original_handling: delete|trash` + Default-Outbox-Target + Processor-Disposal

**Files:**
- Modify: `backend/src/zilpzalp/config.py` (`Literal`, `_apply_default_target`)
- Modify: `backend/src/zilpzalp/processor.py` (`_dispose`, `process`, `skip`, `ProcessResult`)
- Modify: `backend/tests/conftest.py` (`original_handling: delete`)
- Modify: `backend/tests/test_config.py` (Enum-Test + Outbox-Default-Test)
- Modify: `backend/tests/test_processor.py` (delete/trash/skip)

**Interfaces:**
- Consumes: Task 1 (`Paths.trash`, `outbox_path`), Task 2.
- Produces: `Config.original_handling: Literal["delete","trash"]`. `process(source, filename, targets, config) -> ProcessResult` (kopiert, dann entsorgt). `skip(source, config) -> ProcessResult` (entsorgt ohne Kopie). `ProcessResult.original_action: Literal["deleted","trashed"]`, `original_destination: Path | None` (nur bei `trashed`). Bei leeren `targets` in der YAML synthetisiert `load_config`/`save_config` `Target(name="Outbox", path=outbox_path(), default=True)`.

- [ ] **Step 1: conftest + Failing config-tests**

In `backend/tests/conftest.py`, `valid_config`: ändere `"original_handling": "move"` zu `"original_handling": "delete"`.

In `backend/tests/test_config.py`: aktualisiere `test_load_valid_config` Zeile 13 zu `assert cfg.original_handling == "delete"`. Entferne den jetzt obsoleten `test_keep_without_processed_folder_is_valid` (falls in Task 1 nicht schon weg). Ergänze:

```python
def test_trash_handling_is_valid(valid_config, write_config):
    valid_config["original_handling"] = "trash"
    path = write_config(valid_config)
    assert load_config(path).original_handling == "trash"


def test_move_handling_is_rejected(valid_config, write_config):
    valid_config["original_handling"] = "move"
    path = write_config(valid_config)
    with pytest.raises(ConfigError, match="original_handling"):
        load_config(path)


def test_default_outbox_target_synthesized_when_none(valid_config, write_config, env_paths):
    valid_config["targets"] = []
    path = write_config(valid_config)

    cfg = load_config(path)

    assert len(cfg.targets) == 1
    assert cfg.targets[0].name == "Outbox"
    assert cfg.targets[0].path == env_paths["ZILPZALP_PATH_OUTBOX"]
    assert cfg.targets[0].default is True


def test_explicit_targets_suppress_outbox_default(valid_config, write_config):
    path = write_config(valid_config)  # valid_config has one explicit target
    cfg = load_config(path)
    assert [t.name for t in cfg.targets] == ["Finanzen"]
```

Aktualisiere `test_config_available_on_app_state` in `backend/tests/test_main.py` Zeile 15: `assert app.state.config.original_handling == "delete"`.

- [ ] **Step 2: Fehlschlag bestätigen**

Run: `uv run pytest tests/test_config.py -q`
Expected: FAIL (`move` noch erlaubt; kein Outbox-Default).

- [ ] **Step 3: config.py implementieren**

In `backend/src/zilpzalp/config.py`: ändere `original_handling: Literal["move", "delete", "keep"]` zu `original_handling: Literal["delete", "trash"]`.

Füge `Target` (existiert) nutzend einen Helfer hinzu und rufe ihn in `load_config`/`save_config` direkt vor `return`/Zuweisung auf:

```python
def _apply_default_target(config: Config) -> None:
    if not config.targets:
        config.targets = [Target(name="Outbox", path=outbox_path(), default=True)]
```

In `load_config`: nach erfolgreichem `Config(**data)` → `config = Config(**data); _apply_default_target(config); return config`.
In `save_config`: analog vor `return config`.

- [ ] **Step 4: Failing processor-tests**

Ersetze in `backend/tests/test_processor.py` die Tests `test_copies_to_single_target_and_keeps_original`, `test_move_relocates_original_to_processed`, `test_delete_removes_original`, `test_move_conflict_in_processed_raises_before_copy` durch:

```python
def test_delete_removes_original_after_copy(tmp_path):
    config = _config(tmp_path, "delete")
    source = _source(tmp_path)
    target = _target(tmp_path, "finanzen")

    result = process(source, "doc.pdf", [target], config)

    assert (target / "doc.pdf").read_bytes() == b"%PDF-1.4 hello"
    assert not source.exists()
    assert result.original_action == "deleted"
    assert result.original_destination is None


def test_trash_moves_original_after_copy(tmp_path):
    config = _config(tmp_path, "trash")
    source = _source(tmp_path, "orig.pdf")
    target = _target(tmp_path, "finanzen")

    result = process(source, "doc.pdf", [target], config)

    assert (target / "doc.pdf").exists()
    assert not source.exists()
    trashed = Path(config.paths.trash) / "orig.pdf"
    assert trashed.read_bytes() == b"%PDF-1.4 hello"
    assert result.original_action == "trashed"
    assert result.original_destination == trashed


def test_trash_uses_unique_name_on_collision(tmp_path):
    config = _config(tmp_path, "trash")
    source = _source(tmp_path, "orig.pdf")
    target = _target(tmp_path, "finanzen")
    (Path(config.paths.trash) / "orig.pdf").write_bytes(b"old")

    result = process(source, "doc.pdf", [target], config)

    assert (Path(config.paths.trash) / "orig.pdf").read_bytes() == b"old"  # untouched
    assert result.original_destination == Path(config.paths.trash) / "orig (1).pdf"
    assert result.original_destination.read_bytes() == b"%PDF-1.4 hello"


def test_skip_deletes_without_copy(tmp_path):
    config = _config(tmp_path, "delete")
    source = _source(tmp_path)

    result = skip(source, config)

    assert not source.exists()
    assert result.copied == []
    assert result.original_action == "deleted"


def test_skip_trashes_without_copy(tmp_path):
    config = _config(tmp_path, "trash")
    source = _source(tmp_path, "orig.pdf")

    result = skip(source, config)

    assert not source.exists()
    assert (Path(config.paths.trash) / "orig.pdf").exists()
    assert result.original_action == "trashed"
```

In `_config` (test_processor): Default-Arg `original_handling: str = "delete"` setzen. Update Import: `from zilpzalp.processor import FileConflictError, ProcessorError, process, skip`. In den verbleibenden Konflikt-Tests `_config(tmp_path, "keep")` → `_config(tmp_path, "delete")` bzw. `"trash"`. Entferne übrige `@pytest.mark.skip` aus Task 1.

- [ ] **Step 5: Fehlschlag bestätigen**

Run: `uv run pytest tests/test_processor.py -q`
Expected: FAIL (`skip` existiert nicht; `trashed` unbekannt).

- [ ] **Step 6: processor.py implementieren**

Ersetze in `backend/src/zilpzalp/processor.py` `ProcessResult` (Zeilen 24–28) und die Funktion `process` (ab Zeile 31) durch:

```python
@dataclass(frozen=True)
class ProcessResult:
    copied: list[Path]
    original_action: Literal["deleted", "trashed"]
    original_destination: Path | None = None   # set only for "trashed"


def _unique_name(folder: Path, name: str) -> Path:
    candidate = folder / name
    if not candidate.exists():
        return candidate
    stem, suffix = candidate.stem, candidate.suffix
    counter = 1
    while (folder / f"{stem} ({counter}){suffix}").exists():
        counter += 1
    return folder / f"{stem} ({counter}){suffix}"


def _dispose(source: Path, config: Config) -> tuple[str, Path | None]:
    """Remove the inbox original per config.original_handling. Used by both
    filing (after the copy) and skipping (no copy)."""
    if config.original_handling == "trash":
        dest = _unique_name(config.paths.trash, source.name)
        shutil.move(str(source), str(dest))
        return "trashed", dest
    source.unlink(missing_ok=True)
    return "deleted", None


def process(
    source: Path,
    filename: str,
    targets: list[Path],
    config: Config,
) -> ProcessResult:
    """Copy *source* as *filename* into every target folder, then dispose of the
    original per config.original_handling.

    All precondition/conflict checks run before any file is touched, so a
    rejected call leaves the filesystem unchanged. Raises ProcessorError on a
    missing/empty target, FileConflictError on an existing destination.
    """
    if not targets:
        raise ProcessorError("keine Zielordner angegeben")
    for target in targets:
        if not target.is_dir():
            raise ProcessorError(f"Zielordner fehlt: {target}")

    destinations = [target / filename for target in targets]
    for dest in destinations:
        if dest.exists():
            raise FileConflictError(dest)

    for dest in destinations:
        shutil.copy2(source, dest)

    action, dest = _dispose(source, config)
    return ProcessResult(copied=destinations, original_action=action, original_destination=dest)


def skip(source: Path, config: Config) -> ProcessResult:
    """Discard an inbox original without filing it, per config.original_handling."""
    action, dest = _dispose(source, config)
    return ProcessResult(copied=[], original_action=action, original_destination=dest)
```

- [ ] **Step 7: Tests grün, Suite, Lint, Commit**

```bash
uv run pytest -q && uv run ruff check .
git checkout -- uv.lock 2>/dev/null || true
git add backend/src/zilpzalp/config.py backend/src/zilpzalp/processor.py backend/tests/conftest.py backend/tests/test_config.py backend/tests/test_main.py backend/tests/test_processor.py
git commit -m "feat(config): original_handling delete|trash + Skip-Disposal + Outbox-Default"
```

---

### Task 4: Cache-Modul

**Files:**
- Create: `backend/src/zilpzalp/cache.py`
- Create: `backend/tests/test_cache.py`

**Interfaces:**
- Consumes: `zilpzalp.extractor.document_from_odl`, `zilpzalp.document.Document`.
- Produces: `DocumentCache(base: Path)` mit `load_document(path) -> Document | None`, `remove(path) -> None`, `prune(valid_names: Iterable[str]) -> None`. Cache-Dateien: `<base>/<stem>.json` und `<base>/<stem>.md`, Schlüssel = Dateiname des PDFs.

- [ ] **Step 1: Failing tests**

Create `backend/tests/test_cache.py`:

```python
import json
from pathlib import Path

from zilpzalp.cache import DocumentCache


def _odl_json(text):
    return json.dumps({"type": "paragraph", "content": text, "page number": 1})


def test_load_document_returns_none_without_file(tmp_path):
    cache = DocumentCache(tmp_path)
    assert cache.load_document(tmp_path / "missing.pdf") is None


def test_load_document_parses_cached_json(tmp_path):
    (tmp_path / "doc.json").write_text(_odl_json("Hallo Welt"), encoding="utf-8")
    cache = DocumentCache(tmp_path)

    doc = cache.load_document(Path("/inbox/doc.pdf"))

    assert doc is not None
    assert any("Hallo Welt" in b.text for b in doc.blocks)


def test_remove_deletes_both_artifacts(tmp_path):
    (tmp_path / "doc.json").write_text("{}", encoding="utf-8")
    (tmp_path / "doc.md").write_text("# x", encoding="utf-8")
    cache = DocumentCache(tmp_path)

    cache.remove(Path("/inbox/doc.pdf"))

    assert not (tmp_path / "doc.json").exists()
    assert not (tmp_path / "doc.md").exists()


def test_remove_is_idempotent(tmp_path):
    DocumentCache(tmp_path).remove(Path("/inbox/never.pdf"))  # no raise


def test_prune_removes_orphans_keeps_valid(tmp_path):
    for stem in ("keep", "orphan"):
        (tmp_path / f"{stem}.json").write_text("{}", encoding="utf-8")
        (tmp_path / f"{stem}.md").write_text("x", encoding="utf-8")
    cache = DocumentCache(tmp_path)

    cache.prune(["keep.pdf"])

    assert (tmp_path / "keep.json").exists()
    assert not (tmp_path / "orphan.json").exists()
    assert not (tmp_path / "orphan.md").exists()
```

- [ ] **Step 2: Fehlschlag bestätigen**

Run: `uv run pytest tests/test_cache.py -q`
Expected: FAIL (`zilpzalp.cache` fehlt).

- [ ] **Step 3: cache.py implementieren**

Create `backend/src/zilpzalp/cache.py`:

```python
from __future__ import annotations

import json
from collections.abc import Iterable
from pathlib import Path

from zilpzalp.document import Document
from zilpzalp.extractor import document_from_odl


class DocumentCache:
    """Per-document extraction artifacts on disk: <stem>.json (structured ODL
    output, used for re-analysis) and <stem>.md (human-readable, for a future
    preview). Keyed by the PDF's filename, which is unique within the inbox."""

    def __init__(self, base: Path) -> None:
        self._base = Path(base)

    def _json(self, name: str) -> Path:
        return self._base / (Path(name).stem + ".json")

    def _md(self, name: str) -> Path:
        return self._base / (Path(name).stem + ".md")

    def load_document(self, path: Path | str) -> Document | None:
        json_file = self._json(Path(path).name)
        if not json_file.exists():
            return None
        data = json.loads(json_file.read_text(encoding="utf-8"))
        return document_from_odl(data)

    def remove(self, path: Path | str) -> None:
        name = Path(path).name
        self._json(name).unlink(missing_ok=True)
        self._md(name).unlink(missing_ok=True)

    def prune(self, valid_names: Iterable[str]) -> None:
        valid_stems = {Path(n).stem for n in valid_names}
        for artifact in (*self._base.glob("*.json"), *self._base.glob("*.md")):
            if artifact.stem not in valid_stems:
                artifact.unlink(missing_ok=True)
```

- [ ] **Step 4: Tests grün, Commit**

```bash
uv run pytest tests/test_cache.py -q && uv run ruff check .
git checkout -- uv.lock 2>/dev/null || true
git add backend/src/zilpzalp/cache.py backend/tests/test_cache.py
git commit -m "feat(cache): persistenter json/markdown-Extraktions-Cache"
```

---

### Task 5: Extractor schreibt in den Cache

**Files:**
- Modify: `backend/src/zilpzalp/extractor.py:108-124` (`extract`)
- Modify: `backend/tests/test_extractor.py` (Signatur)

**Interfaces:**
- Consumes: Task 4.
- Produces: `extract(pdf_path, cache_dir) -> Document`. Schreibt `<cache_dir>/<stem>.json` und (falls vorhanden) `<cache_dir>/<stem>.md`; parst das JSON zu `Document`.

- [ ] **Step 1: Failing test (Unit, ohne JVM)**

Ergänze in `backend/tests/test_extractor.py`:

```python
def test_extract_writes_cache_and_returns_document(tmp_path, monkeypatch):
    import zilpzalp.extractor as extractor_mod

    pdf = tmp_path / "rechnung.pdf"
    pdf.write_bytes(b"%PDF-1.4")
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()

    def fake_convert(*, input_path, output_dir, format):
        out = Path(output_dir)
        (out / "rechnung.json").write_text(
            json.dumps({"type": "paragraph", "content": "Datum 15.01.2026",
                        "page number": 1}),
            encoding="utf-8",
        )
        (out / "rechnung.md").write_text("# Rechnung\n15.01.2026", encoding="utf-8")

    monkeypatch.setattr(extractor_mod.opendataloader_pdf, "convert", fake_convert)

    doc = extract(pdf, cache_dir)

    assert any("15.01.2026" in b.text for b in doc.blocks)
    assert (cache_dir / "rechnung.json").exists()
    assert (cache_dir / "rechnung.md").read_text(encoding="utf-8").startswith("# Rechnung")
```

Aktualisiere die Integrationstests (Zeilen 45–55): `extract(FIXTURES / "invoice.pdf")` → `extract(FIXTURES / "invoice.pdf", tmp_path)` und `test_extract_pdf_without_text_raises` → `extract(FIXTURES / "empty.pdf", tmp_path)`; beide Funktionssignaturen um `tmp_path` ergänzen.

- [ ] **Step 2: Fehlschlag bestätigen**

Run: `uv run pytest tests/test_extractor.py::test_extract_writes_cache_and_returns_document -q`
Expected: FAIL (`extract()` nimmt nur ein Argument).

- [ ] **Step 3: extractor.py implementieren**

Ersetze `extract` (Zeilen 108–124) durch (Import `import shutil` oben ergänzen):

```python
def extract(pdf_path: str | Path, cache_dir: str | Path) -> Document:
    pdf_path = Path(pdf_path)
    cache_dir = Path(cache_dir)
    stem = pdf_path.stem
    with tempfile.TemporaryDirectory() as tmp:
        opendataloader_pdf.convert(
            input_path=[str(pdf_path)],
            output_dir=tmp,
            format=["json", "markdown"],
        )
        json_outputs = list(Path(tmp).glob("*.json"))
        if not json_outputs:
            raise ExtractionError(
                f"OpenDataLoader erzeugte keine Ausgabe fuer {pdf_path.name!r}"
            )
        json_dest = cache_dir / f"{stem}.json"
        shutil.move(str(json_outputs[0]), str(json_dest))
        md_outputs = list(Path(tmp).glob("*.md")) or list(Path(tmp).glob("*.markdown"))
        if md_outputs:
            shutil.move(str(md_outputs[0]), str(cache_dir / f"{stem}.md"))
        data = json.loads(json_dest.read_text(encoding="utf-8"))
    document = document_from_odl(data)
    if not any(block.text.strip() for block in document.blocks):
        raise ExtractionError(f"Kein Text im PDF {pdf_path.name!r} gefunden")
    return document
```

- [ ] **Step 4: Test grün, Lint, Commit**

```bash
uv run pytest tests/test_extractor.py -q && uv run ruff check .
git checkout -- uv.lock 2>/dev/null || true
git add backend/src/zilpzalp/extractor.py backend/tests/test_extractor.py
git commit -m "feat(extractor): json+markdown persistent in den Cache extrahieren"
```

---

### Task 6: Worker — submit/reanalyze + Cache-Verdrahtung

**Files:**
- Modify: `backend/src/zilpzalp/worker.py`
- Modify: `backend/src/zilpzalp/main.py` (`Worker(..., cache)`, `app.state.cache`, Startup-`prune`)
- Modify: `backend/tests/test_worker.py` (Signatur `extract(p, c)`, Cache übergeben, Reanalyse-Test)
- Modify: `backend/tests/test_main.py` (`extract`-Stub zweiargumentig)

**Interfaces:**
- Consumes: Task 4 (`DocumentCache`), Task 5 (`extract(path, cache_dir)`).
- Produces: `Worker(register, config_provider, cache)`. `submit(path)` enqueued `("extract", path)`; `reanalyze_all()` enqueued `("reanalyze", path)` für jeden Eintrag mit Cache-JSON. `_process(path, reuse=False)` nutzt bei `reuse=True` `cache.load_document` und überspringt `extract`.

- [ ] **Step 1: Failing tests**

In `backend/tests/test_worker.py`: ändere `_make_worker`:

```python
def _make_worker(config):
    from zilpzalp.cache import DocumentCache

    register = Queue()
    cache = DocumentCache(config.paths.cache)
    return register, Worker(register, lambda: config, cache)
```

Ändere alle `monkeypatch.setattr(worker_mod, "extract", lambda p: doc)` zu `lambda p, c: doc` (auch `boom(p)` → `boom(p, c)`), und `lambda p: Document(...)` analog. Ergänze:

```python
def test_reanalyze_all_uses_cache_and_skips_extract(tmp_path, config, monkeypatch):
    import json as _json

    pdf = Path(config.paths.watchfolder) / "doc.pdf"
    pdf.write_bytes(b"%PDF-1.4")
    # seed the cache so reanalyze can read it
    Path(config.paths.cache).joinpath("doc.json").write_text(
        _json.dumps({"type": "paragraph", "content": "Rechnungsdatum: 15.01.2026",
                     "page number": 1}),
        encoding="utf-8",
    )

    def boom(p, c):
        raise AssertionError("extract must not be called during reanalyze")

    monkeypatch.setattr(worker_mod, "extract", boom)

    register, worker = _make_worker(config)
    register.add(pdf)
    worker.reanalyze_all()
    # drain the single queued job synchronously
    action, path = worker._work.get_nowait()
    assert action == "reanalyze"
    worker._process(path, reuse=True)

    entry = register.get(pdf)
    assert entry.status == "ready"
    assert entry.suggestion.date_candidates[0].normalized == "2026-01-15"
```

In `backend/tests/test_main.py` (`test_watcher_populates_queue_on_startup`): `lambda p: Document(...)` → `lambda p, c: Document(...)`.

- [ ] **Step 2: Fehlschlag bestätigen**

Run: `uv run pytest tests/test_worker.py -q`
Expected: FAIL (`Worker.__init__` nimmt keinen `cache`; `reanalyze_all` fehlt).

- [ ] **Step 3: worker.py implementieren**

In `backend/src/zilpzalp/worker.py`:

`__init__` erweitern:

```python
    def __init__(
        self,
        register: Queue,
        config_provider: Callable[[], Config],
        cache,
    ) -> None:
        self._register = register
        self._config_provider = config_provider
        self._cache = cache
        self._work: _queue.Queue = _queue.Queue()
        self._thread = threading.Thread(
            target=self._run, name="zilpzalp-worker", daemon=True
        )
```

`submit`:

```python
    def submit(self, path: Path) -> None:
        """Watcher callback: register (dedup) and enqueue a fresh extraction."""
        if self._register.add(path):
            self._work.put(("extract", Path(path)))

    def reanalyze_all(self) -> None:
        """Re-run analyze+suggest for every entry that has a cached extraction,
        using the current config. Cheap: extraction is skipped."""
        for entry in self._register.list():
            if self._cache.load_document(entry.path) is not None:
                self._work.put(("reanalyze", entry.path))
```

`_run`:

```python
    def _run(self) -> None:
        while True:
            item = self._work.get()
            if item is _SHUTDOWN:
                return
            action, path = item
            try:
                self._process(path, reuse=(action == "reanalyze"))
            except Exception:  # never let the worker thread die
                logger.exception("Unerwarteter Fehler im Worker bei %s", item)
```

`_process`:

```python
    def _process(self, path: Path, reuse: bool = False) -> None:
        self._register.mark_analyzing(path)
        config = self._config_provider()
        document = self._cache.load_document(path) if reuse else None
        if document is None:
            try:
                document = extract(path, config.paths.cache)
            except ExtractionError as exc:
                self._move_to_error(path, config)
                self._register.mark_error(path, str(exc))
                return
            except Exception:
                logger.exception("Extraktionsfehler bei %s", path)
                self._register.mark_error(path, "technischer Fehler bei der Analyse")
                return
        try:
            analysis = analyze(document, config, file_dates=file_dates(path, config))
            suggestion = suggest(analysis, config)
        except Exception:
            logger.exception("Analysefehler bei %s", path)
            self._register.mark_error(path, "technischer Fehler bei der Analyse")
            return
        self._register.set_ready(path, suggestion)
```

- [ ] **Step 4: main.py verdrahten**

In `backend/src/zilpzalp/main.py`, `lifespan`: ergänze Import `from zilpzalp.cache import DocumentCache` und ersetze die Worker-Erzeugung:

```python
    cache = DocumentCache(config.paths.cache)
    app.state.cache = cache
    queue = Queue()
    app.state.queue = queue
    worker = Worker(queue, lambda: app.state.config, cache)
    app.state.worker = worker
    worker.start()
    watcher = Watcher(config.paths.watchfolder, worker.submit)
    app.state.watcher = watcher
    watcher.start()
    cache.prune([e.path.name for e in queue.list()])
```

(`cache.prune(...)` läuft nach dem initialen Scan; verwaiste Cache-Dateien ohne Inbox-PDF werden entfernt.)

- [ ] **Step 5: Tests grün, Suite, Lint, Commit**

```bash
uv run pytest -q && uv run ruff check .
git checkout -- uv.lock 2>/dev/null || true
git add backend/src/zilpzalp/worker.py backend/src/zilpzalp/main.py backend/tests/test_worker.py backend/tests/test_main.py
git commit -m "feat(worker): Cache-gestützte Re-Analyse, submit/reanalyze-Jobs"
```

---

### Task 7: Skip-Route, Cache-Cleanup, Re-Analyse bei Config-Save, UI + i18n

**Files:**
- Modify: `backend/src/zilpzalp/web/routes.py` (`/skip`, `_execute` Cache-Cleanup, `config_save` Re-Analyse, `config` in Queue-Kontexte)
- Modify: `backend/src/zilpzalp/web/templates/_queue_list.html` (Skip-Button)
- Modify: `backend/src/zilpzalp/web/templates/review.html` (Skip-Button)
- Modify: `backend/src/zilpzalp/web/locales/de.json` + `en.json`
- Modify: `backend/tests/test_routes.py`

**Interfaces:**
- Consumes: Task 3 (`processor.skip`), Task 4 (`app.state.cache`), Task 6 (`worker.reanalyze_all`).
- Produces: Route `POST /documents/{entry_id}/skip`. i18n-Keys `action.skip`, `confirm.skip`, `toast.skipped`, `original.delete`, `original.trash`.

- [ ] **Step 1: i18n-Keys**

In `backend/src/zilpzalp/web/locales/de.json`: ersetze die drei `original.*`-Zeilen (14–16) durch:

```json
  "original.delete": "löschen",
  "original.trash": "Papierkorb",
```

und ergänze im `action.*`-Block:

```json
  "action.skip": "Überspringen",
  "confirm.skip": "Dieses Dokument endgültig löschen?",
```

und im `toast.*`-Block:

```json
  "toast.skipped": "„{filename}“ wurde übersprungen.",
```

In `backend/src/zilpzalp/web/locales/en.json` analog: `original.move`/`original.keep` entfernen, `original.delete`: `"delete"`, `original.trash`: `"trash"`, `action.skip`: `"Skip"`, `confirm.skip`: `"Permanently delete this document?"`, `toast.skipped`: `"“{filename}” was skipped."`.

- [ ] **Step 2: Failing route-tests**

In `backend/tests/test_routes.py` ergänze:

```python
def test_skip_deletes_file_and_removes_entry_and_cache(client):
    cfg = app.state.config
    entry = _add_ready(client, "skipme.pdf")
    Path(cfg.paths.cache).joinpath("skipme.json").write_text("{}", encoding="utf-8")

    response = client.post(f"/documents/{entry.id}/skip", follow_redirects=False)

    assert response.status_code == 200
    assert response.headers.get("HX-Redirect", "").startswith("/queue")
    assert app.state.queue.get_by_id(entry.id) is None
    assert not (Path(cfg.paths.watchfolder) / "skipme.pdf").exists()
    assert not Path(cfg.paths.cache).joinpath("skipme.json").exists()


def test_skip_unknown_entry_redirects(client):
    response = client.post("/documents/deadbeef/skip", follow_redirects=False)
    assert response.status_code == 200
    assert response.headers.get("HX-Redirect") == "/queue"


def test_queue_list_shows_skip_button(client):
    _add_ready(client, "rechnung.pdf")
    body = client.get("/partials/queue").text
    assert "/skip" in body
    assert "Überspringen" in body


def test_config_save_triggers_reanalysis(client, monkeypatch):
    import yaml as _yaml

    called = {"n": 0}
    monkeypatch.setattr(app.state.worker, "reanalyze_all", lambda: called.__setitem__("n", called["n"] + 1))

    cfg_path = Path(app.state.config_path)
    new = _yaml.safe_load(cfg_path.read_text(encoding="utf-8"))
    new["summary_mode"] = "always"
    client.post("/config", data={"text": _yaml.safe_dump(new, allow_unicode=True)})

    assert called["n"] == 1
```

- [ ] **Step 3: Fehlschlag bestätigen**

Run: `uv run pytest tests/test_routes.py -k "skip or reanalysis" -q`
Expected: FAIL (Route/Re-Analyse fehlen).

- [ ] **Step 4: routes.py implementieren**

Import ergänzen: `from zilpzalp.processor import FileConflictError, ProcessorError, process, skip`.

In `_execute` (nach `process(...)`, vor `queue.remove`): Cache-Cleanup ergänzen:

```python
def _execute(request, entry, filename, target_paths, config):
    queue: Queue = request.app.state.queue
    lang = resolve_language(request)
    process(entry.path, filename, target_paths, config)
    queue.remove(entry.path)
    request.app.state.cache.remove(entry.path)
    message = translate("toast.filed", lang, filename=filename)
    resp = Response(status_code=200)
    resp.headers["HX-Redirect"] = "/queue?flash=" + quote(message) + "&kind=ok"
    return resp
```

Neue Route (z. B. nach `execute`):

```python
@router.post("/documents/{entry_id}/skip")
def skip_document(request: Request, entry_id: str):
    queue: Queue = request.app.state.queue
    entry = queue.get_by_id(entry_id)
    if entry is None:
        return Response(status_code=200, headers={"HX-Redirect": "/queue"})
    config: Config = request.app.state.config
    lang = resolve_language(request)
    try:
        skip(entry.path, config)
    except ProcessorError as exc:
        message = translate("toast.file_error", lang, error=str(exc))
        return Response(status_code=200, headers={
            "HX-Redirect": "/queue?flash=" + quote(message) + "&kind=err"
        })
    queue.remove(entry.path)
    request.app.state.cache.remove(entry.path)
    message = translate("toast.skipped", lang, filename=entry.path.name)
    return Response(status_code=200, headers={
        "HX-Redirect": "/queue?flash=" + quote(message) + "&kind=ok"
    })
```

In `config_save` (nach `request.app.state.config = config`):

```python
    request.app.state.worker.reanalyze_all()
```

`config` in die Queue-Kontexte aufnehmen, damit die Templates `config.original_handling` für `hx-confirm` kennen. In `queue_page` und `queue_partial` jeweils ergänzen:

```python
    context.update({"entries": queue.list(), "preselected_date": _preselected_date,
                    "config": request.app.state.config})
```

- [ ] **Step 5: Skip-Button in Templates**

In `backend/src/zilpzalp/web/templates/_queue_list.html`: ersetze den Aktions-Container (der `<div style="width:92px;...">`-Block) durch eine Variante mit Skip-Button neben „Prüfen":

```html
      <div style="display:flex;gap:8px;justify-content:flex-end;align-items:center">
        {% if entry.status == 'ready' %}
          <a class="btn sm primary" href="/review/{{ entry.id }}">{{ t('action.review') }}
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="width:14px;height:14px"><path d="M5 12h14M13 6l6 6-6 6"/></svg>
          </a>
        {% endif %}
        <button class="btn sm ghost" hx-post="/documents/{{ entry.id }}/skip"
                {% if config.original_handling == 'delete' %}hx-confirm="{{ t('confirm.skip') }}"{% endif %}>
          {{ t('action.skip') }}
        </button>
      </div>
```

In `backend/src/zilpzalp/web/templates/review.html`: ergänze in `review-actions` (Zeile 99–106) vor dem Confirm-Button einen Skip-Button:

```html
        <div class="review-actions">
          <a class="btn ghost" href="/queue">{{ t('action.cancel') }}</a>
          <button type="button" class="btn ghost" hx-post="/documents/{{ entry.id }}/skip"
                  {% if config.original_handling == 'delete' %}hx-confirm="{{ t('confirm.skip') }}"{% endif %}>
            {{ t('action.skip') }}
          </button>
          <button type="button" class="btn primary" id="confirm-btn" style="flex:1;justify-content:center"
                  hx-post="/documents/{{ entry.id }}/confirm" hx-include="#review-form" hx-target="#modal-root" hx-swap="innerHTML">
            {{ t('action.confirm') }}
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="width:15px;height:15px"><path d="M5 12h14M13 6l6 6-6 6"/></svg>
          </button>
        </div>
```

(Die `review_page`-Route gibt `config` bereits in den Kontext — siehe routes.py Zeile 159.)

- [ ] **Step 6: Tests grün, Suite, Lint, Commit**

```bash
uv run pytest -q && uv run ruff check .
git checkout -- uv.lock 2>/dev/null || true
git add backend/src/zilpzalp/web/routes.py backend/src/zilpzalp/web/templates/_queue_list.html backend/src/zilpzalp/web/templates/review.html backend/src/zilpzalp/web/locales/de.json backend/src/zilpzalp/web/locales/en.json backend/tests/test_routes.py
git commit -m "feat(ui): Skip-Button, Cache-Cleanup bei Ablage, Re-Analyse bei Config-Save"
```

---

### Task 8: Deployment — Entrypoint-Seeding, Default-/Beispiel-Config, Demo

**Files:**
- Create: `backend/config.default.yaml`
- Create: `docker-entrypoint.sh`
- Modify: `backend/config.example.yaml`
- Modify: `Dockerfile.backend`
- Modify: `docker-compose.yml`
- Modify: `.gitignore`
- Delete: `demo/config/config.yaml`, `demo/targets/**`
- Modify: `mkdocs/` Konfigurationsseite (Pfade/Patterns/Disposal)

**Interfaces:**
- Consumes: Task 1–3 (Schema).

- [ ] **Step 1: Default-Config schreiben**

Create `backend/config.default.yaml`:

```yaml
# Minimal-Konfiguration, die der Container-Entrypoint nach /config/config.yaml
# seedet, falls dort keine Datei liegt. Pfade kommen aus ZILPZALP_PATH_*.
original_handling: delete
summary_mode: on_conflict
default_pattern: standard
date_format: "%Y-%m-%d"
patterns:
  standard:
    template: "{date}__{sender}_{doctype}_{description}"
```

- [ ] **Step 2: Beispiel-Config aktualisieren**

Ersetze `backend/config.example.yaml` durch:

```yaml
# Beispielkonfiguration (Domäne). Infrastruktur-Pfade kommen aus Env-Variablen
# (ZILPZALP_PATH_INBOX/ERROR/TRASH/CACHE/OUTBOX), nicht aus dieser Datei.
original_handling: delete        # delete | trash
summary_mode: on_conflict        # always | on_conflict | never

default_pattern: standard
date_format: "%Y-%m-%d"

# Optional: zusätzliche Datums-Matcher (additiv zur eingebauten Erkennung).
date_patterns:
  - label: leistungsdatum
    regex: 'Leistungsdatum:\s*(\d{2}\.\d{2}\.\d{4})'

# Fehlt dieser Block, wird automatisch ein Default-Target "Outbox"
# (ZILPZALP_PATH_OUTBOX) angelegt.
targets:
  - name: Finanzen
    path: /targets/finanzen
    default: true

patterns:
  standard:
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

- [ ] **Step 3: Entrypoint-Script**

Create `docker-entrypoint.sh` (ausführbar):

```sh
#!/bin/sh
set -e

# Seed the domain config on first start so a mounted (empty) /config volume gets
# a real, editable file. An existing file is never overwritten.
: "${ZILPZALP_CONFIG:=/config/config.yaml}"
if [ ! -f "$ZILPZALP_CONFIG" ]; then
    mkdir -p "$(dirname "$ZILPZALP_CONFIG")"
    cp /app/backend/config.default.yaml "$ZILPZALP_CONFIG"
fi

exec "$@"
```

- [ ] **Step 4: Dockerfile anpassen**

In `Dockerfile.backend`, runtime-Stage: nach `COPY backend/src ./src` ergänzen:

```dockerfile
# Domänen-Default-Config + Entrypoint, der sie nach /config seedet, falls leer.
COPY backend/config.default.yaml /app/backend/config.default.yaml
COPY docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
RUN chmod +x /usr/local/bin/docker-entrypoint.sh
```

Ergänze vor der `CMD`-Zeile:

```dockerfile
ENTRYPOINT ["docker-entrypoint.sh"]
```

(`ENV ZILPZALP_CONFIG=/config/config.yaml` bleibt; `CMD ["uvicorn", ...]` bleibt unverändert.)

- [ ] **Step 5: docker-compose vereinfachen**

Ersetze in `docker-compose.yml` den `backend`-Service-Block durch:

```yaml
  backend:
    build:
      context: .
      dockerfile: Dockerfile.backend
    image: zilpzalp-backend
    ports:
      - "8000:8000"
    volumes:
      - ./demo/data:/data
    restart: unless-stopped
```

(Der `docs`-Service bleibt unverändert.)

- [ ] **Step 6: Demo & .gitignore bereinigen**

```bash
git rm -r demo/config demo/targets
```

Ersetze in `.gitignore` den Demo-Block durch:

```gitignore
# Demo: nur das Beispiel-PDF in der Inbox ist versioniert; generierte Ordner nicht.
/demo/data/inbox/*
!/demo/data/inbox/.gitkeep
!/demo/data/inbox/beispiel-rechnung.pdf
/demo/data/error/
/demo/data/processed/
/demo/data/trash/
/demo/data/outbox/
/demo/data/cache/
```

(Die App legt error/trash/outbox/cache beim Start unter dem `./demo/data`-Mount selbst an; `demo/data/processed` und seine `.gitkeep` mit `git rm` entfernen, falls vorhanden: `git rm demo/data/processed/.gitkeep demo/data/error/.gitkeep`.)

- [ ] **Step 7: mkdocs-Doku aktualisieren**

Suche die Konfigurationsseite: `grep -rl "watchfolder\|original_handling\|patterns" mkdocs/`. Dort: Pfad-Tabelle auf `ZILPZALP_PATH_*` umstellen, `patterns` als Map dokumentieren, `original_handling: delete|trash` erklären, Outbox-Default und die Persistenz von `/config` erwähnen. (Englisch.)

- [ ] **Step 8: Build-Smoke + Commit**

Run (Container-Build optional, falls Docker verfügbar):
`docker compose build backend` → erwartet erfolgreichen Build; sonst überspringen.

Run: `uv run pytest -q && uv run ruff check .`
Expected: PASS.

```bash
git checkout -- backend/uv.lock 2>/dev/null || true
git add -A
git commit -m "feat(deploy): Entrypoint-Seeding, ZILPZALP_PATH_* Defaults, Demo verschlankt

BREAKING CHANGE: config.yaml enthält keine paths mehr (kommen aus ZILPZALP_PATH_*);
original_handling akzeptiert nur noch delete|trash; patterns ist jetzt eine Map."
```

---

## Hinweise zur Reihenfolge & Backlog

- Tasks strikt in Reihenfolge ausführen; jeder endet mit grüner Suite + Lint.
- Nach Abschluss: in `docs/backlog.md` eine `## Umsetzung`-Zeile (Art `Feature`) mit dem Merge-Commit-SHA ergänzen und die zugehörigen Ideen aus „## Ideen / später" entfernen, sofern umgesetzt (Preview/Trash-leeren/Cache-Reuse/Re-Analyse-Button bleiben als Ideen bestehen).
