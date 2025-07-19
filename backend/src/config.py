from pydantic_settings import BaseSettings
from pydantic import Field, ConfigDict

class Settings(BaseSettings):
    model_config = ConfigDict(env_file=".env", extra="ignore")

    database_url_raw: str = Field(
        default="postgresql+asyncpg://postgres:password@localhost:5432/modporter",
        alias="DATABASE_URL",
    )
    redis_url: str = Field(default="redis://localhost:6379", alias="REDIS_URL")

    @property
    def database_url(self) -> str:
        """Convert DATABASE_URL to async format for application use"""
        return self.database_url_raw

    @property
    def sync_database_url(self) -> str:
        """Get sync database URL for migrations"""
        url = self.database_url_raw
        if url.startswith("postgresql+asyncpg://"):
            # Convert async URL to sync for migrations
            return url.replace("postgresql+asyncpg://", "postgresql://")
        return url


settings = Settings()
