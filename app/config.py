import json
import os
from typing import List, Optional, Union
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "Email Open Alert API"
    API_V1_STR: str = "/api/v1"
    DEBUG: bool = False
    HOST: str = "0.0.0.0"
    PORT: int = int(os.environ.get("PORT", 8000))
    BASE_URL: str = "http://localhost:8000"

    # CORS
    BACKEND_CORS_ORIGINS: Union[List[str], str] = ["*"]

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, str) and v.startswith("["):
            return json.loads(v)
        elif isinstance(v, list):
            return v
        return ["*"]

    # Database — no default so the app fails fast if DATABASE_URL is missing
    DATABASE_URL: str

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def assemble_db_url(cls, v: str) -> str:
        if not v:
            raise ValueError(
                "DATABASE_URL must be set. "
                "Set it in .env (local) or as an environment variable (production)."
            )
        # Fix dialect prefix for async support
        if v.startswith("postgres://"):
            v = v.replace("postgres://", "postgresql+asyncpg://", 1)
        elif v.startswith("postgresql://"):
            v = v.replace("postgresql://", "postgresql+asyncpg://", 1)
        # Strip SSL params from URL — they are passed via connect_args instead
        import re
        v = re.sub(r"[?&](ssl|sslmode)=[^&]*", "", v)
        # Clean up leftover ? or & at the end
        v = v.rstrip("?&")
        return v

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_ENABLED: bool = False

    # Alert Behavior
    ALERT_ON_FIRST_OPEN_ONLY: bool = False

    # Email Sending
    BREVO_API_KEY: Optional[str] = None

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


settings = Settings()
