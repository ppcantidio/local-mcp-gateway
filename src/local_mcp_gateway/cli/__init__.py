"""CLI layer: Typer entrypoint (`lmg`)."""

# Side-effect: register Typer commands on `app`.
from local_mcp_gateway.cli import commands as _commands  # noqa: F401
from local_mcp_gateway.cli.app import app

__all__ = ["app"]
