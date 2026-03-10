"""
Entry point for running the MCP server via `python -m mcp_server`.
Launches on stdio transport so that MCP clients can connect as a subprocess.
"""

import logging
from .server import build_mcp_server

def main() -> None:
    # Configure logging for the server. 
    # Must NOT log to stdout/stderr since stdio is used for the MCP protocol.
    logging.basicConfig(
        filename="mcp_server.log",
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(name)s - %(message)s"
    )
    logging.getLogger(__name__).info("Starting FastMCP server on stdio transport...")

    mcp = build_mcp_server()
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
