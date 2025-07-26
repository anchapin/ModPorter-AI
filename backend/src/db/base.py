from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from config import settings

# Base is imported in models.py and migrations
# from .declarative_base import Base

# Configure engine based on database type
database_url = settings.database_url
if database_url.startswith("sqlite"):
    # SQLite configuration - no pool settings
    async_engine = create_async_engine(
        database_url,
        echo=False,
    )
else:
    # PostgreSQL configuration - with pool settings
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
