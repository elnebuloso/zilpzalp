from __future__ import annotations

import re
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ValidationError, field_validator, model_validator

KNOWN_PLACEHOLDERS = {"date", "sender", "doctype", "description"}
_PLACEHOLDER_RE = re.compile(r"\{([^}]*)\}")


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

    @field_validator("regex")
    @classmethod
    def _regex_compiles(cls, value: str) -> str:
        try:
            re.compile(value)
        except re.error as exc:
            raise ValueError(f"ungültiger regulärer Ausdruck {value!r}: {exc}")
        return value


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

    @field_validator("date_format")
    @classmethod
    def _date_format_has_directive(cls, value: str) -> str:
        if "%" not in value:
            raise ValueError(
                f"date_format {value!r} enthält keine strftime-Direktive (z. B. %Y-%m-%d)"
            )
        return value

    @model_validator(mode="after")
    def _check_paths_exist(self) -> "Config":
        required = [
            ("watchfolder", self.paths.watchfolder),
            ("error_folder", self.paths.error_folder),
        ]
        for label, folder in required:
            if not folder.is_dir():
                raise ValueError(
                    f"paths.{label} {str(folder)!r} existiert nicht oder ist kein Verzeichnis"
                )
        if self.original_handling == "move":
            processed = self.paths.processed_folder
            if processed is None:
                raise ValueError(
                    "paths.processed_folder ist erforderlich, wenn original_handling: move"
                )
            if not processed.is_dir():
                raise ValueError(
                    f"paths.processed_folder {str(processed)!r} existiert nicht "
                    "oder ist kein Verzeichnis"
                )
        return self

    @model_validator(mode="after")
    def _check_placeholders(self) -> "Config":
        templates = [("default_pattern", self.default_pattern)]
        templates += [
            (f"patterns[{i}].template ({p.name})", p.template)
            for i, p in enumerate(self.patterns)
        ]
        for where, template in templates:
            unknown = set(_PLACEHOLDER_RE.findall(template)) - KNOWN_PLACEHOLDERS
            if unknown:
                raise ValueError(
                    f"{where} enthält unbekannte Platzhalter {sorted(unknown)}; "
                    f"erlaubt sind {sorted(KNOWN_PLACEHOLDERS)}"
                )
        return self


def load_config(path: str | Path) -> Config:
    try:
        raw = Path(path).read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise ConfigError(
            f"Konfigurationsdatei {str(path)!r} kann nicht gelesen werden: {exc}"
        ) from exc
    try:
        data = yaml.safe_load(raw)
    except yaml.YAMLError as exc:
        raise ConfigError(
            f"Konfigurationsdatei {str(path)!r} ist kein gültiges YAML: {exc}"
        ) from exc
    if not isinstance(data, dict):
        raise ConfigError(
            f"Konfigurationsdatei {str(path)!r} muss ein YAML-Mapping enthalten"
        ) from None
    try:
        return Config(**data)
    except ValidationError as exc:
        raise ConfigError(_format_validation_error(path, exc)) from exc


def _format_validation_error(path: str | Path, exc: ValidationError) -> str:
    lines = [f"Konfigurationsdatei {str(path)!r} ist ungültig:"]
    for err in exc.errors():
        loc = ".".join(str(part) for part in err["loc"]) or "(Wurzel)"
        lines.append(f"  - {loc}: {err['msg']}")
    return "\n".join(lines)
