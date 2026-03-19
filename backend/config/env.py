import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv


_CONFIG_DIR = Path(__file__).resolve().parent
_BACKEND_DIR = _CONFIG_DIR.parent
_PROJECT_ROOT = _BACKEND_DIR.parent

load_dotenv(_BACKEND_DIR / ".env")
load_dotenv(_PROJECT_ROOT / ".env")


@dataclass(frozen=True)
class DBConfig:
    host: str
    port: int
    user: str
    database: str
    password: str | None
    sslmode: str

    @property
    def dsn(self) -> str:
        password = f":{self.password}" if self.password else ""
        return f"postgresql://{self.user}{password}@{self.host}:{self.port}/{self.database}"


@dataclass(frozen=True)
class AIConfig:
    provider: str
    azure_endpoint: str | None
    azure_api_key: str | None
    azure_deployment: str
    azure_api_version: str

    @property
    def configured(self) -> bool:
        return bool(self.azure_endpoint and self.azure_api_key and self.azure_deployment)


@dataclass(frozen=True)
class FeatureFlags:
    mcp_enabled: bool
    labs_enabled: bool


@dataclass(frozen=True)
class AppConfig:
    port: int
    environment: str
    cors_origins: tuple[str, ...]
    jwt_secret: str | None
    jwt_expires_in: str
    db: DBConfig
    ai: AIConfig
    features: FeatureFlags


def _env(*names: str) -> str | None:
    for name in names:
        value = os.getenv(name)
        if value is not None:
            normalized = value.strip()
            if normalized:
                return normalized
    return None


def _env_bool(*names: str, default: bool = False) -> bool:
    value = _env(*names)
    if value is None:
        return default
    return value.lower() in {"1", "true", "yes", "on"}


def _split_csv(value: str | None, *, default: tuple[str, ...]) -> tuple[str, ...]:
    if not value:
        return default
    parts = tuple(part.strip() for part in value.split(",") if part.strip())
    return parts or default


@lru_cache(maxsize=1)
def get_config() -> AppConfig:
    api_port = int(_env("PORT", "API_PORT") or "4000")

    host = _env("PGHOST", "POSTGRES_HOST")
    port_raw = _env("PGPORT", "POSTGRES_PORT")
    user = _env("PGUSER", "POSTGRES_USER")
    database = _env("PGDATABASE", "POSTGRES_DB")
    password = _env("PGPASSWORD", "POSTGRES_PASSWORD") or None
    sslmode = _env("PGSSLMODE", "POSTGRES_SSLMODE", "DB_SSLMODE") or "prefer"

    if not host or not port_raw or not user or not database:
        raise RuntimeError(
            "Missing required database environment variables: PGHOST, PGPORT, PGUSER, PGDATABASE"
        )

    db = DBConfig(
        host=host,
        port=int(port_raw),
        user=user,
        database=database,
        password=password,
        sslmode=sslmode,
    )

    ai = AIConfig(
        provider=_env("AI_PROVIDER") or "azure-openai",
        azure_endpoint=_env("AZURE_OPENAI_ENDPOINT"),
        azure_api_key=_env("AZURE_OPENAI_API_KEY"),
        azure_deployment=_env("AZURE_DEPLOYMENT") or "o4-mini",
        azure_api_version=_env("AZURE_OPENAI_API_VERSION") or "2025-01-01-preview",
    )

    return AppConfig(
        port=api_port,
        environment=_env("APP_ENV", "ENVIRONMENT", "NODE_ENV") or "development",
        cors_origins=_split_csv(_env("CORS_ORIGINS"), default=("*",)),
        jwt_secret=_env("JWT_SECRET"),
        jwt_expires_in=_env("JWT_EXPIRES_IN") or "8h",
        db=db,
        ai=ai,
        features=FeatureFlags(
            mcp_enabled=_env_bool("FEATURE_MCP_ENABLED", default=True),
            labs_enabled=_env_bool("FEATURE_LABS_ENABLED", default=True),
        ),
    )
