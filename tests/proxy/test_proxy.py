from __future__ import annotations

import httpx
from starlette.testclient import TestClient

from local_mcp_gateway.config import GatewayConfig, McpServer
from local_mcp_gateway.proxy import create_app, match_mcp
from tests.conftest import TEST_API_KEY

AUTH = {"Authorization": f"Bearer {TEST_API_KEY}"}


def test_match_mcp_strips_name_prefix(paper_config: GatewayConfig) -> None:
    matched = match_mcp("/paper/mcp", paper_config.mcp)
    assert matched is not None
    server, rest = matched
    assert server.name == "paper"
    assert rest == "/mcp"


def test_valid_key_rewrites_host_and_strips_auth(paper_config: GatewayConfig) -> None:
    captured: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        return httpx.Response(
            200,
            json={"jsonrpc": "2.0", "id": 1, "result": {"serverInfo": {"name": "paper-desktop"}}},
            headers={"mcp-session-id": "sess-1"},
        )

    paper_config.mcp = [
        McpServer(
            name="paper",
            url="http://127.0.0.1:9",
            rewrite_host="127.0.0.1:29979",
        )
    ]
    transport = httpx.MockTransport(handler)
    app = create_app(paper_config, api_key=TEST_API_KEY, httpx_transport=transport)
    with TestClient(app) as client:
        response = client.post(
            "/paper/mcp",
            json={"jsonrpc": "2.0", "id": 1, "method": "initialize"},
            headers={
                **AUTH,
                "Origin": "https://evil.example",
                "Cookie": "session=1",
                "Mcp-Session-Id": "sess-1",
            },
        )
    assert response.status_code == 200
    assert response.json()["result"]["serverInfo"]["name"] == "paper-desktop"
    assert response.headers["mcp-session-id"] == "sess-1"
    assert len(captured) == 1
    upstream = captured[0]
    assert str(upstream.url) == "http://127.0.0.1:9/mcp"
    assert upstream.headers.get("host") == "127.0.0.1:29979"
    assert "authorization" not in upstream.headers
    assert "cookie" not in upstream.headers
    assert "origin" not in upstream.headers
    assert upstream.headers.get("mcp-session-id") == "sess-1"


def test_unknown_mcp_is_404_with_valid_key(paper_config: GatewayConfig) -> None:
    transport = httpx.MockTransport(lambda _r: httpx.Response(200))
    app = create_app(paper_config, api_key=TEST_API_KEY, httpx_transport=transport)
    with TestClient(app) as client:
        response = client.post("/other/mcp", json={}, headers=AUTH)
    assert response.status_code == 404


def test_query_string_is_forwarded(paper_config: GatewayConfig) -> None:
    captured: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        return httpx.Response(200, json={"ok": True})

    transport = httpx.MockTransport(handler)
    app = create_app(paper_config, api_key=TEST_API_KEY, httpx_transport=transport)
    with TestClient(app) as client:
        response = client.get("/paper/mcp", params={"session": "1"}, headers=AUTH)
    assert response.status_code == 200
    assert captured[0].url.params.get("session") == "1"


def test_sse_post_is_unwrapped_to_json(paper_config: GatewayConfig) -> None:
    sse = (
        "event: message\n"
        'data: {"jsonrpc":"2.0","id":2,"result":{"tools":[{"name":"open_file"}]}}\n'
        "\n"
    )

    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            content=sse.encode(),
            headers={
                "content-type": "text/event-stream",
                "mcp-session-id": "sess-unwrap",
                "cache-control": "no-cache",
            },
        )

    app = create_app(
        paper_config,
        api_key=TEST_API_KEY,
        httpx_transport=httpx.MockTransport(handler),
    )
    with TestClient(app) as client:
        response = client.post(
            "/paper/mcp",
            json={"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}},
            headers=AUTH,
        )
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/json")
    assert response.headers["mcp-session-id"] == "sess-unwrap"
    assert response.json()["result"]["tools"][0]["name"] == "open_file"
