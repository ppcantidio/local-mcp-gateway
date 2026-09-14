"""Load and persist gateway TOML config."""

from __future__ import annotations

import tomllib
from pathlib import Path

from local_mcp_gateway.config.models import GatewayConfig
from local_mcp_gateway.errors import ConfigError


def load_config(path: Path) -> GatewayConfig:
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ConfigError(f"config not found: {path}") from exc
    except tomllib.TOMLDecodeError as exc:
        raise ConfigError(f"invalid TOML in {path}: {exc}") from exc
    try:
        return GatewayConfig.model_validate(data)
    except Exception as exc:
        raise ConfigError(f"invalid config {path}: {exc}") from exc


def dumps_config(config: GatewayConfig) -> str:
    lines = [
        f"listen = {_toml_str(config.listen)}",
        "",
        "[auth]",
        f"header = {_toml_str(config.auth.header)}",
        f"prefix = {_toml_str(config.auth.prefix)}",
        "",
        "[publisher]",
        f"name = {_toml_str(config.publisher.name)}",
    ]
    if config.publisher.mode:
        lines.append(f"mode = {_toml_str(config.publisher.mode)}")
    for item in config.mcp:
        lines.extend(
            [
                "",
                "[[mcp]]",
                f"name = {_toml_str(item.name)}",
                f"url = {_toml_str(item.url)}",
            ]
        )
        if item.rewrite_host:
            lines.append(f"rewrite_host = {_toml_str(item.rewrite_host)}")
    return "\n".join(lines) + "\n"


def save_config(path: Path, config: GatewayConfig) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(dumps_config(config), encoding="utf-8")


def _toml_str(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'
