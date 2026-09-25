from functools import lru_cache
from pathlib import Path
from typing import Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """All configuration comes from environment variables (or a .env file).

    `backend/.env` takes precedence over the project-root `.env`, so a local
    developer override can coexist with the docker-compose environment.
    """

    model_config = SettingsConfigDict(
        env_file=("../.env", ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=True,
    )

    # Application
    APP_NAME: str = "Face ID Attendance"
    ENVIRONMENT: Literal["development", "test", "production"] = "development"
    DEBUG: bool = False
    FRONTEND_URL: str = "http://localhost:5173"

    # Database (async SQLAlchemy URL, e.g. postgresql+asyncpg://user:pass@host:5432/db)
    DATABASE_URL: str
    DATABASE_ECHO: bool = False

    # Authentication
    JWT_SECRET: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Company defaults (used once, when the settings row is first created; HR edits them afterwards)
    COMPANY_NAME: str = "My Company"
    COMPANY_TIMEZONE: str = "UTC"

    # File storage (profile photos, generated PDFs)
    STORAGE_PATH: Path = Path("storage")
    MAX_PHOTO_SIZE_BYTES: int = 2 * 1024 * 1024
    MAX_LETTER_ATTACHMENT_SIZE_BYTES: int = 5 * 1024 * 1024

    @field_validator("JWT_SECRET")
    @classmethod
    def _secret_length(cls, value: str) -> str:
        if len(value) < 16:
            raise ValueError("must be at least 16 characters long")
        return value

    @field_validator("COMPANY_TIMEZONE")
    @classmethod
    def _valid_timezone(cls, value: str) -> str:
        try:
            ZoneInfo(value)
        except ZoneInfoNotFoundError as exc:
            raise ValueError(f"unknown IANA timezone: {value}") from exc
        return value

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()
