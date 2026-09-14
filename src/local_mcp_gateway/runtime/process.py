"""Subprocess runner used by tunnel publishers.

Tests inject a fake runner so CI never calls tailscale/cloudflared/ngrok.
"""

from __future__ import annotations

import re
import subprocess
import time
from dataclasses import dataclass
from typing import Protocol

from local_mcp_gateway.errors import BinaryMissingError, PublisherError

INSTALL_HINTS: dict[str, str] = {
    "tailscale": "Install the Tailscale CLI: https://tailscale.com/download",
    "cloudflared": (
        "Install cloudflared: "
        "https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/"
    ),
    "ngrok": "Install the ngrok CLI: https://ngrok.com/download",
}


@dataclass(frozen=True)
class RunResult:
    returncode: int
    stdout: str
    stderr: str

    def fail_if_nonzero(self, action: str) -> None:
        if self.returncode == 0:
            return
        detail = (self.stderr or self.stdout).strip() or f"exit {self.returncode}"
        raise PublisherError(f"{action} failed: {detail}")


class SpawnedProcess(Protocol):
    def wait_for_match(self, pattern: re.Pattern[str], *, timeout: float) -> re.Match[str]: ...

    def terminate(self) -> None: ...


class CommandRunner(Protocol):
    def run(self, argv: list[str], *, timeout: float | None = 30) -> RunResult: ...

    def spawn(self, argv: list[str]) -> SpawnedProcess: ...


class SubprocessSpawned:
    def __init__(self, proc: subprocess.Popen[str]) -> None:
        self._proc = proc

    def wait_for_match(self, pattern: re.Pattern[str], *, timeout: float) -> re.Match[str]:
        deadline = time.monotonic() + timeout
        buf = ""
        stdout = self._proc.stdout
        while time.monotonic() < deadline:
            if stdout is None:
                break
            line = stdout.readline()
            if line == "":
                if self._proc.poll() is not None:
                    break
                time.sleep(0.05)
                continue
            buf += line
            match = pattern.search(buf)
            if match:
                return match
        snippet = buf[-2000:] if buf else "(no output)"
        raise PublisherError(f"Timed out waiting for a public HTTPS URL.\n{snippet}")

    def terminate(self) -> None:
        if self._proc.poll() is not None:
            return
        self._proc.terminate()
        try:
            self._proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            self._proc.kill()
            self._proc.wait(timeout=5)


class SystemCommandRunner:
    """Runs real binaries from PATH."""

    def run(self, argv: list[str], *, timeout: float | None = 30) -> RunResult:
        try:
            completed = subprocess.run(
                argv,
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False,
            )
        except FileNotFoundError:
            binary = argv[0]
            raise BinaryMissingError(binary, INSTALL_HINTS.get(binary, "")) from None
        return RunResult(completed.returncode, completed.stdout, completed.stderr)

    def spawn(self, argv: list[str]) -> SpawnedProcess:
        try:
            proc = subprocess.Popen(
                argv,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
            )
        except FileNotFoundError:
            binary = argv[0]
            raise BinaryMissingError(binary, INSTALL_HINTS.get(binary, "")) from None
        return SubprocessSpawned(proc)
