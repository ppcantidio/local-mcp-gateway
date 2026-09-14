"""Helpers for MCP Streamable HTTP SSE payloads."""

from __future__ import annotations

import json
from typing import Any


def is_event_stream(content_type: str | None) -> bool:
    if not content_type:
        return False
    return "text/event-stream" in content_type.lower()


def parse_sse_json_payload(body: bytes) -> Any | None:
    """Extract the last JSON `data:` payload from a finite SSE body.

    Paper/Desktop Streamable HTTP often returns a single ``event: message``
    frame. Cursor Cloud Agents handle ``application/json`` more reliably than
    SSE-framed POST responses, so the gateway unwraps when possible.
    """
    if not body:
        return None
    text = body.decode("utf-8", errors="replace")
    data_lines: list[str] = []
    last_payload: Any | None = None

    def flush() -> None:
        nonlocal data_lines, last_payload
        if not data_lines:
            return
        blob = "\n".join(data_lines)
        data_lines = []
        try:
            last_payload = json.loads(blob)
        except json.JSONDecodeError:
            return

    for line in text.splitlines():
        if line.startswith(":"):
            continue
        if line == "":
            flush()
            continue
        if line.startswith("data:"):
            data_lines.append(line[5:].lstrip())
            continue
        # Other SSE fields (event/id/retry) end a prior data block only on blank line.
    flush()
    return last_payload
