from __future__ import annotations

import tomllib
from pathlib import Path
from typing import Any

import tomli_w
from pydantic import BaseModel, Field


class SettingsConfig(BaseModel):
    default_language: str = "python"
    problems_dir: str = "./leetcode"
    run_mode: str = "local"  # "local" | "remote"


class ApiConfig(BaseModel):
    graphql_endpoint: str = "https://leetcode.com/graphql"
    request_timeout: int = 30
    max_retries: int = 5


class RuntimeConfig(BaseModel):
    python_cmd: str = "python"
    node_cmd: str = "node"
    java_cmd: str = "java"
    javac_cmd: str = "javac"
    cpp_compiler: str = "g++"
    runner_timeout: int = 10


class DisplayConfig(BaseModel):
    show_difficulty: bool = True
    show_tags: bool = False
    syntax_highlight: bool = True


class Config(BaseModel):
    settings: SettingsConfig = Field(default_factory=SettingsConfig)
    api: ApiConfig = Field(default_factory=ApiConfig)
    runtime: RuntimeConfig = Field(default_factory=RuntimeConfig)
    display: DisplayConfig = Field(default_factory=DisplayConfig)


_CONFIG_FILENAME = ".leet2local.toml"
_GLOBAL_CONFIG_DIR = Path.home() / ".config" / "leet2local"
_GLOBAL_CONFIG_PATH = _GLOBAL_CONFIG_DIR / "config.toml"

_config_cache: Config | None = None


def _find_config_path() -> Path | None:
    cwd = Path.cwd()
    for parent in [cwd, *cwd.parents]:
        candidate = parent / _CONFIG_FILENAME
        if candidate.exists():
            return candidate
    if _GLOBAL_CONFIG_PATH.exists():
        return _GLOBAL_CONFIG_PATH
    return None


def load_config() -> Config:
    global _config_cache
    if _config_cache is not None:
        return _config_cache

    path = _find_config_path()
    if path is None:
        _config_cache = Config()
        return _config_cache

    with path.open("rb") as f:
        raw = tomllib.load(f)

    _config_cache = Config.model_validate(raw)
    return _config_cache


def get_config_write_path() -> Path:
    path = _find_config_path()
    if path is not None:
        return path
    return Path.cwd() / _CONFIG_FILENAME


def save_config(config: Config, path: Path | None = None) -> Path:
    global _config_cache
    target = path or get_config_write_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    raw: dict[str, Any] = {
        "settings": config.settings.model_dump(),
        "api": config.api.model_dump(),
        "runtime": config.runtime.model_dump(),
        "display": config.display.model_dump(),
    }
    with target.open("wb") as f:
        tomli_w.dump(raw, f)
    _config_cache = config
    return target


def set_config_value(key: str, value: str) -> None:
    """Set a dotted config key, e.g. 'settings.default_language'."""
    config = load_config()
    raw = config.model_dump()
    parts = key.split(".")
    if len(parts) != 2:
        raise ValueError(f"Key must be in 'section.field' format, got: {key!r}")
    section, field = parts
    if section not in raw:
        raise ValueError(f"Unknown section: {section!r}")
    if field not in raw[section]:
        raise ValueError(f"Unknown field {field!r} in section {section!r}")
    raw[section][field] = value
    updated = Config.model_validate(raw)
    save_config(updated)
    global _config_cache
    _config_cache = updated
