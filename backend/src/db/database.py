"""
Database configuration and session management.
"""

import os
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

try:
    from src.config import settings
except ImportError:
    # Fallback for when running from different contexts
    try:
        from src.config import settings
    except ImportError:
        # Final fallback - assume config is in path
        from config import settings

# Create async engine
engine = create_async_engine(
    settings.database_url,
    echo=os.getenv("DB_ECHO", "false").lower() == "true",
    future=True
)

# Create async session factory
AsyncSessionLocal = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Get an async database session.

    Yields:
        AsyncSession: Database session
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
