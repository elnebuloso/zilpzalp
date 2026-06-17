import json
from pathlib import Path

from zilpzalp.web import i18n
from zilpzalp.web.i18n import translate

LOCALES = Path(i18n.__file__).parent / "locales"


def test_translate_returns_language_string():
    assert i18n.translate("nav.overview", "de") == "Übersicht"
    assert i18n.translate("nav.overview", "en") == "Overview"


def test_translate_falls_back_to_default_language():
    # An unknown language resolves nothing; default (de) is used.
    assert i18n.translate("nav.overview", "fr") == "Übersicht"


def test_translate_unknown_key_returns_key():
    assert i18n.translate("does.not.exist", "de") == "does.not.exist"


def test_translate_interpolates_vars():
    out = i18n.translate("toast.filed", "de", filename="x.pdf")
    assert "x.pdf" in out


def test_resolve_language_prefers_cookie():
    req = _fake_request(cookies={"lang": "en"}, accept="de")
    assert i18n.resolve_language(req) == "en"


def test_resolve_language_uses_accept_language_when_no_cookie():
    req = _fake_request(cookies={}, accept="en-US,en;q=0.9,de;q=0.8")
    assert i18n.resolve_language(req) == "en"


def test_resolve_language_falls_back_to_default():
    req = _fake_request(cookies={}, accept="fr-FR,fr;q=0.9")
    assert i18n.resolve_language(req) == "de"


def test_resolve_language_ignores_unsupported_cookie():
    req = _fake_request(cookies={"lang": "fr"}, accept="en")
    assert i18n.resolve_language(req) == "en"


def test_catalogs_have_identical_keys():
    de = json.loads((LOCALES / "de.json").read_text(encoding="utf-8"))
    en = json.loads((LOCALES / "en.json").read_text(encoding="utf-8"))
    assert set(de) == set(en), (
        f"only de: {set(de) - set(en)} | only en: {set(en) - set(de)}"
    )


class _FakeURL:
    def __init__(self, path="/"):
        self.path = path


class _FakeRequest:
    def __init__(self, cookies, headers):
        self.cookies = cookies
        self.headers = headers
        self.url = _FakeURL()


def _fake_request(cookies, accept):
    return _FakeRequest(cookies, {"accept-language": accept})


def test_upload_done_label_uploaded():
    assert translate("upload.status.done", "de") == "hochgeladen"
    assert translate("upload.status.done", "en") == "uploaded"
