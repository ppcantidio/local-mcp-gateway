from __future__ import annotations

import pytest

from local_mcp_gateway.config import AuthConfig, GatewayConfig, McpServer, PublisherConfig

TEST_API_KEY = "test-token-for-local-mcp-gateway"


@pytest.fixture
def paper_config() -> GatewayConfig:
    return GatewayConfig(
        listen="127.0.0.1:8788",
        auth=AuthConfig(),
        publisher=PublisherConfig(name="local"),
        mcp=[
            McpServer(
                name="paper",
                url="http://127.0.0.1:29979",
                rewrite_host="127.0.0.1:29979",
            )
        ],
    )
