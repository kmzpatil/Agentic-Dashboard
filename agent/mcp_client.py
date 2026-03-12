"""
mcp_client.py
─────────────
Reusable async MCP client that connects to the local mcp_server via stdio.

Usage:
    async with MCPClient() as client:
        tools = await client.list_tools()
        result = await client.call_tool("get_monthly_trend", {})
"""

import json
import logging
import sys
import os
from pathlib import Path
from contextlib import asynccontextmanager
from typing import Any

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# ... (logging config remains the same)
logger = logging.getLogger("mcp_client")


class MCPClient:
    """Async context-manager wrapper around an MCP stdio session."""

    def __init__(self, server_command: str | None = None) -> None:
        agent_dir = str(Path(__file__).parent.resolve())
        env = os.environ.copy()
        # Add 'agent' directory to PYTHONPATH so '-m mcp_server' works from root
        existing_pp = env.get("PYTHONPATH", "")
        env["PYTHONPATH"] = f"{agent_dir}{os.pathsep}{existing_pp}" if existing_pp else agent_dir

        self._server_params = StdioServerParameters(
            command=sys.executable,
            args=["-m", "mcp_server"],
            env=env,
        )
        self._session: ClientSession | None = None
        self._cm_stack: list = []

    async def __aenter__(self) -> "MCPClient":
        # stdio_client returns an async context-manager yielding (read, write) streams
        self._stdio_cm = stdio_client(self._server_params)
        self._read, self._write = await self._stdio_cm.__aenter__()

        # ClientSession wraps the raw streams into a proper MCP session
        self._session_cm = ClientSession(self._read, self._write)
        self._session = await self._session_cm.__aenter__()

        # Initialize the MCP handshake
        logger.info("Initializing MCP session with subprocess...")
        await self._session.initialize()
        logger.info("MCP session initialized successfully.")
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        logger.info("Closing MCP session...")
        if self._session_cm:
            await self._session_cm.__aexit__(exc_type, exc_val, exc_tb)
        if self._stdio_cm:
            await self._stdio_cm.__aexit__(exc_type, exc_val, exc_tb)
        logger.info("MCP session closed.")

    async def list_tools(self) -> list[dict[str, Any]]:
        """Return a list of tool metadata dicts from the MCP server."""
        assert self._session, "MCPClient not connected. Use `async with MCPClient() as c:`"
        result = await self._session.list_tools()
        return [
            {
                "name": t.name,
                "description": t.description or "",
                "input_schema": t.inputSchema,
            }
            for t in result.tools
        ]

    async def call_tool(self, tool_name: str, arguments: dict[str, Any] | None = None) -> str:
        """
        Call a tool on the MCP server by name and return the text result.

        Args:
            tool_name:  Exact tool name as registered on the server.
            arguments:  Dict of keyword arguments for the tool.

        Returns:
            The tool's text output as a string (usually JSON).
        """
        assert self._session, "MCPClient not connected. Use `async with MCPClient() as c:`"
        logger.debug(f"Calling tool '{tool_name}' with args {arguments}")
        result = await self._session.call_tool(tool_name, arguments or {})

        # MCP tool results contain a list of content blocks; concatenate text ones
        texts = [block.text for block in result.content if hasattr(block, "text")]
        combined_text = "\n".join(texts)
        logger.debug(f"Tool '{tool_name}' returned {len(combined_text)} chars")
        return combined_text
