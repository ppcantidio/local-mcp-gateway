from __future__ import annotations

import re

from local_mcp_gateway.publishers.base import PublishedEndpoint
from local_mcp_gateway.publishers.local import loopback_host
from local_mcp_gateway.runtime.process import CommandRunner, SpawnedProcess

TRYCLOUDFLARE_URL = re.compile(r"https://[a-z0-9-]+\.trycloudflare\.com")
URL_TIMEOUT = 45.0


class CloudflarePublisher:
    name = "cloudflare"

    def __init__(self, *, mode: str | None = None, runner: CommandRunner) -> None:
        del mode
        self._runner = runner
        self._proc: SpawnedProcess | None = None

    def start(self, *, listen_host: str, listen_port: int) -> PublishedEndpoint:
        host = loopback_host(listen_host)
        argv = [
            "cloudflared",
            "tunnel",
            "--url",
            f"http://{host}:{listen_port}",
        ]
        self._proc = self._runner.spawn(argv)
        try:
            match = self._proc.wait_for_match(TRYCLOUDFLARE_URL, timeout=URL_TIMEOUT)
        except Exception:
            self.stop()
            raise
        return PublishedEndpoint(url=match.group(0).rstrip("/"))

    def stop(self) -> None:
        if self._proc is None:
            return
        self._proc.terminate()
        self._proc = None
