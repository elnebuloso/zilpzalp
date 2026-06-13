# Dateioperationen (`processor`) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the `processor` module that — on user confirmation — copies a PDF into one or more target folders under its final name and then handles the original in the watchfolder (move/delete/keep), refusing to overwrite anything.

**Architecture:** A single pure-ish module `processor.py` with one entry point `process(source, filename, targets, config)`. It depends **only** on `config` (per Design-Spec §3 component table). All conflict/precondition checks run *before* any file is touched, so a rejected call leaves the filesystem unchanged (no partial copies, no orphaned original). Name conflicts are surfaced as a dedicated exception — the MVP **never** auto-suffixes (§4.1); the user decides later in the UI. Technical runtime errors (missing target dir, permission) raise `ProcessorError`; the stdout-logging + transient-UI presentation of those errors (§6) belongs to the **web layer (Milestone 5)** and is out of scope here.

**Tech Stack:** Python 3.12, `shutil`, `pathlib`, pytest, uv. src-layout under `backend/src/zilpzalp/`.

**Scope (Roadmap Milestone 3 — Design-Spec §4.1, §6):**
- ✅ Copy to chosen target folder(s) under the confirmed filename.
- ✅ Original handling: `move` (→ `processed_folder`), `delete`, `keep`.
- ✅ Name conflict in a target → refuse (no auto-suffix), surface for user decision.
- ✅ Safety: refuse destructive original-handling when there is no successful copy (empty targets / missing target dir), and never overwrite the original in `processed_folder`.

**Out of scope (later milestones / other modules):**
- ❌ `watcher`, `queue` (Milestone 4).
- ❌ Web routes, Review-View, the `summary_mode` summary screen, transient UI error display, stdout logging wiring (Milestone 5).
- ❌ Coupling to `analyzer`/`suggestion` types — `process` takes the **user-confirmed** primitives (`filename`, `targets`), not a `Suggestion` object.

---

## File Structure

| File | Responsibility |
|---|---|
| `backend/src/zilpzalp/processor.py` | **Create.** `process()` + `ProcessResult` + `ProcessorError`/`FileConflictError`. The only place (besides `extractor`) that mutates the filesystem. |
| `backend/tests/test_processor.py` | **Create.** Unit tests against real temp dirs: copy, move/delete/keep, conflict, safety guards. |

