from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

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


def _dispose(source: Path, trash: Path, mode: str) -> tuple[str, Path | None]:
    """Remove the inbox original. *mode* is "delete" or "trash"; the caller
    chooses it per situation (when_filed for filing, when_removed for removal)."""
    if mode == "trash":
        dest = _unique_name(trash, source.name)
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

    action, dest = _dispose(source, config.paths.trash, config.originals.when_filed)
    return ProcessResult(copied=destinations, original_action=action, original_destination=dest)


def remove(source: Path, config: Config) -> ProcessResult:
    """Discard an inbox original on explicit removal, per
    config.originals.when_removed. Tolerant of an already-missing original
    (e.g. an error entry whose file was moved to error/): no disposition, no
    error — the caller still drops the queue entry."""
    if not source.exists():
        return ProcessResult(copied=[], original_action="deleted", original_destination=None)
    action, dest = _dispose(source, config.paths.trash, config.originals.when_removed)
    return ProcessResult(copied=[], original_action=action, original_destination=dest)
