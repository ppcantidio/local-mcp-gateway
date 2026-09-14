"""CLI commands for `lmg`."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Annotated

import typer
from rich.table import Table

from local_mcp_gateway.cli.app import app, console, die, load_or_die
from local_mcp_gateway.config import (
    CONFIG_FILENAME,
    GatewayConfig,
    McpServer,
    default_config_path,
    example_toml_text,
    generate_api_key,
    load_config,
    merge_serve_options,
    require_api_key,
    resolve_config_path,
    save_config,
)
from local_mcp_gateway.errors import ConfigError, GatewayError
from local_mcp_gateway.publishers import create_publisher
from local_mcp_gateway.runtime import run_gateway


@app.command()
def init(
    force: Annotated[bool, typer.Option("--force", help="Overwrite an existing lmg.toml")] = False,
) -> None:
    """Write ./lmg.toml from the example and print a new API key once."""
    dest = Path.cwd() / CONFIG_FILENAME
    if dest.exists() and not force:
        die(f"{dest} already exists. Pass --force to overwrite.")
    dest.write_text(example_toml_text(), encoding="utf-8")
    key = generate_api_key()
    console.print(f"Wrote {dest}")
    console.print("API key (export as LMG_API_KEY; shown once, not written to disk):")
    console.print(key)


@app.command()
def keygen() -> None:
    """Print a new API key. Does not write it to disk."""
    console.print(generate_api_key())


@app.command()
def add(
    name: str,
    url: str,
    rewrite_host: Annotated[
        str | None,
        typer.Option(
            "--rewrite-host",
            help="Host header sent upstream (default: host:port of url)",
        ),
    ] = None,
    config: Annotated[
        Path | None,
        typer.Option(
            "--config",
            help="Config file (default: ./lmg.toml then ~/.config/lmg/config.toml)",
        ),
    ] = None,
) -> None:
    """Register a local MCP server in the config file."""
    path = config or resolve_config_path(None) or default_config_path()
    if path.is_file():
        try:
            cfg = load_config(path)
        except ConfigError as exc:
            die(str(exc))
    else:
        cfg = GatewayConfig()
    try:
        server = McpServer(name=name, url=url, rewrite_host=rewrite_host)
    except Exception as exc:
        die(str(exc))
    existed = any(item.name == server.name for item in cfg.mcp)
    cfg.upsert(server)
    save_config(path, cfg)
    action = "Updated" if existed else "Added"
    console.print(f"{action} {server.name} → {server.origin} (rewrite Host: {server.host_header})")
    console.print(f"Wrote {path}")


@app.command("ls")
def ls_cmd(
    config: Annotated[Path | None, typer.Option("--config")] = None,
) -> None:
    """List registered local MCP servers."""
    path, cfg = load_or_die(config)
    if not cfg.mcp:
        console.print(f"No MCP servers in {path}. Use `lmg add NAME URL`.")
        return
    table = Table(title=str(path))
    table.add_column("name")
    table.add_column("url")
    table.add_column("rewrite_host")
    for item in cfg.mcp:
        table.add_row(item.name, item.url, item.host_header)
    console.print(table)


@app.command("rm")
def rm_cmd(
    name: str,
    config: Annotated[Path | None, typer.Option("--config")] = None,
) -> None:
    """Remove a registered local MCP server."""
    path, cfg = load_or_die(config)
    try:
        cfg.remove(name)
    except ConfigError as exc:
        die(str(exc))
    save_config(path, cfg)
    console.print(f"Removed {name} from {path}")


@app.command()
def serve(
    publisher: Annotated[
        str | None,
        typer.Option("--publisher", help="local | tailscale | cloudflare | ngrok"),
    ] = None,
    mode: Annotated[
        str | None,
        typer.Option("--mode", help="tailscale only: serve | funnel"),
    ] = None,
    listen: Annotated[str | None, typer.Option("--listen", help="host:port to bind")] = None,
    config: Annotated[Path | None, typer.Option("--config")] = None,
    only: Annotated[
        list[str] | None,
        typer.Option("--only", help="Expose only these registered names (repeatable)"),
    ] = None,
    mcp: Annotated[
        list[str] | None,
        typer.Option("--mcp", help="Ephemeral name=url for this run (repeatable)"),
    ] = None,
) -> None:
    """Start the localhost proxy and the configured publisher."""
    resolved = resolve_config_path(config)
    if resolved is not None and resolved.is_file():
        try:
            cfg = load_config(resolved)
        except ConfigError as exc:
            die(str(exc))
    elif config is not None:
        die(f"config not found: {config}")
    else:
        cfg = GatewayConfig()
    try:
        cfg = merge_serve_options(
            cfg,
            publisher=publisher,
            mode=mode,
            listen=listen,
            mcp=mcp,
            only=only,
        )
    except ConfigError as exc:
        die(str(exc))
    except Exception as exc:
        die(str(exc))
    if not cfg.mcp:
        die("No MCP servers registered. Use `lmg add NAME URL` or `lmg serve --mcp name=url`.")
    try:
        api_key = require_api_key()
    except ConfigError as exc:
        die(str(exc))
    try:
        pub = create_publisher(cfg.publisher.name, mode=cfg.publisher.mode)
    except GatewayError as exc:
        die(str(exc))
    try:
        asyncio.run(run_gateway(cfg, api_key=api_key, publisher=pub, console=console))
    except KeyboardInterrupt:
        raise typer.Exit(0) from None
    except GatewayError as exc:
        die(str(exc))
