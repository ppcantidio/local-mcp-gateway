"""Map /{name}/… request paths onto registered MCP upstreams."""

from __future__ import annotations

from local_mcp_gateway.config import McpServer


def match_mcp(path: str, servers: list[McpServer]) -> tuple[McpServer, str] | None:
    stripped = path.lstrip("/")
    if not stripped:
        return None
    name, _, remainder = stripped.partition("/")
    for server in servers:
        if server.name == name:
            rest = f"/{remainder}" if remainder else "/"
            return server, rest
    return None
