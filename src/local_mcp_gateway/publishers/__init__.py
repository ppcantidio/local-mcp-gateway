"""Publisher registry. Adding a publisher is one module + one entry here."""

from __future__ import annotations

from local_mcp_gateway.errors import PublisherError
from local_mcp_gateway.publishers.base import Publisher
from local_mcp_gateway.publishers.cloudflare import CloudflarePublisher
from local_mcp_gateway.publishers.local import LocalPublisher
from local_mcp_gateway.publishers.ngrok import NgrokPublisher
from local_mcp_gateway.publishers.tailscale import TailscalePublisher
from local_mcp_gateway.runtime.process import CommandRunner, SystemCommandRunner

REGISTRY: dict[str, type] = {
    LocalPublisher.name: LocalPublisher,
    TailscalePublisher.name: TailscalePublisher,
    CloudflarePublisher.name: CloudflarePublisher,
    NgrokPublisher.name: NgrokPublisher,
}


def create_publisher(
    name: str,
    *,
    mode: str | None = None,
    runner: CommandRunner | None = None,
) -> Publisher:
    try:
        cls = REGISTRY[name]
    except KeyError:
        known = ", ".join(sorted(REGISTRY))
        raise PublisherError(f"unknown publisher {name!r}. built-in: {known}") from None
    resolved = runner or SystemCommandRunner()
    return cls(mode=mode, runner=resolved)
