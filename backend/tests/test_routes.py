import os
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
    # Add to queue before writing so the watcher's worker.submit() sees
    # queue.add() return False and does not enqueue the file for re-processing.
    app.state.queue.add(pdf)
    app.state.queue.set_ready(pdf, _ready_suggestion(cfg.targets[0].path))
    pdf.write_bytes(b"%PDF-1.4")
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


def _form(target_path, **overrides):
    data = {
        "date_kind": "candidate",
        "date_value": "2026-01-15",
        "sender": "Stadtwerke",
        "doctype": "Rechnung",
        "description": "Strom",
        "pattern": "standard",
        "targets": [str(target_path)],
    }
    data.update(overrides)
    return data


def test_confirm_executes_directly_when_summary_never(client):
    cfg = app.state.config
    cfg.__dict__["summary_mode"] = "never"  # in-memory override for this test
    entry = _add_ready(client, "rechnung.pdf")

    response = client.post(
        f"/documents/{entry.id}/confirm",
        data=_form(cfg.targets[0].path),
    )

    assert response.status_code == 200
    assert response.headers.get("HX-Redirect", "").startswith("/queue")
    # document left the queue and a copy landed in the target
    assert app.state.queue.get_by_id(entry.id) is None
    target = Path(cfg.targets[0].path)
    assert any(target.iterdir())


def test_confirm_shows_summary_when_always(client):
    cfg = app.state.config
    cfg.__dict__["summary_mode"] = "always"
    entry = _add_ready(client, "rechnung.pdf")

    response = client.post(
        f"/documents/{entry.id}/confirm",
        data=_form(cfg.targets[0].path),
    )

    assert response.status_code == 200
    assert "Zusammenfassung" in response.text
    assert "Ausführen" in response.text
    # nothing executed yet
    assert app.state.queue.get_by_id(entry.id) is not None


def test_execute_with_conflict_locks_summary(client):
    cfg = app.state.config
    cfg.__dict__["summary_mode"] = "never"
    entry = _add_ready(client, "rechnung.pdf")
    target = Path(cfg.targets[0].path)
    # pre-create the conflicting destination
    (target / "2026-01-15__Stadtwerke_Rechnung_Strom.pdf").write_bytes(b"x")

    response = client.post(
        f"/documents/{entry.id}/confirm",
        data=_form(target),
    )

    assert response.status_code == 200
    assert "Namenskonflikt" in response.text
    # execution blocked, doc stays in queue
    assert app.state.queue.get_by_id(entry.id) is not None


def test_config_page_shows_current_yaml(client):
    response = client.get("/config")
    assert response.status_code == 200
    assert "Konfiguration" in response.text
    assert "original_handling" in response.text    # current file content shown


def test_config_save_valid_updates_state(client):
    import yaml as _yaml

    cfg_path = Path(app.state.config_path)
    new = _yaml.safe_load(cfg_path.read_text(encoding="utf-8"))
    new["summary_mode"] = "always"
    text = _yaml.safe_dump(new, allow_unicode=True)

    response = client.post("/config", data={"text": text})

    assert response.status_code == 200
    assert "gespeichert" in response.text.lower()
    assert app.state.config.summary_mode == "always"


def test_config_save_invalid_shows_errors_and_keeps_config(client):
    before = app.state.config.summary_mode
    response = client.post("/config", data={"text": "original_handling: bogus"})

    assert response.status_code == 200
    assert "nicht übernommen" in response.text
    assert app.state.config.summary_mode == before


def test_language_cookie_switches_nav_to_english(client):
    response = client.get("/", cookies={"lang": "en"})
    assert response.status_code == 200
    body = response.text
    assert "Overview" in body
    assert "Operational details" in body
    assert 'lang="en"' in body


def test_default_language_is_german(client):
    response = client.get("/")
    assert "Übersicht" in response.text
    assert 'lang="de"' in response.text


