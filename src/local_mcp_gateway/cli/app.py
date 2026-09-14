"""Typer app shell and shared CLI helpers."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Annotated, NoReturn

import typer
from rich.console import Console

from local_mcp_gateway import __version__
from local_mcp_gateway.config import (
    CONFIG_FILENAME,
    GatewayConfig,
    load_config,
    resolve_config_path,
)
from local_mcp_gateway.errors import ConfigError

app = typer.Typer(
    name="lmg",
    no_args_is_help=True,
    add_completion=False,
    help="Expose localhost MCP servers through a local proxy and a pluggable tunnel.",
)
console = Console()
err_console = Console(stderr=True)


def die(message: str, code: int = 1) -> NoReturn:
    err_console.print(f"[red]{message}[/red]")
    raise typer.Exit(code)


def load_or_die(path: Path | None) -> tuple[Path, GatewayConfig]:
    resolved = resolve_config_path(path)
    if resolved is None:
        die(f"No config found. Run `lmg init` or pass --config. Expected ./{CONFIG_FILENAME}")
    if not resolved.is_file():
        die(f"config not found: {resolved}")
    try:
        return resolved, load_config(resolved)
    except ConfigError as exc:
        die(str(exc))


def version_callback(value: bool) -> None:
    if value:
        console.print(__version__)
        raise typer.Exit()


@app.callback()
def main(
    version: Annotated[
        bool,
        typer.Option("--version", callback=version_callback, is_eager=True),
    ] = False,
) -> None:
    """Expose localhost MCP servers through a local proxy and a pluggable tunnel."""
    del version
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
