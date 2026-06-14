from fastapi.testclient import TestClient

from zilpzalp.main import CONFIG_ENV, app


def _client(valid_config, write_config, monkeypatch):
    path = write_config(valid_config)
    monkeypatch.setenv(CONFIG_ENV, str(path))
    return TestClient(app)


def test_all_probes_ok_when_healthy(valid_config, write_config, monkeypatch):
    with _client(valid_config, write_config, monkeypatch) as client:
        for route in ("/healthz/startup", "/healthz/ready", "/healthz/live"):
            response = client.get(route)
            assert response.status_code == 200, route
            assert response.json() == {"status": "ok"}, route


def test_ready_and_live_fail_when_worker_dead(
    valid_config, write_config, monkeypatch
):
    with _client(valid_config, write_config, monkeypatch) as client:
        monkeypatch.setattr(app.state.worker, "is_alive", lambda: False)

        assert client.get("/healthz/startup").status_code == 200
        for route in ("/healthz/ready", "/healthz/live"):
            response = client.get(route)
            assert response.status_code == 503, route
            assert response.json()["status"] == "unavailable", route
            assert response.json()["checks"]["worker"] is False, route


def test_ready_and_live_fail_when_watcher_dead(
    valid_config, write_config, monkeypatch
):
    with _client(valid_config, write_config, monkeypatch) as client:
        monkeypatch.setattr(app.state.watcher, "is_alive", lambda: False)

        assert client.get("/healthz/startup").status_code == 200
        for route in ("/healthz/ready", "/healthz/live"):
            response = client.get(route)
            assert response.status_code == 503, route
            assert response.json()["checks"]["watcher"] is False, route
