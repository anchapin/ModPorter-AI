from pydantic_settings import BaseSettings
from pydantic import Field, ConfigDict

class Settings(BaseSettings):
    model_config = ConfigDict(env_file=".env", extra='ignore')

    database_url_raw: str = Field(default="postgresql+asyncpg://postgres:password@localhost:5432/modporter", alias="DATABASE_URL")
    redis_url: str = Field(default="redis://localhost:6379", alias="REDIS_URL")
    openai_api_key: str = Field(alias="OPENAI_API_KEY")
    anthropic_api_key: str = Field(alias="ANTHROPIC_API_KEY")
    debug: bool = Field(alias="DEBUG")
    log_level: str = Field(alias="LOG_LEVEL")
    allowed_origins: str = Field(alias="ALLOWED_ORIGINS")
    vite_api_url: str = Field(alias="VITE_API_URL")
    max_file_size: str = Field(alias="MAX_FILE_SIZE")
    max_conversion_time: int = Field(alias="MAX_CONVERSION_TIME")
    rate_limit_per_minute: int = Field(alias="RATE_LIMIT_PER_MINUTE")
    rate_limit_per_hour: int = Field(alias="RATE_LIMIT_PER_HOUR")

    @property
    def database_url(self) -> str:
        """Convert DATABASE_URL to async format for application use"""
        url = self.database_url_raw
        if url.startswith("postgresql://"):
            return url.replace("postgresql://", "postgresql+asyncpg://")
        return url

    @property
    def sync_database_url(self) -> str:
        """Get sync database URL for migrations"""
        url = self.database_url_raw
        if url.startswith("postgresql+asyncpg://"):
            return url.replace("postgresql+asyncpg://", "postgresql://")
        return url

settings = Settings()
