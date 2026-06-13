from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import Any

import opendataloader_pdf

from zilpzalp.document import Block, BlockKind, Document

# --- ODL-JSON-Schlüssel (gegen tests/fixtures/SCHEMA_NOTES.md prüfen/anpassen) ---
_KEY_TYPE = "type"
_KEY_TEXT = "content"
_KEY_PAGE = "page number"
_KEY_BBOX = "bounding box"
_KEY_HEADING_LEVEL = "heading level"
_KEY_CHILDREN = "kids"  # Falls SCHEMA_NOTES "children"/anderen Namen zeigt: hier anpassen.
_KEY_ROWS = "rows"        # Liste der Tabellenzeilen
_KEY_CELLS = "cells"      # Liste der Zellen je Zeile

# ODL-Typ → unser BlockKind. Unbekannte Typen werden übersprungen.
_KIND_MAP: dict[str, BlockKind] = {
    "heading": "heading",
    "title": "heading",
    "paragraph": "paragraph",
    "text": "paragraph",
    "list": "list",
    "caption": "caption",
    "table": "table",
}


def _bbox(node: dict[str, Any]) -> tuple[float, float, float, float]:
    raw = node.get(_KEY_BBOX) or [0.0, 0.0, 0.0, 0.0]
    left, bottom, right, top = (float(v) for v in raw[:4])
    return (left, bottom, right, top)


def _simple_block(node: dict[str, Any], kind: BlockKind) -> Block | None:
    text = (node.get(_KEY_TEXT) or "").strip()
    if not text:
        return None
    level = node.get(_KEY_HEADING_LEVEL) if kind == "heading" else None
    return Block(
        kind=kind,
        text=text,
        page=int(node.get(_KEY_PAGE, 1)),
        bbox=_bbox(node),
        level=int(level) if level is not None else None,
    )


def _table_cells(node: dict[str, Any]) -> list[list[str]]:
    rows: list[list[str]] = []
    for row in node.get(_KEY_ROWS, []) or []:
        cells = []
        for cell in row.get(_KEY_CELLS, []) or []:
            # Eine Zelle kann selbst verschachtelte Text-Knoten haben -> einsammeln.
            parts: list[Block] = []
            _walk(cell, parts)
            inline = (cell.get(_KEY_TEXT) or "").strip()
            text = inline or " ".join(p.text for p in parts).strip()
            cells.append(text)
        if cells:
            rows.append(cells)
    return rows


def _table_block(node: dict[str, Any]) -> Block | None:
    cells = _table_cells(node)
    if not cells:
        return None
    text = "\n".join(" ".join(row) for row in cells)
    return Block(kind="table", text=text, page=int(node.get(_KEY_PAGE, 1)), bbox=_bbox(node), cells=cells)


def _walk(node: Any, blocks: list[Block]) -> None:
    if isinstance(node, list):
        for child in node:
            _walk(child, blocks)
        return
    if not isinstance(node, dict):
        return
    kind = _KIND_MAP.get(str(node.get(_KEY_TYPE, "")).lower())
    if kind == "table":
        block = _table_block(node)
        if block is not None:
            blocks.append(block)
        return  # nicht zusätzlich in die Zellen hineinlaufen
    if kind is not None:
        block = _simple_block(node, kind)
        if block is not None:
            blocks.append(block)
    _walk(node.get(_KEY_CHILDREN, []), blocks)


def document_from_odl(data: Any) -> Document:
    blocks: list[Block] = []
    _walk(data, blocks)
    return Document(blocks=blocks)


class ExtractionError(Exception):
    """PDF lieferte keinen verwertbaren Text (korrupt, leer oder reiner Scan)."""


def extract(pdf_path: str | Path) -> Document:
    pdf_path = Path(pdf_path)
    with tempfile.TemporaryDirectory() as tmp:
        opendataloader_pdf.convert(
            input_path=[str(pdf_path)],
            output_dir=tmp,
            format="json",
        )
        outputs = list(Path(tmp).glob("*.json"))
        if not outputs:
            raise ExtractionError(f"OpenDataLoader erzeugte keine Ausgabe fuer {pdf_path.name!r}")
        data = json.loads(outputs[0].read_text(encoding="utf-8"))
    # TemporaryDirectory ist hier bereits geloescht -> kein Volltext bleibt auf Platte.
    document = document_from_odl(data)
    if not any(block.text.strip() for block in document.blocks):
        raise ExtractionError(f"Kein Text im PDF {pdf_path.name!r} gefunden")
    return document
