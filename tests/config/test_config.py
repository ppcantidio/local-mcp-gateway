from __future__ import annotations

from pathlib import Path

import pytest

from local_mcp_gateway.config import (
    GatewayConfig,
    McpServer,
    dumps_config,
    load_config,
    merge_serve_options,
    parse_mcp_option,
    save_config,
)
from local_mcp_gateway.errors import ConfigError


def test_roundtrip_toml(tmp_path: Path) -> None:
    path = tmp_path / "lmg.toml"
    config = GatewayConfig(
        mcp=[McpServer(name="paper", url="http://127.0.0.1:29979", rewrite_host="127.0.0.1:29979")]
    )
    save_config(path, config)
    loaded = load_config(path)
    assert loaded.mcp[0].name == "paper"
    assert loaded.mcp[0].host_header == "127.0.0.1:29979"
    assert "29979" in dumps_config(loaded)


def test_parse_mcp_option() -> None:
    server = parse_mcp_option("paper=http://127.0.0.1:29979")
    assert server.name == "paper"
    assert server.host_header == "127.0.0.1:29979"


def test_merge_ephemeral_and_only() -> None:
    config = GatewayConfig(
        mcp=[
            McpServer(name="paper", url="http://127.0.0.1:29979"),
            McpServer(name="other", url="http://127.0.0.1:3100"),
        ]
    )
    merged = merge_serve_options(
        config,
        publisher="cloudflare",
        mode=None,
        listen=None,
        mcp=["extra=http://127.0.0.1:4000"],
        only=["extra"],
    )
    assert merged.publisher.name == "cloudflare"
    assert [item.name for item in merged.mcp] == ["extra"]


def test_rewrite_host_defaults_to_url_netloc() -> None:
    server = McpServer(name="paper", url="http://127.0.0.1:29979")
    assert server.host_header == "127.0.0.1:29979"


def test_reserved_name() -> None:
    with pytest.raises(ValueError, match="reserved"):
        McpServer(name="healthz", url="http://127.0.0.1:1")


def test_unknown_only_name() -> None:
    config = GatewayConfig(mcp=[McpServer(name="paper", url="http://127.0.0.1:29979")])
    with pytest.raises(ConfigError, match="unknown"):
        merge_serve_options(config, publisher=None, mode=None, listen=None, mcp=None, only=["nope"])
