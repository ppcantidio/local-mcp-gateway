"""Fake command runner for publisher unit tests."""

from __future__ import annotations

import re

from local_mcp_gateway.errors import BinaryMissingError, PublisherError
from local_mcp_gateway.runtime.process import INSTALL_HINTS, RunResult, SpawnedProcess


class FakeSpawned:
    def __init__(self, output: str) -> None:
        self.output = output
        self.terminated = False

    def wait_for_match(self, pattern: re.Pattern[str], *, timeout: float) -> re.Match[str]:
        del timeout
        match = pattern.search(self.output)
        if match is None:
            raise PublisherError("fake process produced no matching URL")
        return match

    def terminate(self) -> None:
        self.terminated = True


class FakeRun:
    def __init__(
        self,
        argv_prefix: tuple[str, ...],
        *,
        returncode: int = 0,
        stdout: str = "",
        stderr: str = "",
    ) -> None:
        self.argv_prefix = argv_prefix
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


class FakeRunner:
    def __init__(self) -> None:
        self.runs: list[list[str]] = []
        self.spawns: list[list[str]] = []
        self.spawned: FakeSpawned | None = None
        self.missing: set[str] = set()
        self._handlers: list[FakeRun] = []
        self._spawn_output = ""

    def add_run(
        self,
        argv_prefix: list[str],
        *,
        returncode: int = 0,
        stdout: str = "",
        stderr: str = "",
    ) -> None:
        self._handlers.append(
            FakeRun(tuple(argv_prefix), returncode=returncode, stdout=stdout, stderr=stderr)
        )

    def set_spawn_output(self, output: str) -> None:
        self._spawn_output = output

    def run(self, argv: list[str], *, timeout: float | None = 30) -> RunResult:
        del timeout
        if argv[0] in self.missing:
            raise BinaryMissingError(argv[0], INSTALL_HINTS.get(argv[0], ""))
        self.runs.append(argv)
        for handler in self._handlers:
            if tuple(argv[: len(handler.argv_prefix)]) == handler.argv_prefix:
                return RunResult(handler.returncode, handler.stdout, handler.stderr)
        return RunResult(0, "", "")

    def spawn(self, argv: list[str]) -> SpawnedProcess:
        if argv[0] in self.missing:
            raise BinaryMissingError(argv[0], INSTALL_HINTS.get(argv[0], ""))
        self.spawns.append(argv)
        self.spawned = FakeSpawned(self._spawn_output)
        return self.spawned
