from __future__ import annotations

from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel


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


def load_config(path: Path) -> Config:
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    return Config(**data)
