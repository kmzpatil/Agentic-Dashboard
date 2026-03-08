"""Utilities for building the Frammer MCP server."""

from .config import ServerSettings


def build_mcp_server(settings: ServerSettings | None = None):
    from .server import build_mcp_server as _build_mcp_server

    return _build_mcp_server(settings)


__all__ = ["ServerSettings", "build_mcp_server"]
