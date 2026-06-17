import pytest
import yaml


@pytest.fixture(autouse=True)
def env_paths(tmp_path, monkeypatch):
    """Point all ZILPZALP_PATH_* at fresh temp dirs and create them, so every
    test runs against a writable, isolated /data layout."""
    mapping = {
        "ZILPZALP_PATH_INBOX": tmp_path / "inbox",
        "ZILPZALP_PATH_ERROR": tmp_path / "error",
        "ZILPZALP_PATH_TRASH": tmp_path / "trash",
        "ZILPZALP_PATH_CACHE": tmp_path / "cache",
        "ZILPZALP_PATH_OUTBOX": tmp_path / "outbox",
    }
    for var, path in mapping.items():
        path.mkdir(parents=True, exist_ok=True)
        monkeypatch.setenv(var, str(path))
    return mapping


@pytest.fixture
def valid_config(tmp_path):
    """A complete, valid domain config dict. Paths come from env (env_paths)."""
    (tmp_path / "finanzen").mkdir(exist_ok=True)
    return {
        "originals": {"when_filed": "delete", "when_removed": "trash"},
        "summary_mode": "on_conflict",
        "default_pattern": "standard",
        "date_format": "%Y-%m-%d",
        "date_patterns": [],
        "targets": [
            {"name": "Finanzen", "path": str(tmp_path / "finanzen"), "default": False}
        ],
        "patterns": {
            "standard": {"template": "{date}__{sender}_{doctype}_{description}"}
        },
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
