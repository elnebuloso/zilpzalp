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
        shutil.copy2(source, dest)

    return ProcessResult(copied=destinations, original_action="kept")
