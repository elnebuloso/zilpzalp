from pathlib import Path

from zilpzalp.analyzer import Analysis, DateCandidate
from zilpzalp.config import load_config
from zilpzalp.suggestion import suggest


def _config(tmp_path: Path, extra: str = "") -> "object":
    (tmp_path / "inbox").mkdir(exist_ok=True)
    (tmp_path / "error").mkdir(exist_ok=True)
    cfg = tmp_path / "config.yaml"
    cfg.write_text(
        f"""
paths:
  watchfolder: {tmp_path / "inbox"}
  error_folder: {tmp_path / "error"}
original_handling: keep
summary_mode: never
default_pattern: "{{date}}__{{sender}}_{{doctype}}_{{description}}"
date_format: "%Y-%m-%d"
{extra}
""",
        encoding="utf-8",
    )
    return load_config(cfg)


def test_renders_default_pattern_and_preselects_first_date(tmp_path):
    analysis = Analysis(
        date_candidates=[
            DateCandidate(normalized="2026-01-15", raw="15.01.2026", label="Rechnungsdatum"),
            DateCandidate(normalized="2026-02-01", raw="01.02.2026", label="Faellig am"),
        ],
        sender="Stadtwerke",
        doctype="Rechnung",
        full_text="...",
    )
    s = suggest(analysis, _config(tmp_path))

    assert s.preselected_date_index == 0
    assert s.filename == "2026-01-15__Stadtwerke_Rechnung_.pdf"
    assert len(s.date_candidates) == 2          # §4.3: alle Kandidaten durchgereicht


RULES = """
patterns:
  - name: standard
    template: "{date}__{sender}_{doctype}_{description}"
rules:
  - name: Stromrechnung Stadtwerke
    match:
      sender_contains: "Stadtwerke"
      keywords_any: ["Stromabschlag", "Abschlag"]
    apply:
      sender: "Stadtwerke"
      doctype: "Rechnung"
      description: "Stromabschlag"
      pattern: standard
      preferred_date: faellig
"""


def test_matching_rule_applies_overrides_and_preferred_date(tmp_path):
    analysis = Analysis(
        date_candidates=[
            DateCandidate(normalized="2026-01-15", raw="15.01.2026", label="Rechnungsdatum"),
            DateCandidate(normalized="2026-02-01", raw="01.02.2026", label="Faellig am"),
        ],
        sender="Stadtwerke Musterstadt GmbH",
        doctype=None,
        full_text="... Stromabschlag Januar ...",
    )
    s = suggest(analysis, _config(tmp_path, RULES))

    assert s.description == "Stromabschlag"               # apply-Override
    assert s.preselected_date_index == 1                  # preferred_date "faellig" -> "Faellig am"
    assert s.filename == "2026-02-01__Stadtwerke_Rechnung_Stromabschlag.pdf"


def test_first_matching_rule_wins(tmp_path):
    two_rules = """
rules:
  - name: generisch
    match:
      sender_contains: "Stadtwerke"
    apply:
      doctype: "Allgemein"
  - name: spezifisch
    match:
      sender_contains: "Stadtwerke"
    apply:
      doctype: "Rechnung"
"""
    analysis = Analysis(
        date_candidates=[DateCandidate(normalized="2026-01-15", raw="15.01.2026")],
        sender="Stadtwerke",
        full_text="x",
    )
    s = suggest(analysis, _config(tmp_path, two_rules))
    assert s.doctype == "Allgemein"                       # erste Uebereinstimmung gewinnt
