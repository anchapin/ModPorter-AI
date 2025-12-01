"""
Pytest configuration and fixtures for ModPorter AI tests.
"""

import os
import pytest
import sys
from pathlib import Path
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy import text

# Set test environment (pytest.ini also sets this via env section)
os.environ["TESTING"] = "true"

# Add backend src to path
backend_src = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(backend_src))


@pytest.fixture(scope="session")
def project_root():
    """Provide project root path for consistent fixture paths."""
    return Path(__file__).parent.parent


@pytest.fixture(scope="function")
async def db_session():
    """Create a test database session."""
    from src.config import settings
    from src.db.declarative_base import Base

    # Use test database
    test_db_url = settings.database_url

    # Create test engine
    engine_kwargs = {"echo": False}
    if not test_db_url.startswith("sqlite"):
        engine_kwargs.update({
            "pool_size": 1,
            "max_overflow": 0,
        })

    test_engine = create_async_engine(test_db_url, **engine_kwargs)

    # Create test session
    TestAsyncSessionLocal = async_sessionmaker(
        bind=test_engine, expire_on_commit=False, class_=AsyncSession
    )

    # Initialize test database
    async with test_engine.begin() as conn:
        if not test_db_url.startswith("sqlite"):
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS \"pgcrypto\""))
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS \"vector\""))
        await conn.run_sync(Base.metadata.create_all)

    async with TestAsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

    # Clean up database
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await test_engine.dispose()

