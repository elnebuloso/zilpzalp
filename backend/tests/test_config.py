import pytest

from zilpzalp.config import Config, ConfigError, load_config


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
    del valid_config["paths"]
    path = write_config(valid_config)

    with pytest.raises(ConfigError) as exc:
        load_config(path)
    assert "paths" in str(exc.value)


def test_non_utf8_file_raises_config_error(tmp_path):
    path = tmp_path / "config.yaml"
    path.write_bytes(b"\xff\xfe\x00")

    with pytest.raises(ConfigError, match="kann nicht gelesen werden"):
        load_config(path)
