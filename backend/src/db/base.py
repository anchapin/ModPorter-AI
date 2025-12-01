from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

try:
    from src.config import settings
except ImportError:
    from src.config import settings

# Base is imported in models.py and migrations
# from .declarative_base import Base

# Configure engine based on database type
database_url = settings.database_url
print(f"Database URL being used: {database_url}")  # Debug

if database_url.startswith("sqlite"):
    # SQLite configuration - no pool settings
    async_engine = create_async_engine(
        database_url,
        echo=False,
    )
else:
    # PostgreSQL configuration - with pool settings
    # Ensure we're using asyncpg driver for async operations
    if database_url.startswith("postgresql://"):
        database_url = database_url.replace("postgresql://", "postgresql+asyncpg://")

    async_engine = create_async_engine(
        database_url,
        echo=False,
        pool_size=10,
        max_overflow=20,
    )

AsyncSessionLocal = async_sessionmaker(
    bind=async_engine, expire_on_commit=False, class_=AsyncSession
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session
