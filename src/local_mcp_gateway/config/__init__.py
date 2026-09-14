"""Configuration layer: models, file IO, env secrets, CLI merge."""

from local_mcp_gateway.config.io import dumps_config, load_config, save_config
from local_mcp_gateway.config.merge import merge_serve_options, parse_mcp_option
from local_mcp_gateway.config.models import (
    AuthConfig,
    GatewayConfig,
    McpServer,
    ProxyConfig,
    PublisherConfig,
    parse_listen,
)
from local_mcp_gateway.config.paths import (
    CONFIG_FILENAME,
    XDG_CONFIG,
    default_config_path,
    example_toml_text,
    resolve_config_path,
)
from local_mcp_gateway.config.secrets import (
    RuntimeSecrets,
    generate_api_key,
    require_api_key,
)

__all__ = [
    "CONFIG_FILENAME",
    "XDG_CONFIG",
    "AuthConfig",
    "GatewayConfig",
    "McpServer",
    "ProxyConfig",
    "PublisherConfig",
    "RuntimeSecrets",
    "default_config_path",
    "dumps_config",
    "example_toml_text",
    "generate_api_key",
    "load_config",
    "merge_serve_options",
    "parse_listen",
    "parse_mcp_option",
    "require_api_key",
    "resolve_config_path",
    "save_config",
]
