"""Errors raised by the CLI, proxy, and publishers."""


class GatewayError(Exception):
    """Base error for local-mcp-gateway."""


class ConfigError(GatewayError):
    """Invalid or missing configuration."""


class PublisherError(GatewayError):
    """A publisher failed to start, stop, or resolve a public URL."""


class BinaryMissingError(PublisherError):
    """A required CLI binary is not on PATH."""

    def __init__(self, binary: str, hint: str) -> None:
        self.binary = binary
        self.hint = hint
        super().__init__(f"{binary} not found on PATH. {hint}")
