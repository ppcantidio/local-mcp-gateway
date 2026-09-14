"""CLI option → config merge helpers."""

from __future__ import annotations

from local_mcp_gateway.config.models import GatewayConfig, McpServer, parse_listen
from local_mcp_gateway.errors import ConfigError


def parse_mcp_option(value: str) -> McpServer:
    if "=" not in value:
        raise ConfigError("--mcp must be name=url")
    name, url = value.split("=", 1)
    try:
        return McpServer(name=name.strip(), url=url.strip())
    except Exception as exc:
        raise ConfigError(str(exc)) from exc


def merge_serve_options(
    config: GatewayConfig,
    *,
    publisher: str | None,
    mode: str | None,
    listen: str | None,
    mcp: list[str] | None,
    only: list[str] | None,
) -> GatewayConfig:
    merged = config.model_copy(deep=True)
    if listen:
        try:
            parse_listen(listen)
        except ValueError as exc:
            raise ConfigError(str(exc)) from exc
        merged.listen = listen
    if publisher:
        merged.publisher.name = publisher
    if mode:
        merged.publisher.mode = mode
    for raw in mcp or []:
        merged.upsert(parse_mcp_option(raw))
    return merged.filtered(only)
