"""API key generation and env secrets (never written to TOML)."""

from __future__ import annotations

import os
import secrets

from pydantic_settings import BaseSettings, SettingsConfigDict

from local_mcp_gateway.errors import ConfigError


class RuntimeSecrets(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="LMG_", extra="ignore")

    api_key: str = ""


def generate_api_key() -> str:
    return secrets.token_urlsafe(32)


def require_api_key() -> str:
    key = RuntimeSecrets().api_key.strip()
    if key:
        return key
    override = os.environ.get("LMG_API_KEY", "").strip()
    if override:
        return override
    raise ConfigError("LMG_API_KEY is required. Generate one with `lmg keygen`.")
