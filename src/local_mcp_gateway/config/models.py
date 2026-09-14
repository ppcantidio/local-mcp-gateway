"""Config models: gateway TOML shape."""

from __future__ import annotations

import re
from typing import Self
from urllib.parse import urlsplit, urlunsplit

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from local_mcp_gateway.errors import ConfigError

RESERVED_NAMES = frozenset({"healthz"})
NAME_RE = re.compile(r"^[a-z][a-z0-9-]{0,62}$")


def parse_listen(listen: str) -> tuple[str, int]:
    value = listen.strip()
    if value.startswith("["):
        host, port_s = value.rsplit("]:", 1)
        return host[1:], int(port_s)
    if ":" not in value:
        raise ValueError("listen must be host:port")
    host, port_s = value.rsplit(":", 1)
    return host, int(port_s)


class AuthConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    header: str = "authorization"
    prefix: str = "Bearer "


class PublisherConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = "local"
    mode: str | None = None


class ProxyConfig(BaseModel):
    """Tunables for Cloud Agent + tunnel reliability."""

    model_config = ConfigDict(extra="forbid")

    # None = leave GET SSE enabled (Cursor Cloud discovery needs it).
    # Set true only if you want POST-only Streamable HTTP.
    disable_get_sse: bool | None = None
    sse_heartbeat_seconds: float = 15.0
    upstream_retries: int = 2

    @field_validator("sse_heartbeat_seconds")
    @classmethod
    def validate_heartbeat(cls, value: float) -> float:
        if value < 0:
            raise ValueError("sse_heartbeat_seconds must be >= 0 (0 disables heartbeats)")
        return value

    @field_validator("upstream_retries")
    @classmethod
    def validate_retries(cls, value: int) -> int:
        if value < 0 or value > 5:
            raise ValueError("upstream_retries must be between 0 and 5")
        return value


class McpServer(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    url: str
    rewrite_host: str | None = None

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        name = value.strip()
        if name in RESERVED_NAMES:
            raise ValueError(f"{name!r} is a reserved path and cannot be used as an MCP name")
        if not NAME_RE.match(name):
            raise ValueError(
                "MCP name must be a lowercase slug "
                "(start with a letter, then letters/digits/hyphens)"
            )
        return name

    @field_validator("url")
    @classmethod
    def validate_url(cls, value: str) -> str:
        parts = urlsplit(value.strip())
        if parts.scheme not in {"http", "https"} or not parts.netloc:
            raise ValueError("url must be an absolute http(s) URL with a host")
        return value.strip()

    @field_validator("rewrite_host")
    @classmethod
    def validate_rewrite_host(cls, value: str | None) -> str | None:
        if value is None:
            return None
        host = value.strip()
        if not host or "://" in host or "/" in host:
            raise ValueError("rewrite_host must be a Host header value like 127.0.0.1:29979")
        return host

    @property
    def origin(self) -> str:
        parts = urlsplit(self.url)
        return urlunsplit((parts.scheme, parts.netloc, "", "", ""))

    @property
    def host_header(self) -> str:
        if self.rewrite_host:
            return self.rewrite_host
        return urlsplit(self.url).netloc


class GatewayConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    listen: str = "127.0.0.1:8788"
    auth: AuthConfig = Field(default_factory=AuthConfig)
    publisher: PublisherConfig = Field(default_factory=PublisherConfig)
    proxy: ProxyConfig = Field(default_factory=ProxyConfig)
    mcp: list[McpServer] = Field(default_factory=list)

    @field_validator("listen")
    @classmethod
    def validate_listen(cls, value: str) -> str:
        parse_listen(value)
        return value

    @model_validator(mode="after")
    def unique_names(self) -> Self:
        names = [item.name for item in self.mcp]
        dupes = {name for name in names if names.count(name) > 1}
        if dupes:
            raise ValueError(f"duplicate MCP names: {', '.join(sorted(dupes))}")
        return self

    def get_sse_disabled(self) -> bool:
        # Default False: Cursor Cloud MCP discovery opens GET SSE and treats
        # 405 / empty tools as a hard discovery failure. Funnel idle flaps are
        # mitigated by sse_heartbeat_seconds instead.
        if self.proxy.disable_get_sse is not None:
            return self.proxy.disable_get_sse
        return False

    def server(self, name: str) -> McpServer:
        for item in self.mcp:
            if item.name == name:
                return item
        raise ConfigError(f"unknown MCP {name!r}")

    def upsert(self, server: McpServer) -> None:
        self.mcp = [item for item in self.mcp if item.name != server.name] + [server]

    def remove(self, name: str) -> None:
        before = len(self.mcp)
        self.mcp = [item for item in self.mcp if item.name != name]
        if len(self.mcp) == before:
            raise ConfigError(f"unknown MCP {name!r}")

    def filtered(self, only: list[str] | None) -> GatewayConfig:
        if not only:
            return self
        wanted = list(only)
        missing = [name for name in wanted if all(item.name != name for item in self.mcp)]
        if missing:
            raise ConfigError(f"unknown MCP name(s): {', '.join(missing)}")
        clone = self.model_copy(deep=True)
        clone.mcp = [item for item in self.mcp if item.name in wanted]
        return clone