def test_set_language_sets_cookie_and_redirects(client):
    response = client.get("/lang/en?next=/queue", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/queue"
    assert "lang=en" in response.headers.get("set-cookie", "")


def test_set_language_rejects_unknown_code(client):
    response = client.get("/lang/fr", follow_redirects=False)
    assert response.status_code == 303
    assert "lang=" not in response.headers.get("set-cookie", "")


def test_set_language_ignores_external_next(client):
    response = client.get("/lang/en?next=https://evil.test", follow_redirects=False)
    assert response.headers["location"] == "/"


def test_set_language_rejects_protocol_relative_next(client):
    for evil in ("//evil.com", "/\\evil.com"):
        response = client.get("/lang/en", params={"next": evil}, follow_redirects=False)
        assert response.status_code == 303
        assert response.headers["location"] == "/", evil


def test_candidate_date_uses_config_date_format(client):
    cfg = app.state.config
    cfg.__dict__["summary_mode"] = "never"
    cfg.__dict__["date_format"] = "%d.%m.%Y"  # in-memory override for this test
    entry = _add_ready(client, "rechnung.pdf")

    response = client.post(
        f"/documents/{entry.id}/confirm",
        data=_form(cfg.targets[0].path, date_kind="candidate", date_value="2026-01-15"),
    )

    assert response.status_code == 200
    assert response.headers.get("HX-Redirect", "").startswith("/queue")
    target = Path(cfg.targets[0].path)
    names = [p.name for p in target.iterdir()]
    # Candidate date now formatted via config.date_format (15.01.2026), not raw ISO.
    assert any(name.startswith("15.01.2026") for name in names), names


def test_confirm_uses_manually_entered_date(client):
    cfg = app.state.config
    cfg.__dict__["summary_mode"] = "never"  # in-memory override for this test
    entry = _add_ready(client, "manual.pdf")

    response = client.post(
        f"/documents/{entry.id}/confirm",
        data=_form(cfg.targets[0].path, date_kind="manual", date_value="2020-07-09"),
    )

    assert response.status_code == 200
    target = Path(cfg.targets[0].path)
    assert any(f.name.startswith("2020-07-09") for f in target.iterdir())


def test_flash_message_is_localized_to_english(client):
    cfg = app.state.config
    cfg.__dict__["summary_mode"] = "never"
    entry = _add_ready(client, "rechnung.pdf")

    response = client.post(
        f"/documents/{entry.id}/confirm",
        data=_form(cfg.targets[0].path),
        cookies={"lang": "en"},
    )

    assert response.status_code == 200
    redirect = response.headers.get("HX-Redirect", "")
    assert "has+been+filed" in redirect or "has%20been%20filed" in redirect


def test_summary_modal_is_localized_to_english(client):
    cfg = app.state.config
    cfg.__dict__["summary_mode"] = "always"
    entry = _add_ready(client, "rechnung.pdf")

    response = client.post(
        f"/documents/{entry.id}/confirm",
        data=_form(cfg.targets[0].path),
        cookies={"lang": "en"},
    )

    assert response.status_code == 200
    assert "Summary" in response.text
    assert "Execute" in response.text


def test_review_renders_localized_file_date_label(client):
    cfg = app.state.config
    pdf = Path(cfg.paths.watchfolder) / "fallback.pdf"
    app.state.queue.add(pdf)
    app.state.queue.set_ready(pdf, Suggestion(
        filename="2020-07-09__Unbekannt_Dokument_.pdf",
        date_candidates=[
            DateCandidate(normalized="2020-07-09", raw="", label_key="file_modified"),
        ],
        preselected_date_index=0,
        sender="",
        doctype="",
        description="",
        pattern_name="standard",
        target_paths=[Path(cfg.targets[0].path)],
    ))
    pdf.write_bytes(b"%PDF-1.4")
    entry = app.state.queue.get(pdf)

    response = client.get(f"/review/{entry.id}")

    assert response.status_code == 200
    assert "Datei geändert" in response.text  # de default locale


def _upload(client, filename, content):
    return client.post(
        "/upload",
        files={"file": (filename, content, "application/pdf")},
    )


def test_upload_valid_pdf_lands_in_watchfolder(client):
    cfg = app.state.config
    resp = _upload(client, "rechnung.pdf", b"%PDF-1.4 hello")
    assert resp.status_code == 200
    assert resp.json()["filename"] == "rechnung.pdf"
    landed = Path(cfg.paths.watchfolder) / "rechnung.pdf"
    assert landed.exists()
    assert landed.read_bytes() == b"%PDF-1.4 hello"


def test_upload_rejects_non_pdf_extension(client):
    cfg = app.state.config
    resp = _upload(client, "notes.txt", b"%PDF-1.4 hello")
    assert resp.status_code == 400
    assert not (Path(cfg.paths.watchfolder) / "notes.txt").exists()


def test_upload_rejects_bad_magic_bytes(client):
    cfg = app.state.config
    resp = _upload(client, "fake.pdf", b"NOT A PDF")
    assert resp.status_code == 400
    assert not (Path(cfg.paths.watchfolder) / "fake.pdf").exists()


def test_upload_name_conflict_gets_suffix(client):
    cfg = app.state.config
    existing = Path(cfg.paths.watchfolder) / "rechnung.pdf"
    existing.write_bytes(b"%PDF-1.4 original")
    resp = _upload(client, "rechnung.pdf", b"%PDF-1.4 second")
    assert resp.status_code == 200
    assert resp.json()["filename"] == "rechnung (1).pdf"
    assert existing.read_bytes() == b"%PDF-1.4 original"
    assert (Path(cfg.paths.watchfolder) / "rechnung (1).pdf").exists()


def test_upload_strips_path_components(client):
    cfg = app.state.config
    resp = _upload(client, "../evil.pdf", b"%PDF-1.4 x")
    assert resp.status_code == 200
    assert resp.json()["filename"] == "evil.pdf"
    assert (Path(cfg.paths.watchfolder) / "evil.pdf").exists()


def test_upload_leaves_no_part_file(client):
    cfg = app.state.config
    resp = _upload(client, "rechnung.pdf", b"%PDF-1.4 hello")
    assert resp.status_code == 200
    leftovers = list(Path(cfg.paths.watchfolder).glob(".upload-*"))
    assert leftovers == []


def test_upload_rejects_empty_stem_name(client):
    cfg = app.state.config
    resp = _upload(client, ".pdf", b"%PDF-1.4 x")
    assert resp.status_code == 400
    assert not (Path(cfg.paths.watchfolder) / ".pdf").exists()


def test_overview_shows_upload_zone(client):
    response = client.get("/")
    assert response.status_code == 200
    body = response.text
    assert 'id="upload-zone"' in body
    assert 'id="upload-input"' in body
    assert "PDF" in body


def test_skip_deletes_file_and_removes_entry_and_cache(client):
    cfg = app.state.config
    entry = _add_ready(client, "skipme.pdf")
    Path(cfg.paths.cache).joinpath("skipme.json").write_text("{}", encoding="utf-8")

    response = client.post(f"/documents/{entry.id}/skip", follow_redirects=False)

    assert response.status_code == 200
    assert response.headers.get("HX-Redirect", "").startswith("/queue")
    assert app.state.queue.get_by_id(entry.id) is None
    assert not (Path(cfg.paths.watchfolder) / "skipme.pdf").exists()
    assert not Path(cfg.paths.cache).joinpath("skipme.json").exists()


def test_skip_unknown_entry_redirects(client):
    response = client.post("/documents/deadbeef/skip", follow_redirects=False)
    assert response.status_code == 200
    assert response.headers.get("HX-Redirect") == "/queue"


def test_queue_list_shows_skip_button(client):
    _add_ready(client, "rechnung.pdf")
    body = client.get("/partials/queue").text
    assert "/skip" in body
    assert "Überspringen" in body


def test_config_save_triggers_reanalysis(client, monkeypatch):
    import yaml as _yaml

    called = {"n": 0}
    monkeypatch.setattr(app.state.worker, "reanalyze_all", lambda: called.__setitem__("n", called["n"] + 1))

    cfg_path = Path(app.state.config_path)
    new = _yaml.safe_load(cfg_path.read_text(encoding="utf-8"))
    new["summary_mode"] = "always"
    client.post("/config", data={"text": _yaml.safe_dump(new, allow_unicode=True)})

    assert called["n"] == 1


def test_queue_lists_newest_first(client):
    old = _add_ready(client, "old.pdf")
    new = _add_ready(client, "new.pdf")
    os.utime(old.path, (1000, 1000))
    os.utime(new.path, (2000, 2000))
    body = client.get("/partials/queue").text
    assert body.index("new.pdf") < body.index("old.pdf")


def test_overview_recent_newest_first(client):
    old = _add_ready(client, "old.pdf")
    new = _add_ready(client, "new.pdf")
    os.utime(old.path, (1000, 1000))
    os.utime(new.path, (2000, 2000))
    body = client.get("/partials/overview").text
    assert body.index("new.pdf") < body.index("old.pdf")


def test_queue_survives_missing_file(client):
    entry = _add_ready(client, "gone.pdf")
    entry.path.unlink()
    response = client.get("/partials/queue")
    assert response.status_code == 200


def test_overview_recent_shows_ready_badge(client):
    _add_ready(client, "rechnung.pdf")
    body = client.get("/partials/overview").text
    assert "b-ready" in body
    assert "/review/" in body


def test_document_pdf_served_inline(client):
    entry = _add_ready(client, "rechnung.pdf")
    response = client.get(f"/documents/{entry.id}/pdf")
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert "inline" in response.headers.get("content-disposition", "")
    assert response.content.startswith(b"%PDF")


def test_document_pdf_unknown_id_404(client):
    response = client.get("/documents/deadbeef/pdf")
    assert response.status_code == 404


def test_extract_markdown_returns_pre(client):
    cfg = app.state.config
    entry = _add_ready(client, "rechnung.pdf")
    Path(cfg.paths.cache).joinpath("rechnung.md").write_text("# Hallo", encoding="utf-8")

    response = client.get(f"/documents/{entry.id}/extract/markdown")
    assert response.status_code == 200
    assert "<pre" in response.text
    assert "# Hallo" in response.text


def test_extract_html_returns_sandboxed_iframe(client):
    cfg = app.state.config
    entry = _add_ready(client, "rechnung.pdf")
    Path(cfg.paths.cache).joinpath("rechnung.html").write_text("<h1>Hi</h1>", encoding="utf-8")

    response = client.get(f"/documents/{entry.id}/extract/html")
    assert response.status_code == 200
    assert "<iframe" in response.text
    assert "sandbox" in response.text
    assert "srcdoc" in response.text
    assert "allow-scripts" not in response.text


def test_extract_json_is_pretty_printed(client):
    cfg = app.state.config
    entry = _add_ready(client, "rechnung.pdf")
    Path(cfg.paths.cache).joinpath("rechnung.json").write_text('{"a":1,"b":2}', encoding="utf-8")

    response = client.get(f"/documents/{entry.id}/extract/json")
    assert response.status_code == 200
    assert '&#34;a&#34;: 1' in response.text  # indented, space after colon, with HTML escaping


def test_extract_missing_file_shows_unavailable(client):
    entry = _add_ready(client, "rechnung.pdf")
    response = client.get(f"/documents/{entry.id}/extract/markdown")
    assert response.status_code == 200
    assert "Nicht verfügbar" in response.text


def test_extract_unknown_kind_404(client):
    entry = _add_ready(client, "rechnung.pdf")
    response = client.get(f"/documents/{entry.id}/extract/bogus")
    assert response.status_code == 404


def test_confirm_advances_to_next_ready_document(client):
    cfg = app.state.config
    cfg.__dict__["summary_mode"] = "never"
    first = _add_ready(client, "first.pdf")
    second = _add_ready(client, "second.pdf")

    response = client.post(
        f"/documents/{first.id}/confirm",
        data=_form(cfg.targets[0].path),
    )

    assert response.status_code == 200
    redirect = response.headers.get("HX-Redirect", "")
    assert redirect.startswith(f"/review/{second.id}")
    assert "flash=" in redirect


def test_confirm_returns_to_queue_when_no_more_ready(client):
    cfg = app.state.config
    cfg.__dict__["summary_mode"] = "never"
    only = _add_ready(client, "only.pdf")

    response = client.post(
        f"/documents/{only.id}/confirm",
        data=_form(cfg.targets[0].path),
    )

    assert response.headers.get("HX-Redirect", "").startswith("/queue")


def test_skip_advances_to_next_ready_document(client):
    first = _add_ready(client, "first.pdf")
    second = _add_ready(client, "second.pdf")

    response = client.post(f"/documents/{first.id}/skip", follow_redirects=False)

    redirect = response.headers.get("HX-Redirect", "")
    assert redirect.startswith(f"/review/{second.id}")


def test_review_has_no_preselected_date(client):
    entry = _add_ready(client, "rechnung.pdf")
    response = client.get(f"/review/{entry.id}")
    assert response.status_code == 200
    body = response.text
    assert "date-opt sel" not in body          # no candidate preselected
    assert 'data-selected-date=""' in body     # hidden value starts empty
