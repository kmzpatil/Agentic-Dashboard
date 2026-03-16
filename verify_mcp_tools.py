
import os, sys, asyncio
from dotenv import load_dotenv

# Ensure we are in the agent directory
os.chdir(os.path.join(os.getcwd(), "agent"))
sys.path.insert(0, os.getcwd())

from mcp_server.server import build_mcp_server

async def main():
    mcp = build_mcp_server()
    # FastMCP tools are in mcp.tools
    print("Registered tools in MCP:")
    for name, tool in mcp._tools.items():
        print(f"- {name}: {tool.description}")

if __name__ == "__main__":
    asyncio.run(main())
