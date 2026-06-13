import pytest
import yaml


@pytest.fixture
def valid_config(tmp_path):
    """A complete, valid config dict whose paths point at real temp dirs."""
    for sub in ("inbox", "error", "processed", "finanzen"):
        (tmp_path / sub).mkdir()
    return {
        "paths": {
            "watchfolder": str(tmp_path / "inbox"),
            "error_folder": str(tmp_path / "error"),
            "processed_folder": str(tmp_path / "processed"),
        },
        "original_handling": "move",
        "summary_mode": "on_conflict",
        "default_pattern": "{date}__{sender}_{doctype}_{description}",
        "date_format": "%Y-%m-%d",
        "date_patterns": [],
        "targets": [
            {"name": "Finanzen", "path": str(tmp_path / "finanzen"), "default": False}
        ],
        "patterns": [
            {"name": "standard", "template": "{date}__{sender}_{doctype}_{description}"}
        ],
        "rules": [],
    }


@pytest.fixture
def write_config(tmp_path):
    """Write a config dict to <tmp_path>/config.yaml and return its path."""

    def _write(data):
        path = tmp_path / "config.yaml"
        path.write_text(yaml.safe_dump(data), encoding="utf-8")
        return path

    return _write
