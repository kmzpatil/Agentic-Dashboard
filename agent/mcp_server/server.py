from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from .config import ServerSettings
from .database import DatabaseClient
from .modules import AnalyticsToolModule, DatabaseToolModule
from .registry import register_modules


def build_mcp_server(settings: ServerSettings | None = None) -> FastMCP:
    resolved_settings = settings or ServerSettings.from_env()
    mcp = FastMCP(resolved_settings.server_name)
    database_client = DatabaseClient(
        database_url=resolved_settings.database_url,
        default_schema=resolved_settings.default_schema,
    )
    modules = [
        DatabaseToolModule(database_client, resolved_settings),
        AnalyticsToolModule(database_client, resolved_settings),
    ]
    register_modules(mcp, modules)
    return mcp
