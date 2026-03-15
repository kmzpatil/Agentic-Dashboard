from __future__ import annotations

import json

from mcp.server.fastmcp import FastMCP

from backend.analytics.overview_service import get_overview_snapshot
from backend.analytics.trends_service import get_trends_snapshot
from backend.insights.service import build_insights
from backend.middleware.auth import AuthContext


def _make_auth_context(role: str = "website_admin", client_name: str | None = None, user_id: int | None = None) -> AuthContext:
    return AuthContext(
        auth_user_id="mcp",
        username="mcp",
        role=role,
        client_name=client_name,
        user_id=user_id,
    )


def build_mcp_server() -> FastMCP:
    mcp = FastMCP("frammer-mcp")

    @mcp.tool()
    def get_overview(role: str = "website_admin", client_name: str | None = None, user_id: int | None = None) -> str:
        auth = _make_auth_context(role=role, client_name=client_name, user_id=user_id)
        return json.dumps(get_overview_snapshot(auth), default=str)

    @mcp.tool()
    def get_trends(
        metric: str = "uploaded_count",
        granularity: str = "month",
        role: str = "website_admin",
        client_name: str | None = None,
        user_id: int | None = None,
    ) -> str:
        auth = _make_auth_context(role=role, client_name=client_name, user_id=user_id)
        return json.dumps(get_trends_snapshot(auth, metric=metric, granularity=granularity), default=str)

    @mcp.tool()
    def get_insights(
        surface: str = "mission-control",
        limit: int = 5,
        role: str = "website_admin",
        client_name: str | None = None,
        user_id: int | None = None,
    ) -> str:
        auth = _make_auth_context(role=role, client_name=client_name, user_id=user_id)
        return json.dumps([card.model_dump() for card in build_insights(auth, surface=surface, limit=limit)], default=str)

    return mcp
