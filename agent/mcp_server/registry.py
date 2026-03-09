from __future__ import annotations

from typing import Iterable, Protocol

from mcp.server.fastmcp import FastMCP


class ToolModule(Protocol):
    def register(self, mcp: FastMCP) -> None:
        """Attach tool functions to an MCP server instance."""


def register_modules(mcp: FastMCP, modules: Iterable[ToolModule]) -> None:
    for module in modules:
        module.register(mcp)
