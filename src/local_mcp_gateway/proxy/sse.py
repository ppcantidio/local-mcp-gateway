"""Helpers for MCP Streamable HTTP SSE payloads."""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator
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


async def iter_with_sse_heartbeats(
    chunks: AsyncIterator[bytes],
    *,
    interval_seconds: float,
) -> AsyncIterator[bytes]:
    """Pass through bytes, injecting SSE comment heartbeats while idle.

    Heartbeats are only emitted at SSE event boundaries (buffer ends with
    ``\\n\\n``) or before any upstream data arrives, so we never split a frame.
    """
    if interval_seconds <= 0:
        async for chunk in chunks:
            yield chunk
        return

    agen = chunks.__aiter__()
    pending = asyncio.create_task(agen.__anext__())
    buf = b""
    try:
        while True:
            done, _ = await asyncio.wait({pending}, timeout=interval_seconds)
            if not done:
                if not buf or buf.endswith(b"\n\n"):
                    yield b": keepalive\n\n"
                continue
            try:
                chunk = pending.result()
            except StopAsyncIteration:
                break
            buf += chunk
            # Cap buffer used only for boundary detection.
            if len(buf) > 64:
                buf = buf[-64:]
            yield chunk
            pending = asyncio.create_task(agen.__anext__())
    finally:
        if not pending.done():
            pending.cancel()
            try:
                await pending
            except (asyncio.CancelledError, StopAsyncIteration):
                pass
