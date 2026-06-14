from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from zilpzalp.analyzer import DateCandidate
from zilpzalp.main import CONFIG_ENV, app
from zilpzalp.suggestion import Suggestion


@pytest.fixture
def client(valid_config, write_config, monkeypatch):
    monkeypatch.setenv(CONFIG_ENV, str(write_config(valid_config)))
    with TestClient(app) as client:
        yield client


def _ready_suggestion(target_path):
    return Suggestion(
        filename="2026-01-15__Stadtwerke_Rechnung_.pdf",
        date_candidates=[
            DateCandidate(normalized="2026-01-15", raw="15.01.2026",
                          label="Rechnungsdatum", snippet="Rechnungsdatum: 15.01.2026"),
            DateCandidate(normalized="2026-02-01", raw="01.02.2026",
                          label="fällig am", snippet="fällig am 01.02.2026"),
        ],
        preselected_date_index=0,
        sender="Stadtwerke",
        doctype="Rechnung",
        description="Strom",
        pattern_name="standard",
        target_paths=[Path(target_path)],
    )


def _add_ready(client, name="rechnung.pdf"):
    cfg = app.state.config
    pdf = Path(cfg.paths.watchfolder) / name
    pdf.write_bytes(b"%PDF-1.4")
    app.state.queue.add(pdf)
    app.state.queue.set_ready(pdf, _ready_suggestion(cfg.targets[0].path))
    return app.state.queue.get(pdf)


def test_overview_renders_counters_and_betriebsangaben(client):
    _add_ready(client)
    response = client.get("/")
    assert response.status_code == 200
    body = response.text
    assert "Übersicht" in body
    assert "Betriebsangaben" in body
    assert "rechnung.pdf" in body
    assert "bereit" in body


def test_overview_partial_returns_fragment(client):
    response = client.get("/partials/overview")
    assert response.status_code == 200
    assert "<html" not in response.text.lower()
    assert "counters" in response.text


def test_overview_empty_state(client):
    response = client.get("/")
    assert "Die Warteschlange ist leer" in response.text


def test_queue_page_lists_ready_document(client):
    _add_ready(client, "rechnung.pdf")
    response = client.get("/queue")
    assert response.status_code == 200
    body = response.text
    assert "Warteschlange" in body
    assert "rechnung.pdf" in body
    assert "Prüfen" in body


def test_queue_partial_returns_fragment(client):
    _add_ready(client, "rechnung.pdf")
    response = client.get("/partials/queue")
    assert response.status_code == 200
    assert "<html" not in response.text.lower()
    assert "rechnung.pdf" in response.text


def test_queue_empty_state(client):
    response = client.get("/queue")
    assert "Keine Dokumente in der Warteschlange" in response.text


def test_review_renders_all_date_candidates_and_fields(client):
    entry = _add_ready(client, "rechnung.pdf")
    response = client.get(f"/review/{entry.id}")
    assert response.status_code == 200
    body = response.text
    assert "Dokument prüfen" in body
    assert "Rechnungsdatum" in body
    assert "fällig am" in body          # all candidates shown, none dropped (§4.3)
    assert 'name="sender"' in body
    assert "Datum manuell eingeben" in body
    assert "Finanzen" in body           # target folder chip from config


def test_review_redirects_when_not_ready(client):
    cfg = app.state.config
    pdf = Path(cfg.paths.watchfolder) / "pending.pdf"
    pdf.write_bytes(b"%PDF-1.4")
    app.state.queue.add(pdf)            # status pending
    entry = app.state.queue.get(pdf)

    response = client.get(f"/review/{entry.id}", follow_redirects=False)
    assert response.status_code in (302, 303, 307)
    assert response.headers["location"] == "/queue"


def test_review_unknown_id_redirects(client):
    response = client.get("/review/deadbeef", follow_redirects=False)
    assert response.status_code in (302, 303, 307)
    assert response.headers["location"] == "/queue"
