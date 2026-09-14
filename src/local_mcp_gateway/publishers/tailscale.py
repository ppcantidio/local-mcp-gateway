from __future__ import annotations

import json

from local_mcp_gateway.errors import PublisherError
from local_mcp_gateway.publishers.base import PublishedEndpoint
from local_mcp_gateway.publishers.local import loopback_host
from local_mcp_gateway.runtime.process import CommandRunner

FUNNEL_HTTPS_PORTS = (443, 8443, 10000)
DEFAULT_HTTPS_PORT = 443


class TailscalePublisher:
    name = "tailscale"

    def __init__(self, *, mode: str | None, runner: CommandRunner) -> None:
        if mode not in {"serve", "funnel"}:
            raise PublisherError("tailscale publisher requires mode 'serve' or 'funnel'")
        self.mode = mode
        self._runner = runner
        self._https_port = DEFAULT_HTTPS_PORT
        self._mapped = False

    def start(self, *, listen_host: str, listen_port: int) -> PublishedEndpoint:
        target_host = loopback_host(listen_host)
        if self.mode == "serve":
            argv = [
                "tailscale",
                "serve",
                "--bg",
                f"--https={self._https_port}",
                f"http://{target_host}:{listen_port}",
            ]
        else:
            if self._https_port not in FUNNEL_HTTPS_PORTS:
                raise PublisherError(
                    f"Funnel public HTTPS port must be one of {FUNNEL_HTTPS_PORTS}"
                )
            argv = [
                "tailscale",
                "funnel",
                "--bg",
                f"--https={self._https_port}",
                str(listen_port),
            ]
        result = self._runner.run(argv)
        result.fail_if_nonzero(f"tailscale {self.mode}")
        self._mapped = True
        return PublishedEndpoint(url=self._public_origin())

    def stop(self) -> None:
        if not self._mapped:
            return
        argv = [
            "tailscale",
            self.mode,
            f"--https={self._https_port}",
            "off",
        ]
        result = self._runner.run(argv)
        result.fail_if_nonzero(f"tailscale {self.mode} off")
        self._mapped = False

    def _public_origin(self) -> str:
        status = self._runner.run(["tailscale", "status", "--json"])
        status.fail_if_nonzero("tailscale status --json")
        try:
            payload = json.loads(status.stdout)
            dns_name = payload["Self"]["DNSName"].rstrip(".")
        except (json.JSONDecodeError, KeyError, TypeError, AttributeError) as exc:
            raise PublisherError(
                "could not read Self.DNSName from tailscale status --json"
            ) from exc
        if not dns_name:
            raise PublisherError("tailscale status --json had an empty Self.DNSName")
        return f"https://{dns_name}"
