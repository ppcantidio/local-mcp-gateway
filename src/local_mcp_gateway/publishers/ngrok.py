from __future__ import annotations

import json
import re

from local_mcp_gateway.errors import PublisherError
from local_mcp_gateway.publishers.base import PublishedEndpoint
from local_mcp_gateway.runtime.process import CommandRunner, SpawnedProcess

NGROK_HTTPS = re.compile(r"https://[a-zA-Z0-9.-]+")
URL_TIMEOUT = 45.0


class NgrokPublisher:
    name = "ngrok"

    def __init__(self, *, mode: str | None = None, runner: CommandRunner) -> None:
        del mode
        self._runner = runner
        self._proc: SpawnedProcess | None = None

    def start(self, *, listen_host: str, listen_port: int) -> PublishedEndpoint:
        del listen_host
        argv = [
            "ngrok",
            "http",
            str(listen_port),
            "--log",
            "stdout",
            "--log-format",
            "json",
        ]
        self._proc = self._runner.spawn(argv)
        try:
            match = self._proc.wait_for_match(NGROK_HTTPS, timeout=URL_TIMEOUT)
        except Exception:
            self.stop()
            raise
        url = _https_url_from_ngrok_output(match.string)
        return PublishedEndpoint(url=url.rstrip("/"))

    def stop(self) -> None:
        if self._proc is None:
            return
        self._proc.terminate()
        self._proc = None


def _https_url_from_ngrok_output(blob: str) -> str:
    for line in blob.splitlines():
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        candidate = payload.get("url")
        if isinstance(candidate, str) and candidate.startswith("https://"):
            return candidate
    match = NGROK_HTTPS.search(blob)
    if match and "127.0.0.1" not in match.group(0) and "localhost" not in match.group(0):
        return match.group(0)
    raise PublisherError("ngrok started but no public https URL was found in logs")
