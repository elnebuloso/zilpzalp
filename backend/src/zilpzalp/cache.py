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

    def _html(self, name: str) -> Path:
        return self._base / (Path(name).stem + ".html")

    def load_document(self, path: Path | str) -> Document | None:
        json_file = self._json(Path(path).name)
        if not json_file.exists():
            return None
        data = json.loads(json_file.read_text(encoding="utf-8"))
        return document_from_odl(data)

    def _read(self, target: Path) -> str | None:
        if not target.exists():
            return None
        return target.read_text(encoding="utf-8")

    def read_markdown(self, path: Path | str) -> str | None:
        return self._read(self._md(Path(path).name))

    def read_html(self, path: Path | str) -> str | None:
        return self._read(self._html(Path(path).name))

    def read_json_text(self, path: Path | str) -> str | None:
        return self._read(self._json(Path(path).name))

    def remove(self, path: Path | str) -> None:
        name = Path(path).name
        self._json(name).unlink(missing_ok=True)
        self._md(name).unlink(missing_ok=True)
        self._html(name).unlink(missing_ok=True)

    def prune(self, valid_names: Iterable[str]) -> None:
        valid_stems = {Path(n).stem for n in valid_names}
        for artifact in (
            *self._base.glob("*.json"),
            *self._base.glob("*.md"),
            *self._base.glob("*.html"),
        ):
            if artifact.stem not in valid_stems:
                artifact.unlink(missing_ok=True)
