from __future__ import annotations

from local_mcp_gateway.publishers.base import PublishedEndpoint


def loopback_host(listen_host: str) -> str:
    if listen_host in {"0.0.0.0", "::", "[::]"}:
        return "127.0.0.1"
    return listen_host


class LocalPublisher:
    name = "local"

    def __init__(self, *, mode: str | None = None, runner: object | None = None) -> None:
        del mode, runner

    def start(self, *, listen_host: str, listen_port: int) -> PublishedEndpoint:
        host = loopback_host(listen_host)
        return PublishedEndpoint(url=f"http://{host}:{listen_port}")

    def stop(self) -> None:
        return None
