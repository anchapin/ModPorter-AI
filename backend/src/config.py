from pydantic_settings import BaseSettings
from pydantic import Field

class Settings(BaseSettings):
    database_url: str = Field(
        "postgresql+asyncpg://postgres:password@localhost:5432/modporter", env="DATABASE_URL"
    )
    redis_url: str = Field(
        "redis://localhost:6379", env="REDIS_URL"
    )

settings = Settings()