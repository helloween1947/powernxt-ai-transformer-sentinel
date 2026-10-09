import logging
import sys
from typing import List, Union
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration loaded from environment variables and .env file."""

    # Project metadata
    PROJECT_NAME: str = "PowerNXT Transformer Sentinel API"
    VERSION: str = "0.1.0"
    ENVIRONMENT: str = "development"
    SUPPORTED_PYTHON_VERSION: str = ">=3.11, <=3.14"

    # Logging
    LOG_LEVEL: str = "INFO"

    # PostgreSQL Database URL
    # Format: postgresql+psycopg://<user>:<password>@<host>:<port>/<dbname>
    # Note: On local Windows without Docker use localhost; inside Docker Compose use hostname 'db'
    DATABASE_URL: str = "postgresql+psycopg://sentinel:sentinel_dev_pw@localhost:5433/sentinel_db"

    # CORS Origins allowed to access API
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=True,
    )

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def assemble_db_url(cls, v: str) -> str:
        """Ensure standard postgresql:// URLs use psycopg v3 dialect."""
        if isinstance(v, str) and v.startswith("postgresql://"):
            return v.replace("postgresql://", "postgresql+psycopg://", 1)
        return v

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v


settings = Settings()


def setup_logging() -> None:
    """Configures structured application logging without exposing secrets."""
    log_format = "%(asctime)s | %(levelname)-7s | %(name)s | %(message)s"
    logging.basicConfig(
        level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
        format=log_format,
        handlers=[logging.StreamHandler(sys.stdout)],
        force=True,
    )
    # Prevent noisy external loggers from spamming
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
