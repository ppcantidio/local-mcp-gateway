"""Config file locations and example template."""

from __future__ import annotations

from pathlib import Path

CONFIG_FILENAME = "lmg.toml"
XDG_CONFIG = Path.home() / ".config" / "lmg" / "config.toml"


def default_config_path() -> Path:
    cwd = Path.cwd() / CONFIG_FILENAME
    if cwd.is_file():
        return cwd
    if XDG_CONFIG.is_file():
        return XDG_CONFIG
    return cwd


def resolve_config_path(explicit: Path | None) -> Path | None:
    if explicit is not None:
        return explicit
    cwd = Path.cwd() / CONFIG_FILENAME
    if cwd.is_file():
        return cwd
    if XDG_CONFIG.is_file():
        return XDG_CONFIG
    return None


def example_toml_text() -> str:
    data = Path(__file__).resolve().parents[1] / "data" / "lmg.example.toml"
    if data.is_file():
        return data.read_text(encoding="utf-8")
    root = Path(__file__).resolve().parents[3] / "lmg.example.toml"
    return root.read_text(encoding="utf-8")
