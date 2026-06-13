import pytest
from fastapi.testclient import TestClient

from zilpzalp.config import ConfigError
from zilpzalp.main import CONFIG_ENV, app


def test_health_with_valid_config(valid_config, write_config, monkeypatch):
    path = write_config(valid_config)
    monkeypatch.setenv(CONFIG_ENV, str(path))

    with TestClient(app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_config_available_on_app_state(valid_config, write_config, monkeypatch):
    path = write_config(valid_config)
    monkeypatch.setenv(CONFIG_ENV, str(path))

    with TestClient(app):
        assert app.state.config.original_handling == "move"


def test_startup_aborts_on_invalid_config(valid_config, write_config, monkeypatch):
    valid_config["original_handling"] = "bogus"
    path = write_config(valid_config)
    monkeypatch.setenv(CONFIG_ENV, str(path))

    with pytest.raises(ConfigError):
        with TestClient(app):
            pass
