"""
app/core/config.py
Pydantic Settings — loads .env and validates all environment variables.
Implemented in: Task 3.1
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings managed by Pydantic.
    Values are automatically loaded from environment variables or a .env file.
    """

    ENVIRONMENT: str = "development"
    DATABASE_URL: str
    CLERK_JWKS_URL: str

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """
    Get cached settings instance.
    Uses lru_cache to ensure the .env file is read only once.
    """
    return Settings()  # pyright: ignore[reportCallIssue]
