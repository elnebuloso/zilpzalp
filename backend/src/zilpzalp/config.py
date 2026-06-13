from __future__ import annotations

from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ValidationError


class ConfigError(Exception):
    """Raised when config.yaml is missing, unparseable, or invalid."""


class Paths(BaseModel):
    watchfolder: Path
    error_folder: Path
    processed_folder: Path | None = None


class Target(BaseModel):
    name: str
    path: Path
    default: bool = False


class Pattern(BaseModel):
    name: str
    template: str


class DatePattern(BaseModel):
    label: str
    regex: str


class Config(BaseModel):
    paths: Paths
    original_handling: Literal["move", "delete", "keep"]
    summary_mode: Literal["always", "on_conflict", "never"]
    default_pattern: str
    date_format: str
    date_patterns: list[DatePattern] = []
    targets: list[Target] = []
    patterns: list[Pattern] = []
    # rules are consumed by the analyzer/suggestion engine (Milestone 2);
    # kept opaque here on purpose.
    rules: list[dict] = []


def load_config(path: str | Path) -> Config:
    try:
        raw = Path(path).read_text(encoding="utf-8")
    except OSError as exc:
        raise ConfigError(
            f"Konfigurationsdatei {str(path)!r} kann nicht gelesen werden: {exc}"
        )
    try:
        data = yaml.safe_load(raw)
    except yaml.YAMLError as exc:
        raise ConfigError(
            f"Konfigurationsdatei {str(path)!r} ist kein gültiges YAML: {exc}"
        )
    if not isinstance(data, dict):
        raise ConfigError(
            f"Konfigurationsdatei {str(path)!r} muss ein YAML-Mapping enthalten"
        )
    try:
        return Config(**data)
    except ValidationError as exc:
        raise ConfigError(_format_validation_error(path, exc))


def _format_validation_error(path: str | Path, exc: ValidationError) -> str:
    lines = [f"Konfigurationsdatei {str(path)!r} ist ungültig:"]
    for err in exc.errors():
        loc = ".".join(str(part) for part in err["loc"]) or "(Wurzel)"
        lines.append(f"  - {loc}: {err['msg']}")
    return "\n".join(lines)
