"""Orchestrate proxy + publisher lifecycle."""

from __future__ import annotations

import asyncio
import logging

import uvicorn
from rich.console import Console
from rich.table import Table

from local_mcp_gateway import __version__
from local_mcp_gateway.config import GatewayConfig, parse_listen
from local_mcp_gateway.proxy import SERVICE_NAME, create_app
from local_mcp_gateway.publishers.base import PublishedEndpoint, Publisher

log = logging.getLogger("local_mcp_gateway")


async def _wait_until_started(server: uvicorn.Server, serve_task: asyncio.Task[None]) -> None:
    while not server.started:
        if serve_task.done():
            await serve_task
            raise RuntimeError("proxy failed to start")
        await asyncio.sleep(0.05)


def print_ready(console: Console, endpoint: PublishedEndpoint, config: GatewayConfig) -> None:
    origin = endpoint.origin
    console.print(f"[bold]{SERVICE_NAME}[/bold] {__version__}")
    console.print(f"public origin  {origin}")
    table = Table(show_header=True, header_style="bold", box=None, pad_edge=False)
    table.add_column("mcp")
    table.add_column("url")
    for item in config.mcp:
        table.add_row(item.name, endpoint.mcp_url(item.name))
    console.print(table)
    console.print("Leave this process running. Laptop asleep = MCP down.")


async def run_gateway(
    config: GatewayConfig,
    *,
    api_key: str,
    publisher: Publisher,
    console: Console | None = None,
) -> None:
    out = console or Console()
    app = create_app(config, api_key=api_key)
    host, port = parse_listen(config.listen)
    server = uvicorn.Server(
        uvicorn.Config(app, host=host, port=port, log_level="info", access_log=True)
    )
    serve_task = asyncio.create_task(server.serve())
    try:
        await _wait_until_started(server, serve_task)
        endpoint = await asyncio.to_thread(publisher.start, listen_host=host, listen_port=port)
        print_ready(out, endpoint, config)
        await serve_task
    finally:
        try:
            await asyncio.to_thread(publisher.stop)
        except Exception:
            log.exception("publisher stop failed")
        server.should_exit = True
        if not serve_task.done():
            await serve_task
