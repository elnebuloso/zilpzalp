import pytest
import yaml

from zilpzalp.config import Config, ConfigError, load_config, save_config


def test_load_valid_config(valid_config, write_config):
    path = write_config(valid_config)

    cfg = load_config(path)

    assert isinstance(cfg, Config)
    assert cfg.original_handling == "move"
    assert cfg.summary_mode == "on_conflict"
    assert cfg.date_format == "%Y-%m-%d"
    assert cfg.paths.watchfolder.name == "inbox"
    assert cfg.targets[0].name == "Finanzen"
    assert cfg.patterns[0].template == "{date}__{sender}_{doctype}_{description}"


def test_missing_file_raises_config_error(tmp_path):
    with pytest.raises(ConfigError, match="kann nicht gelesen werden"):
        load_config(tmp_path / "does-not-exist.yaml")


def test_invalid_yaml_raises_config_error(tmp_path):
    path = tmp_path / "config.yaml"
    path.write_text("paths: [unbalanced\n", encoding="utf-8")

    with pytest.raises(ConfigError, match="kein gültiges YAML"):
        load_config(path)


def test_non_mapping_yaml_raises_config_error(tmp_path):
    path = tmp_path / "config.yaml"
    path.write_text("- just\n- a\n- list\n", encoding="utf-8")

    with pytest.raises(ConfigError, match="YAML-Mapping"):
        load_config(path)


def test_invalid_enum_raises_config_error(valid_config, write_config):
    valid_config["original_handling"] = "bogus"
    path = write_config(valid_config)

    with pytest.raises(ConfigError) as exc:
        load_config(path)
    assert "original_handling" in str(exc.value)


def test_missing_required_field_raises_config_error(valid_config, write_config):
    del valid_config["original_handling"]
    path = write_config(valid_config)

    with pytest.raises(ConfigError) as exc:
        load_config(path)
    assert "original_handling" in str(exc.value)


def test_non_utf8_file_raises_config_error(tmp_path):
    path = tmp_path / "config.yaml"
    path.write_bytes(b"\xff\xfe\x00")

    with pytest.raises(ConfigError, match="kann nicht gelesen werden"):
        load_config(path)


def test_paths_come_from_env_not_yaml(valid_config, write_config, env_paths):
    valid_config["paths"] = {"watchfolder": "/ignored/in/yaml"}  # must be ignored
    path = write_config(valid_config)

    cfg = load_config(path)

    assert cfg.paths.watchfolder == env_paths["ZILPZALP_PATH_INBOX"]
    assert cfg.paths.error_folder == env_paths["ZILPZALP_PATH_ERROR"]
    assert cfg.paths.trash == env_paths["ZILPZALP_PATH_TRASH"]
    assert cfg.paths.cache == env_paths["ZILPZALP_PATH_CACHE"]


def test_paths_use_defaults_when_env_unset(valid_config, write_config, monkeypatch):
    for var in ("INBOX", "ERROR", "TRASH", "CACHE"):
        monkeypatch.delenv(f"ZILPZALP_PATH_{var}", raising=False)
    from pathlib import Path
    from zilpzalp.config import load_paths

    paths = load_paths()
    assert paths.watchfolder == Path("/data/inbox")
    assert paths.trash == Path("/data/trash")


def test_unknown_placeholder_in_default_pattern_raises(valid_config, write_config):
    valid_config["default_pattern"] = "{date}_{unknown}"
    path = write_config(valid_config)

    with pytest.raises(ConfigError, match="unbekannte Platzhalter"):
        load_config(path)


def test_unknown_placeholder_in_pattern_template_raises(valid_config, write_config):
    valid_config["patterns"] = [{"name": "standard", "template": "{date}_{bogus}"}]
    path = write_config(valid_config)

    with pytest.raises(ConfigError, match="bogus"):
        load_config(path)


def test_known_placeholders_are_valid(valid_config, write_config):
    valid_config["default_pattern"] = "{sender}-{doctype}-{description}-{date}"
    path = write_config(valid_config)

    cfg = load_config(path)

    assert cfg.default_pattern == "{sender}-{doctype}-{description}-{date}"


def test_invalid_date_pattern_regex_raises(valid_config, write_config):
    valid_config["date_patterns"] = [{"label": "broken", "regex": "(unbalanced"}]
    path = write_config(valid_config)

    with pytest.raises(ConfigError, match="ungültiger regulärer Ausdruck"):
        load_config(path)


def test_valid_date_pattern_regex_is_accepted(valid_config, write_config):
    valid_config["date_patterns"] = [
        {"label": "leistungsdatum", "regex": r"Leistungsdatum:\s*(\d{2}\.\d{2}\.\d{4})"}
    ]
    path = write_config(valid_config)

    cfg = load_config(path)

    assert cfg.date_patterns[0].label == "leistungsdatum"


def test_missing_date_patterns_block_is_valid(valid_config, write_config):
    del valid_config["date_patterns"]
    path = write_config(valid_config)

    cfg = load_config(path)

    assert cfg.date_patterns == []


def test_date_format_without_directive_raises(valid_config, write_config):
    valid_config["date_format"] = "no-directive-here"
    path = write_config(valid_config)

    with pytest.raises(ConfigError, match="strftime-Direktive"):
        load_config(path)


def test_date_format_with_directive_is_valid(valid_config, write_config):
    valid_config["date_format"] = "%d.%m.%Y"
    path = write_config(valid_config)

    cfg = load_config(path)

    assert cfg.date_format == "%d.%m.%Y"


def test_empty_placeholder_raises_clear_message(valid_config, write_config):
    valid_config["default_pattern"] = "{date}_{}"
    path = write_config(valid_config)

    with pytest.raises(ConfigError, match="leerer Platzhalter"):
        load_config(path)


def test_invalid_summary_mode_raises_config_error(valid_config, write_config):
    valid_config["summary_mode"] = "bogus"
    path = write_config(valid_config)

    with pytest.raises(ConfigError) as exc:
        load_config(path)
    assert "summary_mode" in str(exc.value)


def test_save_config_writes_and_returns_parsed(valid_config, write_config):
    path = write_config(valid_config)
    updated = dict(valid_config)
    updated["summary_mode"] = "always"
    text = yaml.safe_dump(updated, allow_unicode=True)

    config = save_config(path, text)

    assert config.summary_mode == "always"
    assert path.read_text(encoding="utf-8") == text


def test_save_config_rejects_invalid_value_and_keeps_old_file(valid_config, write_config):
    path = write_config(valid_config)
    original = path.read_text(encoding="utf-8")
    bad = dict(valid_config)
    bad["original_handling"] = "bogus"

    with pytest.raises(ConfigError):
        save_config(path, yaml.safe_dump(bad, allow_unicode=True))

    assert path.read_text(encoding="utf-8") == original


def test_save_config_rejects_invalid_yaml_and_keeps_old_file(valid_config, write_config):
    path = write_config(valid_config)
    original = path.read_text(encoding="utf-8")

    with pytest.raises(ConfigError):
        save_config(path, "paths: [this is not: valid yaml")

    assert path.read_text(encoding="utf-8") == original
