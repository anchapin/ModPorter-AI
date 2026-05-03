"""
Test fixtures and configuration for backend testing with real database.

This module provides fixtures for testing with PostgreSQL database.
"""

import os
import pytest
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker


# Database URL for testing
TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL", "postgresql+asyncpg://postgres:password@localhost:5433/portkit"
)


@pytest.fixture(scope="session")
def test_db_url():
    """Provide test database URL."""
    return TEST_DATABASE_URL


@pytest.fixture(scope="session")
async def test_engine(test_db_url):
    """Create test database engine."""
    engine = create_async_engine(test_db_url, echo=False)
    yield engine
    await engine.dispose()


@pytest.fixture
async def test_db_session(test_engine):
    """Create test database session."""
    async_session = sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        yield session
        await session.rollback()
