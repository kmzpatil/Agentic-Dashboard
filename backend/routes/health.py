from fastapi import APIRouter

from backend.assistant.service import ensure_assistant_tables
from backend.config.env import get_config
from backend.contracts import HealthStatus, ServiceStatus
from backend.db.pool import query


router = APIRouter()

REQUIRED_TABLES = (
    "public.raw_videos",
    "public.created_assets",
    "public.published_posts",
    "public.users",
    "public.app_users",
    "public.conversations",
)


@router.get("", response_model=HealthStatus, include_in_schema=False)
@router.get("/", response_model=HealthStatus)
def health_check():
    config = get_config()

    database_ok = False
    missing_tables: list[str] = []
    database_error: str | None = None

    try:
        query("SELECT 1")
        for table_name in REQUIRED_TABLES:
            result = query("SELECT to_regclass($1) AS table_name", [table_name])
            if not result.rows or not result.rows[0].get("table_name"):
                missing_tables.append(table_name.split(".")[-1])
        database_ok = not missing_tables
    except Exception as error:
        database_error = str(error)

    assistant_ok = False
    assistant_error = None
    try:
        ensure_assistant_tables()
        assistant_ok = config.ai.configured
        if not assistant_ok:
            assistant_error = "AI provider is not configured"
    except Exception as error:
        assistant_error = str(error)

    services = {
        "database": ServiceStatus(
            ok=database_ok,
            detail="Primary analytics database ready" if database_ok else "Database setup incomplete",
            error=database_error,
            missing_tables=missing_tables,
            database=config.db.database,
        ),
        "ai": ServiceStatus(
            ok=config.ai.configured,
            detail=config.ai.provider,
            configured=config.ai.configured,
            error=None if config.ai.configured else "Missing Azure OpenAI configuration",
        ),
        "assistant": ServiceStatus(
            ok=assistant_ok,
            detail="ATLAS runtime ready" if assistant_ok else "ATLAS degraded",
            configured=config.ai.configured,
            error=assistant_error,
        ),
        "agent": ServiceStatus(
            ok=assistant_ok,
            detail="Compatibility shim active" if assistant_ok else "Compatibility shim degraded",
            configured=config.ai.configured,
            error=assistant_error,
        ),
        "mcp": ServiceStatus(
            ok=config.features.mcp_enabled,
            detail="Mounted at /mcp" if config.features.mcp_enabled else "Disabled",
            configured=config.features.mcp_enabled,
        ),
        "bootstrap": ServiceStatus(
            ok=not missing_tables,
            detail="Seeded demo tables available" if not missing_tables else "Seed/bootstrap required",
            missing_tables=missing_tables,
        ),
    }
    return HealthStatus(ok=all(service.ok for service in services.values()), services=services)
