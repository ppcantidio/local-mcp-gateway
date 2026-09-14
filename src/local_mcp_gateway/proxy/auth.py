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


def authorization_failure_reason(
    request: Request,
    *,
    api_key: str,
    header: str,
    prefix: str,
) -> str:
    """Safe diagnostic for logs — never includes the secret value."""
    provided = request.headers.get(header, "") or ""
    if not provided:
        return "missing_authorization"
    if "${" in provided:
        return "unsubstituted_placeholder"
    if provided.startswith("Bearer Bearer "):
        return "double_bearer_prefix"
    expected = f"{prefix}{api_key}"
    if len(provided) != len(expected):
        return f"length_mismatch provided={len(provided)} expected={len(expected)}"
    if prefix and not provided.startswith(prefix):
        return "bad_prefix"
    return "wrong_token"
