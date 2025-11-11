from pydantic_settings import BaseSettings
from pydantic import Field, ConfigDict
import os

class Settings(BaseSettings):
    model_config = ConfigDict(env_file=["../.env", "../.env.local"], extra="ignore")

    database_url_raw: str = Field(
        default="postgresql://supabase_user:supabase_password@db.supabase_project_id.supabase.co:5432/postgres",
        alias="DATABASE_URL",
    )
    redis_url: str = Field(default="redis://localhost:6379", alias="REDIS_URL")
    
    # Neo4j graph database settings
    neo4j_uri: str = Field(default="bolt://localhost:7687", alias="NEO4J_URI")
    neo4j_user: str = Field(default="neo4j", alias="NEO4J_USER")
    neo4j_password: str = Field(default="password", alias="NEO4J_PASSWORD")

    @property
    def database_url(self) -> str:
        """Convert DATABASE_URL to async format for application use"""
        # Use test database if in testing mode
        if os.getenv("TESTING") == "true":
            # Default to SQLite for testing to avoid connection issues
            # Use file-based database for testing to support table creation across connections
            test_db_url = os.getenv("TEST_DATABASE_URL", "sqlite+aiosqlite:///./test.db")
            return test_db_url
        
        # Convert to async format if needed
        url = self.database_url_raw
        if url.startswith("postgresql://"):
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
