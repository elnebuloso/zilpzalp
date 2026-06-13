from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

BlockKind = Literal["heading", "paragraph", "table", "list", "caption"]


@dataclass(frozen=True)
class Block:
    kind: BlockKind
    text: str                                   # Plaintext des Blocks
    page: int
    bbox: tuple[float, float, float, float]      # (links, unten, rechts, oben), PDF-Punkte
    level: int | None = None                     # nur bei heading: Hierarchieebene
    cells: list[list[str]] | None = None         # nur bei table: Zeilen × Spalten


@dataclass(frozen=True)
class Document:
    blocks: list[Block]                          # in korrigierter Lesereihenfolge
