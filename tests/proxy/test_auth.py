from __future__ import annotations

import httpx
from starlette.testclient import TestClient

from local_mcp_gateway.config import GatewayConfig
from local_mcp_gateway.proxy import create_app
from tests.conftest import TEST_API_KEY


def _client(config: GatewayConfig, transport: httpx.MockTransport | None = None) -> TestClient:
    app = create_app(config, api_key=TEST_API_KEY, httpx_transport=transport)
    return TestClient(app)


def test_healthz_has_no_auth(paper_config: GatewayConfig) -> None:
    with _client(paper_config) as client:
        response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"ok": True}


def test_root_has_no_auth(paper_config: GatewayConfig) -> None:
    with _client(paper_config) as client:
        response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"service": "local-mcp-gateway"}


def test_missing_api_key_is_401(paper_config: GatewayConfig) -> None:
    with _client(paper_config) as client:
        response = client.post(
            "/paper/mcp",
            json={"jsonrpc": "2.0", "id": 1, "method": "initialize"},
        )
    assert response.status_code == 401
    assert response.json() == {"error": "unauthorized"}


def test_wrong_api_key_is_401(paper_config: GatewayConfig) -> None:
    with _client(paper_config) as client:
        response = client.post(
            "/paper/mcp",
            json={"jsonrpc": "2.0", "id": 1, "method": "initialize"},
            headers={"Authorization": "Bearer wrong"},
        )
    assert response.status_code == 401
    assert response.json() == {"error": "unauthorized"}


def test_unnamed_mcp_path_is_401_without_key(paper_config: GatewayConfig) -> None:
    with _client(paper_config) as client:
        response = client.post("/mcp", json={})
    assert response.status_code == 401
    assert response.json()["error"] == "unauthorized"
    assert response.headers.get("www-authenticate", "").startswith("Bearer")


def test_oauth_discovery_is_404_without_auth(paper_config: GatewayConfig) -> None:
    with _client(paper_config) as client:
        well_known = client.get("/.well-known/oauth-protected-resource/paper/mcp")
        register = client.post("/register", json={})
    assert well_known.status_code == 404
    assert well_known.json()["error"] == "oauth_not_supported"
    assert register.status_code == 404
