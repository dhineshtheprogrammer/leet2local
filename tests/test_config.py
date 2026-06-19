from leet2local.config import Config, load_config, save_config, set_config_value


def test_default_config():
    cfg = Config()
    assert cfg.settings.default_language == "python"
    assert cfg.settings.run_mode == "local"
    assert cfg.api.max_retries == 5


def test_save_and_load(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    # Patch cache
    import leet2local.config as cfg_mod
    cfg_mod._config_cache = None

    cfg = Config()
    save_config(cfg, tmp_path / ".leet2local.toml")

    cfg_mod._config_cache = None
    loaded = load_config()
    assert loaded.settings.default_language == cfg.settings.default_language


def test_set_config_value(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    import leet2local.config as cfg_mod
    cfg_mod._config_cache = None

    cfg = Config()
    save_config(cfg, tmp_path / ".leet2local.toml")
    cfg_mod._config_cache = None

    set_config_value("settings.default_language", "javascript")
    cfg_mod._config_cache = None
    loaded = load_config()
    assert loaded.settings.default_language == "javascript"
