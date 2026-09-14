"""Publisher protocol. Proxy code never branches on publisher name."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class PublishedEndpoint:
    """Origin the MCP client should use (scheme + host, no path)."""

    url: str

    @property
    def origin(self) -> str:
        return self.url.rstrip("/")

    def mcp_url(self, name: str) -> str:
        return f"{self.origin}/{name}/mcp"


class Publisher(Protocol):
    name: str

    def start(self, *, listen_host: str, listen_port: int) -> PublishedEndpoint: ...

    def stop(self) -> None: ...
