"""HTTP proxy layer: auth, routing, Host rewrite, SSE streaming."""

from local_mcp_gateway.proxy.app import SERVICE_NAME, create_app
from local_mcp_gateway.proxy.routing import match_mcp

__all__ = ["SERVICE_NAME", "create_app", "match_mcp"]