**Design notes for the implementer:**
- `filename` already includes the `.pdf` extension (the `suggestion` module appends it). `processor` uses it verbatim — it does not build or alter names.
- `config.original_handling` is a validated `Literal["move", "delete", "keep"]`; when it is `"move"`, `config.paths.processed_folder` is **guaranteed non-`None`** by `Config` validation ([config.py:82-92](../../../backend/src/zilpzalp/config.py#L82-L92)). So no `None` check is needed on the `move` path.
- Use `shutil.copy2` (preserves mtime) for copies and `shutil.move` for the original.
- Ordering inside `process()`: (1) validate `targets` non-empty, (2) validate each target dir exists, (3) check each target destination for conflict, (4) for `move`, check the `processed_folder` destination for conflict — **only then** (5) copy to all targets and (6) handle the original. This guarantees "rejected call → filesystem unchanged".

---

### Task 1: Module skeleton — copy to target folder(s), `keep` original

**Files:**
- Create: `backend/src/zilpzalp/processor.py`
- Test: `backend/tests/test_processor.py`

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/test_processor.py`:

```python
from pathlib import Path

import pytest

from zilpzalp.config import load_config
from zilpzalp.processor import FileConflictError, ProcessorError, process


def _config(tmp_path: Path, original_handling: str = "keep", extra: str = ""):
    """Build a validated Config whose paths point at real temp dirs."""
    for sub in ("inbox", "error", "processed"):
        (tmp_path / sub).mkdir(exist_ok=True)
    cfg = tmp_path / "config.yaml"
    cfg.write_text(
        f"""
paths:
  watchfolder: {tmp_path / "inbox"}
  error_folder: {tmp_path / "error"}
  processed_folder: {tmp_path / "processed"}
original_handling: {original_handling}
summary_mode: never
default_pattern: "{{date}}__{{sender}}_{{doctype}}_{{description}}"
date_format: "%Y-%m-%d"
{extra}
""",
        encoding="utf-8",
    )
    return load_config(cfg)


def _source(tmp_path: Path, name: str = "orig.pdf", content: bytes = b"%PDF-1.4 hello") -> Path:
    p = tmp_path / "inbox" / name
    p.write_bytes(content)
    return p


def _target(tmp_path: Path, name: str) -> Path:
    d = tmp_path / name
    d.mkdir(exist_ok=True)
    return d


def test_copies_to_single_target_and_keeps_original(tmp_path):
    config = _config(tmp_path, "keep")
    source = _source(tmp_path)
    target = _target(tmp_path, "finanzen")

    result = process(source, "2026-01-15__Acme.pdf", [target], config)

    dest = target / "2026-01-15__Acme.pdf"
    assert dest.read_bytes() == b"%PDF-1.4 hello"   # copy created with confirmed name
    assert source.exists()                          # keep: original untouched
    assert result.copied == [dest]
    assert result.original_action == "kept"
    assert result.original_destination is None


def test_copies_to_multiple_targets(tmp_path):
    config = _config(tmp_path, "keep")
    source = _source(tmp_path)
    t1 = _target(tmp_path, "finanzen")
    t2 = _target(tmp_path, "versicherungen")

    result = process(source, "doc.pdf", [t1, t2], config)

    assert (t1 / "doc.pdf").read_bytes() == b"%PDF-1.4 hello"
    assert (t2 / "doc.pdf").read_bytes() == b"%PDF-1.4 hello"
    assert result.copied == [t1 / "doc.pdf", t2 / "doc.pdf"]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && uv run pytest tests/test_processor.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'zilpzalp.processor'`

- [ ] **Step 3: Write the minimal implementation**

Create `backend/src/zilpzalp/processor.py`:

```python
from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path

from zilpzalp.config import Config


class ProcessorError(Exception):
    """Base class for file-operation failures during processing."""


class FileConflictError(ProcessorError):
    """A destination file already exists. The MVP never auto-suffixes (§4.1);
    the user decides how to resolve the conflict."""

    def __init__(self, destination: Path) -> None:
        self.destination = destination
        super().__init__(f"Zieldatei existiert bereits: {destination}")


@dataclass(frozen=True)
class ProcessResult:
    copied: list[Path]
    original_action: str                       # "moved" | "deleted" | "kept"
    original_destination: Path | None = None   # set only for "moved"


def process(
    source: Path,
    filename: str,
    targets: list[Path],
    config: Config,
) -> ProcessResult:
    """Copy *source* as *filename* into every target folder, then handle the
    original per config.original_handling.

    All precondition/conflict checks run before any file is touched, so a
    rejected call leaves the filesystem unchanged. Raises ProcessorError on a
    missing/empty target, FileConflictError on an existing destination.
    """
    destinations = [target / filename for target in targets]

    for dest in destinations:
        shutil.copy2(source, dest)

    return ProcessResult(copied=destinations, original_action="kept")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && uv run pytest tests/test_processor.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add backend/src/zilpzalp/processor.py backend/tests/test_processor.py
git commit -m "feat(processor): copy PDF to target folders, keep original"
```

---

### Task 2: Original handling — `move` and `delete`

**Files:**
- Modify: `backend/src/zilpzalp/processor.py`
- Test: `backend/tests/test_processor.py`

- [ ] **Step 1: Write the failing tests**

Append to `backend/tests/test_processor.py`:

```python
def test_move_relocates_original_to_processed(tmp_path):
    config = _config(tmp_path, "move")
    source = _source(tmp_path, "orig.pdf")
    target = _target(tmp_path, "finanzen")

    result = process(source, "doc.pdf", [target], config)

    assert (target / "doc.pdf").exists()                      # copy made
    assert not source.exists()                                # original moved away
    processed = tmp_path / "processed" / "orig.pdf"           # keeps original name
    assert processed.read_bytes() == b"%PDF-1.4 hello"
    assert result.original_action == "moved"
    assert result.original_destination == processed


def test_delete_removes_original(tmp_path):
    config = _config(tmp_path, "delete")
    source = _source(tmp_path)
    target = _target(tmp_path, "finanzen")

    result = process(source, "doc.pdf", [target], config)

    assert (target / "doc.pdf").exists()                      # copy made
    assert not source.exists()                                # original deleted
    assert result.original_action == "deleted"
    assert result.original_destination is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && uv run pytest tests/test_processor.py -v`
Expected: FAIL — both new tests fail (`original_action` is `"kept"`, source still exists).

- [ ] **Step 3: Update the implementation**

Replace the body of `process()` (everything after the docstring) in `backend/src/zilpzalp/processor.py` with:

```python
    destinations = [target / filename for target in targets]

    processed_dest: Path | None = None
    if config.original_handling == "move":
        processed_dest = config.paths.processed_folder / source.name

    for dest in destinations:
        shutil.copy2(source, dest)

    if config.original_handling == "move":
        shutil.move(str(source), str(processed_dest))
        return ProcessResult(
            copied=destinations,
            original_action="moved",
            original_destination=processed_dest,
        )
    if config.original_handling == "delete":
        source.unlink()
        return ProcessResult(copied=destinations, original_action="deleted")
    return ProcessResult(copied=destinations, original_action="kept")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && uv run pytest tests/test_processor.py -v`
Expected: PASS (4 passed)

- [ ] **Step 5: Commit**

```bash
git add backend/src/zilpzalp/processor.py backend/tests/test_processor.py
git commit -m "feat(processor): handle original via move and delete"
```

---

### Task 3: Name-conflict detection (no auto-suffix, no partial writes)

**Files:**
- Modify: `backend/src/zilpzalp/processor.py`
- Test: `backend/tests/test_processor.py`

- [ ] **Step 1: Write the failing tests**

Append to `backend/tests/test_processor.py`:

```python
def test_conflict_at_target_raises_and_leaves_original(tmp_path):
    config = _config(tmp_path, "delete")
    source = _source(tmp_path)
    target = _target(tmp_path, "finanzen")
    existing = target / "doc.pdf"
    existing.write_bytes(b"already here")

    with pytest.raises(FileConflictError):
        process(source, "doc.pdf", [target], config)

    assert existing.read_bytes() == b"already here"   # not overwritten (no auto-suffix)
    assert source.exists()                            # delete did not run


def test_conflict_preflight_prevents_partial_copy(tmp_path):
    config = _config(tmp_path, "keep")
    source = _source(tmp_path)
    t1 = _target(tmp_path, "finanzen")
    t2 = _target(tmp_path, "versicherungen")
    (t2 / "doc.pdf").write_bytes(b"already here")      # conflict in the SECOND target

    with pytest.raises(FileConflictError):
        process(source, "doc.pdf", [t1, t2], config)

    assert not (t1 / "doc.pdf").exists()               # first target NOT written either
    assert source.exists()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && uv run pytest tests/test_processor.py -v`
Expected: FAIL — no `FileConflictError` raised; `test_conflict_preflight_prevents_partial_copy` shows `t1/doc.pdf` was written before the second copy errored on overwrite (or no error at all).

- [ ] **Step 3: Update the implementation**

In `process()`, insert the conflict pre-flight **before** the copy loop. The body after the docstring becomes:

```python
    destinations = [target / filename for target in targets]

    for dest in destinations:
        if dest.exists():
            raise FileConflictError(dest)

    processed_dest: Path | None = None
    if config.original_handling == "move":
        processed_dest = config.paths.processed_folder / source.name
        if processed_dest.exists():
            raise FileConflictError(processed_dest)

    for dest in destinations:
        shutil.copy2(source, dest)

    if config.original_handling == "move":
        shutil.move(str(source), str(processed_dest))
        return ProcessResult(
            copied=destinations,
            original_action="moved",
            original_destination=processed_dest,
        )
    if config.original_handling == "delete":
        source.unlink()
        return ProcessResult(copied=destinations, original_action="deleted")
    return ProcessResult(copied=destinations, original_action="kept")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && uv run pytest tests/test_processor.py -v`
Expected: PASS (6 passed)

- [ ] **Step 5: Commit**

```bash
git add backend/src/zilpzalp/processor.py backend/tests/test_processor.py
git commit -m "feat(processor): reject name conflicts without auto-suffix"
```

---

### Task 4: Safety guards — empty/missing targets, processed-folder conflict

**Files:**
- Modify: `backend/src/zilpzalp/processor.py`
- Test: `backend/tests/test_processor.py`

- [ ] **Step 1: Write the failing tests**

Append to `backend/tests/test_processor.py`:

```python
def test_empty_targets_raises_and_keeps_original(tmp_path):
    config = _config(tmp_path, "delete")
    source = _source(tmp_path)

    with pytest.raises(ProcessorError):
        process(source, "doc.pdf", [], config)

    assert source.exists()        # no copy => never delete the original


def test_missing_target_dir_raises_and_leaves_original(tmp_path):
    config = _config(tmp_path, "delete")
    source = _source(tmp_path)
    missing = tmp_path / "nope"   # never created

    with pytest.raises(ProcessorError):
        process(source, "doc.pdf", [missing], config)

    assert source.exists()        # original untouched


def test_move_conflict_in_processed_raises_before_copy(tmp_path):
    config = _config(tmp_path, "move")
    source = _source(tmp_path, "orig.pdf")
    target = _target(tmp_path, "finanzen")
    (tmp_path / "processed" / "orig.pdf").write_bytes(b"old")   # would be overwritten by move

    with pytest.raises(FileConflictError):
        process(source, "doc.pdf", [target], config)

    assert not (target / "doc.pdf").exists()   # nothing copied
    assert source.exists()                     # original not moved
    assert (tmp_path / "processed" / "orig.pdf").read_bytes() == b"old"  # not overwritten
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && uv run pytest tests/test_processor.py -v`
Expected: FAIL — `test_empty_targets_raises_and_keeps_original` deletes the original with no copy; `test_missing_target_dir_raises_and_leaves_original` raises a raw `FileNotFoundError` from `shutil.copy2` *after* nothing/leaves inconsistent state (not a `ProcessorError`). (`test_move_conflict_in_processed_raises_before_copy` already passes from Task 3 — keep it as a regression guard.)

- [ ] **Step 3: Update the implementation**

In `process()`, add the empty-target and missing-dir checks at the very start of the body (before building `destinations`). The body after the docstring becomes:

```python
    if not targets:
        raise ProcessorError("keine Zielordner angegeben")
    for target in targets:
        if not target.is_dir():
            raise ProcessorError(f"Zielordner fehlt: {target}")

    destinations = [target / filename for target in targets]

    for dest in destinations:
        if dest.exists():
            raise FileConflictError(dest)

    processed_dest: Path | None = None
    if config.original_handling == "move":
        processed_dest = config.paths.processed_folder / source.name
        if processed_dest.exists():
            raise FileConflictError(processed_dest)

    for dest in destinations:
        shutil.copy2(source, dest)

    if config.original_handling == "move":
        shutil.move(str(source), str(processed_dest))
        return ProcessResult(
            copied=destinations,
            original_action="moved",
            original_destination=processed_dest,
        )
    if config.original_handling == "delete":
        source.unlink()
        return ProcessResult(copied=destinations, original_action="deleted")
    return ProcessResult(copied=destinations, original_action="kept")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && uv run pytest tests/test_processor.py -v`
Expected: PASS (9 passed)

- [ ] **Step 5: Commit**

```bash
git add backend/src/zilpzalp/processor.py backend/tests/test_processor.py
git commit -m "feat(processor): guard against empty/missing targets and processed overwrite"
```

---

### Task 5: Final verification — full suite + lint

**Files:** none (verification only)

- [ ] **Step 1: Run the full test suite (excluding the slow JVM integration branch)**

Run: `cd backend && uv run pytest -m "not integration" -v`
Expected: PASS — all existing tests plus the 9 new `test_processor.py` tests pass.

- [ ] **Step 2: Lint**

Run: `cd backend && uv run ruff check src/zilpzalp/processor.py tests/test_processor.py`
Expected: `All checks passed!`

- [ ] **Step 3: Commit only if lint produced fixes**

```bash
# Only if ruff reported and you applied fixes:
git add backend/src/zilpzalp/processor.py backend/tests/test_processor.py
git commit -m "style(processor): satisfy ruff"
```

---

## Self-Review

**1. Spec coverage (Design-Spec §4.1, §6 + Roadmap Milestone 3):**
- "Copy an Zielordner" → Tasks 1–2 (single + multiple targets). ✅
- "Original-Handling move/delete/keep" → Task 1 (keep), Task 2 (move, delete). ✅
- "Namenskonflikt im Ziel → Nutzer entscheidet (kein Auto-Suffix)" → Task 3 (`FileConflictError`, no overwrite, no partial copy). ✅
- §6 "technischer Laufzeitfehler (Zielpfad weg, Permission)" → Task 4 surfaces missing target dir as `ProcessorError`; permission errors propagate as `OSError`. stdout-logging/transient-UI presentation is explicitly deferred to Milestone 5 (web layer) — noted in the header. ✅
- §7 test requirement "Copy + Original-Handling gegen Temp-Verzeichnisse; Namenskonflikt" → all tests run against `tmp_path`. ✅
- Safety against data loss (no copy ⇒ never destroy original; never overwrite the moved original) → Task 4. ✅ (Design decision beyond the literal spec, documented in the header.)

**2. Placeholder scan:** No "TBD"/"add error handling"/"similar to Task N". Every code step shows complete, copy-pasteable content. ✅

**3. Type consistency:** `process(source, filename, targets, config)` signature, `ProcessResult(copied, original_action, original_destination)`, `ProcessorError`/`FileConflictError(destination)` are used identically across all tasks and tests. `original_action` values `"kept"`/`"moved"`/`"deleted"` are consistent. ✅
