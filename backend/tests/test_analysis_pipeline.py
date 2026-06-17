from pathlib import Path

from zilpzalp.analyzer import analyze
from zilpzalp.config import load_config
from zilpzalp.document import Block, Document
from zilpzalp.suggestion import suggest


def _config(tmp_path: Path) -> "object":
    (tmp_path / "inbox").mkdir(exist_ok=True)
    (tmp_path / "error").mkdir(exist_ok=True)
    cfg = tmp_path / "config.yaml"
    cfg.write_text(
        f"""
paths:
  watchfolder: {tmp_path / "inbox"}
  error_folder: {tmp_path / "error"}
originals:
  when_filed: delete
  when_removed: trash
summary_mode: never
default_pattern: standard
date_format: "%Y-%m-%d"
patterns:
  standard:
    template: "{{date}}__{{sender}}_{{doctype}}_{{description}}"
rules:
  - name: Stadtwerke
    match:
      sender_contains: "Stadtwerke"
      keywords_any: ["Stromabschlag"]
    apply:
      sender: "Stadtwerke"
      doctype: "Rechnung"
      description: "Stromabschlag"
      preferred_date: rechnungsdatum
""",
        encoding="utf-8",
    )
    return load_config(cfg)


def test_full_analysis_pipeline_invoice(tmp_path):
    doc = Document(blocks=[
        Block(kind="paragraph", text="Stadtwerke Musterstadt GmbH", page=1, bbox=(0, 810, 500, 830)),
        Block(kind="heading", text="Rechnung", page=1, bbox=(0, 770, 200, 790), level=1),
        Block(kind="paragraph", text="Rechnungsdatum: 15.01.2026", page=1, bbox=(0, 720, 500, 740)),
        Block(kind="paragraph", text="Faellig am: 01.02.2026", page=1, bbox=(0, 690, 500, 710)),
        Block(kind="paragraph", text="Stromabschlag Januar", page=1, bbox=(0, 660, 500, 680)),
    ])
    analysis = analyze(doc, _config(tmp_path))
    suggestion = suggest(analysis, _config(tmp_path))

    # §4.3: beide Datumsangaben sichtbar, korrekt gelabelt.
    labels = {c.label: c.normalized for c in analysis.date_candidates}
    assert labels["Rechnungsdatum"] == "2026-01-15"
    assert labels["Faellig am"] == "2026-02-01"
    assert len(analysis.date_candidates) == 2

    # Regel greift -> Vorauswahl Rechnungsdatum, fertiger Name.
    assert suggestion.preselected_date_index == 0
    assert suggestion.filename == "2026-01-15__Stadtwerke_Rechnung_Stromabschlag.pdf"
