from pydantic_settings import BaseSettings
from pydantic import Field
import os

class Settings(BaseSettings):
    database_url_raw: str = Field(
        "postgresql+asyncpg://postgres:password@localhost:5432/modporter", env="DATABASE_URL"
    )
    redis_url: str = Field(
        "redis://localhost:6379", env="REDIS_URL"
    )

    @property
    def database_url(self) -> str:
        """Convert DATABASE_URL to async format for application use"""
        url = self.database_url_raw
        if url.startswith("postgresql://"):
            # Convert sync URL to async for application use
            return url.replace("postgresql://", "postgresql+asyncpg://")
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