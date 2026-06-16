from __future__ import annotations

import os
import re
import tempfile
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ValidationError, field_validator, model_validator

KNOWN_PLACEHOLDERS = {"date", "sender", "doctype", "description"}
_PLACEHOLDER_RE = re.compile(r"\{([^}]*)\}")


class ConfigError(Exception):
    """Raised when config.yaml is missing, unparseable, or invalid."""


DEFAULT_PATHS = {
    "inbox": "/data/inbox",
    "error": "/data/error",
    "trash": "/data/trash",
    "cache": "/data/cache",
    "outbox": "/data/outbox",
}


class Paths(BaseModel):
    watchfolder: Path
    error_folder: Path
    trash: Path
    cache: Path


def load_paths() -> Paths:
    env = os.environ.get
    return Paths(
        watchfolder=Path(env("ZILPZALP_PATH_INBOX", DEFAULT_PATHS["inbox"])),
        error_folder=Path(env("ZILPZALP_PATH_ERROR", DEFAULT_PATHS["error"])),
        trash=Path(env("ZILPZALP_PATH_TRASH", DEFAULT_PATHS["trash"])),
        cache=Path(env("ZILPZALP_PATH_CACHE", DEFAULT_PATHS["cache"])),
    )


def outbox_path() -> Path:
    return Path(os.environ.get("ZILPZALP_PATH_OUTBOX", DEFAULT_PATHS["outbox"]))


class Target(BaseModel):
    name: str
    path: Path
    default: bool = False


class Pattern(BaseModel):
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
    patterns: dict[str, Pattern] = {}
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
    def _check_patterns(self) -> "Config":
        if not self.patterns:
            raise ValueError("patterns darf nicht leer sein")
        if self.default_pattern not in self.patterns:
            raise ValueError(
                f"default_pattern {self.default_pattern!r} verweist auf kein "
                f"definiertes Pattern; verfügbar: {sorted(self.patterns)}"
            )
        for name, pattern in self.patterns.items():
            found = set(_PLACEHOLDER_RE.findall(pattern.template))
            if "" in found:
                raise ValueError(f"patterns.{name}: leerer Platzhalter {{}}")
            unknown = found - KNOWN_PLACEHOLDERS
            if unknown:
                raise ValueError(
                    f"patterns.{name} enthält unbekannte Platzhalter {sorted(unknown)}; "
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
    data.pop("paths", None)  # paths come from env, never from YAML
    data["paths"] = load_paths()
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


def save_config(path: str | Path, text: str) -> Config:
    """Validate *text* with the same rules as load_config and, only if valid,
    write it to *path* atomically. On any error the existing file is left
    untouched (Design-Spec §2.3 / ui.md Konfiguration)."""
    path = Path(path)
    try:
        data = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise ConfigError(f"Eingabe ist kein gültiges YAML: {exc}") from exc
    if not isinstance(data, dict):
        raise ConfigError("Konfiguration muss ein YAML-Mapping enthalten")
    data.pop("paths", None)  # paths come from env, never from YAML
    data["paths"] = load_paths()
    try:
        config = Config(**data)
    except ValidationError as exc:
        raise ConfigError(_format_validation_error(path, exc)) from exc

    fd, tmp_name = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(text)
        os.replace(tmp_name, path)
    except OSError:
        Path(tmp_name).unlink(missing_ok=True)
        raise
    return config
