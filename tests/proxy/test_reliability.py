from __future__ import annotations

import httpx
from starlette.testclient import TestClient

from local_mcp_gateway.config import GatewayConfig, ProxyConfig, PublisherConfig
from local_mcp_gateway.proxy import create_app
from tests.conftest import TEST_API_KEY

AUTH = {"Authorization": f"Bearer {TEST_API_KEY}"}


def test_funnel_keeps_get_sse_enabled_by_default(paper_config: GatewayConfig) -> None:
    paper_config.publisher = PublisherConfig(name="tailscale", mode="funnel")
    assert paper_config.get_sse_disabled() is False

    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"ok": True})

    app = create_app(
        paper_config,
        api_key=TEST_API_KEY,
        httpx_transport=httpx.MockTransport(handler),
    )
    with TestClient(app) as client:
        response = client.get("/paper/mcp", headers=AUTH)
        health = client.get("/healthz")
    assert response.status_code == 200
    assert response.json()["ok"] is True
    assert health.json()["get_sse_disabled"] is False
    assert health.json()["version"] == "0.1.4"


def test_explicit_disable_get_sse(paper_config: GatewayConfig) -> None:
    paper_config.publisher = PublisherConfig(name="tailscale", mode="funnel")
    paper_config.proxy = ProxyConfig(disable_get_sse=True)

    calls = {"n": 0}

    def handler(_request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        return httpx.Response(200, json={"ok": True})

    app = create_app(
        paper_config,
        api_key=TEST_API_KEY,
        httpx_transport=httpx.MockTransport(handler),
    )
    with TestClient(app) as client:
        response = client.get("/paper/mcp", headers=AUTH)
    assert response.status_code == 405
    assert response.json()["error"] == "get_sse_disabled"
    assert calls["n"] == 0


def test_upstream_retries_then_succeeds(paper_config: GatewayConfig) -> None:
    paper_config.proxy = ProxyConfig(upstream_retries=2, disable_get_sse=True)
    attempts = {"n": 0}

    def handler(_request: httpx.Request) -> httpx.Response:
        attempts["n"] += 1
        if attempts["n"] < 3:
            raise httpx.ConnectError("boom")
        return httpx.Response(200, json={"ok": True})

    app = create_app(
        paper_config,
        api_key=TEST_API_KEY,
        httpx_transport=httpx.MockTransport(handler),
    )
    with TestClient(app) as client:
        response = client.post("/paper/mcp", json={"jsonrpc": "2.0", "id": 1}, headers=AUTH)
    assert response.status_code == 200
    assert response.json()["ok"] is True
    assert attempts["n"] == 3


def test_sse_heartbeat_helper_emits_before_data() -> None:
    import asyncio

    from local_mcp_gateway.proxy.sse import iter_with_sse_heartbeats

    async def slow() -> None:
        async def gen():
            await asyncio.sleep(0.05)
            yield b'data: {"ok":true}\n\n'

        out = []
        async for chunk in iter_with_sse_heartbeats(gen(), interval_seconds=0.01):
            out.append(chunk)
        assert any(b"keepalive" in c for c in out)
        assert any(b"data:" in c for c in out)

    asyncio.run(slow())
