"""Hop-by-hop / sensitive header filtering for upstream proxying."""

from __future__ import annotations

from collections.abc import Mapping

import httpx

DROP_REQUEST_HEADERS = frozenset(
    {
        "authorization",
        "cookie",
        "origin",
        "host",
        "connection",
        "keep-alive",
        "proxy-authenticate",
        "proxy-authorization",
        "te",
        "trailer",
        "transfer-encoding",
        "upgrade",
        "content-length",
    }
)
DROP_RESPONSE_HEADERS = frozenset(
    {
        "connection",
        "keep-alive",
        "proxy-authenticate",
        "proxy-authorization",
        "te",
        "trailer",
        "transfer-encoding",
        "upgrade",
        "content-encoding",
        "content-length",
    }
)


def filter_request_headers(headers: Mapping[str, str], rewrite_host: str) -> httpx.Headers:
    out = httpx.Headers()
    for key, value in headers.items():
        if key.lower() in DROP_REQUEST_HEADERS:
            continue
        out[key] = value
    out["host"] = rewrite_host
    return out


def filter_response_headers(headers: httpx.Headers) -> dict[str, str]:
    return {
        key: value for key, value in headers.items() if key.lower() not in DROP_RESPONSE_HEADERS
    }
