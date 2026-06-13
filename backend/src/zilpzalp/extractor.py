from __future__ import annotations

from typing import Any

from zilpzalp.document import Block, BlockKind, Document

# --- ODL-JSON-Schlüssel (gegen tests/fixtures/SCHEMA_NOTES.md prüfen/anpassen) ---
_KEY_TYPE = "type"
_KEY_TEXT = "content"
_KEY_PAGE = "page number"
_KEY_BBOX = "bounding box"
_KEY_HEADING_LEVEL = "heading level"
_KEY_CHILDREN = "kids"  # Falls SCHEMA_NOTES "children"/anderen Namen zeigt: hier anpassen.

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


def _walk(node: Any, blocks: list[Block]) -> None:
    if isinstance(node, list):
        for child in node:
            _walk(child, blocks)
        return
    if not isinstance(node, dict):
        return
    kind = _KIND_MAP.get(str(node.get(_KEY_TYPE, "")).lower())
    if kind == "table":
        return  # Tabellen behandelt Task 5; hier (noch) überspringen, NICHT hineinlaufen.
    if kind is not None:
        block = _simple_block(node, kind)
        if block is not None:
            blocks.append(block)
    _walk(node.get(_KEY_CHILDREN, []), blocks)


def document_from_odl(data: Any) -> Document:
    blocks: list[Block] = []
    _walk(data, blocks)
    return Document(blocks=blocks)
