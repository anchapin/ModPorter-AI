from pydantic_settings import BaseSettings
from pydantic import Field, ConfigDict
import os


class Settings(BaseSettings):
    model_config = ConfigDict(env_file="../.env", extra="ignore")

    database_url_raw: str = Field(
        default="postgresql://INVALID_CONFIG",
        alias="DATABASE_URL",
    )
    redis_url: str = Field(default="redis://localhost:6379", alias="REDIS_URL")

    @property
    def database_url(self) -> str:
        """Convert DATABASE_URL to async format for application use"""
        # Use test database if in testing mode
        if os.getenv("TESTING") == "true":
            # Default to SQLite for testing to avoid connection issues
            test_db_url = os.getenv("TEST_DATABASE_URL", "sqlite+aiosqlite:///:memory:")
            return test_db_url
        url = self.database_url_raw
        # Convert postgresql:// to postgresql+asyncpg:// for async SQLAlchemy
        if url.startswith("postgresql://"):
            return url.replace("postgresql://", "postgresql+asyncpg://", 1)
        return url

    @property
    def sync_database_url(self) -> str:
        """Get sync database URL for migrations"""
        url = self.database_url_raw
        if url.startswith("postgresql+asyncpg://"):
            # Convert async URL to sync for migrations
            return url.replace("postgresql+asyncpg://", "postgresql://")
        return url


settings = Settings()
