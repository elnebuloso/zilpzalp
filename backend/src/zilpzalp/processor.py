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
    original_action: Literal["moved", "deleted", "kept"]
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
