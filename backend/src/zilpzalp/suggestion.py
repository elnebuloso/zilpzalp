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


def _rule_matches(rule: dict, analysis: Analysis) -> bool:
    match = rule.get("match", {}) or {}
    sender_contains = match.get("sender_contains")
    if sender_contains and sender_contains.lower() not in (analysis.sender or "").lower():
        return False
    keywords_any = match.get("keywords_any")
    if keywords_any and not any(
        k.lower() in analysis.full_text.lower() for k in keywords_any
    ):
        return False
    return True


def _first_matching_rule(analysis: Analysis, config: Config) -> dict | None:
    for rule in config.rules:
        if _rule_matches(rule, analysis):
            return rule
    return None


def _resolve_targets(config: Config, names: list[str]) -> list[Path]:
    if names:
        wanted = set(names)
        return [t.path for t in config.targets if t.name in wanted]
    return [t.path for t in config.targets if t.default]


def suggest(analysis: Analysis, config: Config) -> Suggestion:
    sender = analysis.sender or ""
    doctype = analysis.doctype or ""
    description = ""
    pattern_name: str | None = None
    preferred_label: str | None = None
    target_names: list[str] = []

    rule = _first_matching_rule(analysis, config)
    if rule:
        apply = rule.get("apply", {}) or {}
        sender = apply.get("sender", sender)
        doctype = apply.get("doctype", doctype)
        description = apply.get("description", description)
        pattern_name = apply.get("pattern", pattern_name)
        preferred_label = apply.get("preferred_date")
        target_names = apply.get("targets", []) or []

    idx = _preselect(analysis.date_candidates, preferred_label)
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
        target_paths=_resolve_targets(config, target_names),
    )
