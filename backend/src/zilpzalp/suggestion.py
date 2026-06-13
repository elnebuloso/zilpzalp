from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from zilpzalp.analyzer import Analysis, DateCandidate
from zilpzalp.config import Config


@dataclass(frozen=True)
class Suggestion:
    filename: str
    date_candidates: list[DateCandidate] = field(default_factory=list)
    preselected_date_index: int | None = None
    sender: str = ""
    doctype: str = ""
    description: str = ""
    pattern_name: str | None = None
    target_paths: list[Path] = field(default_factory=list)


def _resolve_pattern(config: Config, pattern_name: str | None) -> str:
    if pattern_name:
        for pattern in config.patterns:
            if pattern.name == pattern_name:
                return pattern.template
    return config.default_pattern


def _preselect(candidates: list[DateCandidate], preferred_label: str | None) -> int | None:
    if not candidates:
        return None
    if preferred_label:
        wanted = preferred_label.lower()
        for i, c in enumerate(candidates):
            if c.label and wanted in c.label.lower():
                return i
    return 0


def suggest(analysis: Analysis, config: Config) -> Suggestion:
    sender = analysis.sender or ""
    doctype = analysis.doctype or ""
    description = ""
    pattern_name: str | None = None

    idx = _preselect(analysis.date_candidates, None)
    date_str = analysis.date_candidates[idx].normalized if idx is not None else ""
    template = _resolve_pattern(config, pattern_name)
    filename = (
        template.format(date=date_str, sender=sender, doctype=doctype, description=description)
        + ".pdf"
    )
    return Suggestion(
        filename=filename,
        date_candidates=list(analysis.date_candidates),
        preselected_date_index=idx,
        sender=sender,
        doctype=doctype,
        description=description,
        pattern_name=pattern_name,
        target_paths=[],
    )
