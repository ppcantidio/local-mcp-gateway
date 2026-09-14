"""Starlette app: authenticated reverse proxy for Streamable HTTP / SSE."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import httpx
from starlette.applications import Starlette
from starlette.middleware.gzip import GZipMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response, StreamingResponse
from starlette.routing import Route

from local_mcp_gateway import __version__
from local_mcp_gateway.config import GatewayConfig
from local_mcp_gateway.proxy.auth import authorization_failure_reason, is_authorized
from local_mcp_gateway.proxy.headers import filter_request_headers, filter_response_headers
from local_mcp_gateway.proxy.routing import match_mcp
from local_mcp_gateway.proxy.sse import (
    is_event_stream,
    iter_with_sse_heartbeats,
    parse_sse_json_payload,
)

log = logging.getLogger("local_mcp_gateway")

SERVICE_NAME = "local-mcp-gateway"
UPSTREAM_TIMEOUT = httpx.Timeout(connect=15.0, read=None, write=30.0, pool=10.0)
UNAUTHORIZED_HEADERS = {"WWW-Authenticate": 'Bearer realm="local-mcp-gateway"'}
# Finite Streamable HTTP POST bodies (e.g. tools/list) — buffer then unwrap SSE→JSON.
SSE_UNWRAP_MAX_BYTES = 16 * 1024 * 1024


def create_app(
    config: GatewayConfig,
    *,
    api_key: str,
    httpx_transport: httpx.AsyncBaseTransport | None = None,
) -> Starlette:
    @asynccontextmanager
    async def lifespan(app: Starlette) -> AsyncIterator[None]:
        async with httpx.AsyncClient(
            timeout=UPSTREAM_TIMEOUT,
            transport=httpx_transport,
            follow_redirects=False,
            trust_env=False,
            limits=httpx.Limits(max_keepalive_connections=20, keepalive_expiry=30.0),
        ) as client:
            app.state.http = client
            yield

    async def healthz(_request: Request) -> JSONResponse:
        return JSONResponse(
            {
                "ok": True,
                "version": __version__,
                "sse_unwrap": True,
                "get_sse_disabled": config.get_sse_disabled(),
                "upstream_retries": config.proxy.upstream_retries,
            }
        )

    async def root(_request: Request) -> JSONResponse:
        return JSONResponse({"service": SERVICE_NAME, "version": __version__})

    async def no_oauth(_request: Request) -> JSONResponse:
        # Cursor probes these after a 401. We use static Bearer API keys, not OAuth.
        return JSONResponse(
            {
                "error": "oauth_not_supported",
                "message": "Authenticate with Authorization: Bearer <LMG_API_KEY>",
            },
            status_code=404,
        )

    async def proxy(request: Request) -> Response:
        if not is_authorized(
            request,
            api_key=api_key,
            header=config.auth.header,
            prefix=config.auth.prefix,
        ):
            reason = authorization_failure_reason(
                request,
                api_key=api_key,
                header=config.auth.header,
                prefix=config.auth.prefix,
            )
            log.warning("unauthorized %s %s (%s)", request.method, request.url.path, reason)
            return JSONResponse(
                {"error": "unauthorized"},
                status_code=401,
                headers=UNAUTHORIZED_HEADERS,
            )

        matched = match_mcp(request.url.path, config.mcp)
        if matched is None:
            return JSONResponse({"error": "not_found"}, status_code=404)

        # Long-lived idle GET SSE through Tailscale Funnel often surfaces as
        # Cursor Cloud "fetch failed" / flaky live discovery. MCP clients must
        # tolerate 405 and continue with POST-only Streamable HTTP.
        if request.method == "GET" and config.get_sse_disabled():
            return JSONResponse(
                {
                    "error": "get_sse_disabled",
                    "message": (
                        "GET SSE is disabled on this gateway (recommended for Funnel). "
                        "Use POST Streamable HTTP."
                    ),
                },
                status_code=405,
                headers={"Allow": "POST"},
            )

        server, rest = matched
        upstream_url = f"{server.origin}{rest}"
        headers = filter_request_headers(request.headers, server.host_header)
        client: httpx.AsyncClient = request.app.state.http
        body = await request.body()

        attempts = 1 + max(0, config.proxy.upstream_retries)
        resp: httpx.Response | None = None
        for attempt in range(attempts):
            req = client.build_request(
                request.method,
                upstream_url,
                headers=headers,
                content=body if body else None,
                params=request.query_params,
            )
            try:
                resp = await client.send(req, stream=True)
                break
            except httpx.RequestError:
                log.warning(
                    "upstream request failed for %s %s (attempt %s/%s)",
                    request.method,
                    upstream_url,
                    attempt + 1,
                    attempts,
                )
                if attempt + 1 >= attempts:
                    return JSONResponse({"error": "upstream_unavailable"}, status_code=502)
                await asyncio.sleep(0.05 * (attempt + 1))

        assert resp is not None
        out_headers = filter_response_headers(resp.headers)
        content_type = resp.headers.get("content-type")

        # Cursor Cloud Agents discover tools more reliably from JSON than from
        # SSE-framed Streamable HTTP POST bodies. Unwrap finite SSE→JSON.
        if (
            request.method in {"POST", "PUT", "PATCH"}
            and resp.status_code == 200
            and is_event_stream(content_type)
        ):
            try:
                raw = await resp.aread()
            finally:
                await resp.aclose()
            if len(raw) <= SSE_UNWRAP_MAX_BYTES:
                payload = parse_sse_json_payload(raw)
                if payload is not None:
                    out_headers = {
                        key: value
                        for key, value in out_headers.items()
                        if key.lower() != "content-type"
                    }
                    return JSONResponse(payload, status_code=200, headers=out_headers)
            return Response(
                content=raw,
                status_code=resp.status_code,
                headers=out_headers,
                media_type=content_type,
            )

        async def stream() -> AsyncIterator[bytes]:
            try:
                upstream = resp.aiter_bytes()
                if is_event_stream(content_type) and config.proxy.sse_heartbeat_seconds > 0:
                    upstream = iter_with_sse_heartbeats(
                        upstream,
                        interval_seconds=config.proxy.sse_heartbeat_seconds,
                    )
                async for chunk in upstream:
                    yield chunk
            finally:
                await resp.aclose()

        return StreamingResponse(
            stream(),
            status_code=resp.status_code,
            headers=out_headers,
            media_type=content_type,
        )

    routes = [
        Route("/healthz", healthz, methods=["GET", "HEAD"]),
        Route("/", root, methods=["GET", "HEAD"]),
        Route("/.well-known/{path:path}", no_oauth, methods=["GET", "HEAD", "POST"]),
        Route("/register", no_oauth, methods=["GET", "POST"]),
        Route(
            "/{path:path}",
            proxy,
            methods=["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"],
        ),
    ]
    app = Starlette(routes=routes, lifespan=lifespan)
    app.add_middleware(GZipMiddleware, minimum_size=500)
    app.state.config = config
    return app
