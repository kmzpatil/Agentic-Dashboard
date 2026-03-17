"""
system_tools.py
---------------
MCP Tool Module for system-level utilities.
Currently provides:
  - get_current_time
"""

from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
from mcp.server.fastmcp import FastMCP

@dataclass
class SystemToolModule:
    def register(self, mcp: FastMCP) -> None:
        
        @mcp.tool()
        def get_current_time() -> str:
            """Return the current local date and time. 
            Use this to resolve relative time queries like 'today', 'yesterday', or 'last month'."""
            now = datetime.now()
            return now.strftime("%Y-%m-%d %H:%M:%S")
