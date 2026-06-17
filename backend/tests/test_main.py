import pytest
from fastapi.testclient import TestClient

from zilpzalp.config import ConfigError
from zilpzalp.main import CONFIG_ENV, app


def test_config_available_on_app_state(valid_config, write_config, monkeypatch):
    path = write_config(valid_config)
    monkeypatch.setenv(CONFIG_ENV, str(path))

    with TestClient(app):
        assert app.state.config.originals.when_filed == "delete"


def test_startup_aborts_on_invalid_config(valid_config, write_config, monkeypatch):
    valid_config["originals"]["when_filed"] = "bogus"
    path = write_config(valid_config)
    monkeypatch.setenv(CONFIG_ENV, str(path))

    with pytest.raises(ConfigError):
        with TestClient(app):
            pass


def test_watcher_populates_queue_on_startup(
    valid_config, write_config, monkeypatch, env_paths
):
    # Avoid a real JVM call: stub the extractor used by the worker.
    from zilpzalp import worker as worker_mod
    from zilpzalp.document import Block, Document

    monkeypatch.setattr(
        worker_mod,
        "extract",
        lambda p, c: Document(
            blocks=[Block(kind="paragraph", text="Datum 15.01.2026", page=1, bbox=(0, 0, 0, 0))]
        ),
    )

    watchfolder = env_paths["ZILPZALP_PATH_INBOX"]
    (watchfolder / "incoming.pdf").write_bytes(b"%PDF-1.4")
    path = write_config(valid_config)
    monkeypatch.setenv(CONFIG_ENV, str(path))

    with TestClient(app):
        names = [entry.path.name for entry in app.state.queue.list()]

    assert "incoming.pdf" in names


def test_static_css_is_served(valid_config, write_config, monkeypatch):
    path = write_config(valid_config)
    monkeypatch.setenv(CONFIG_ENV, str(path))

    with TestClient(app) as client:
        response = client.get("/static/styles.css")

    assert response.status_code == 200
    assert "ZilpZalp" in response.text


def test_started_flag_set_during_lifespan(valid_config, write_config, monkeypatch):
    path = write_config(valid_config)
    monkeypatch.setenv(CONFIG_ENV, str(path))

    assert getattr(app.state, "started", False) is False
    with TestClient(app):
        assert app.state.started is True
