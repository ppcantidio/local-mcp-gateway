"""Constant-time API-key checks for the HTTP proxy."""

from __future__ import annotations

import hmac

from starlette.requests import Request


def is_authorized(
    request: Request,
    *,
    api_key: str,
    header: str,
    prefix: str,
) -> bool:
    provided = request.headers.get(header, "") or ""
    expected = f"{prefix}{api_key}"
    return hmac.compare_digest(provided.encode("utf-8"), expected.encode("utf-8"))
