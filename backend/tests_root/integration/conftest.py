"""
Pytest configuration for integration tests.
"""

import sys
import os
from pathlib import Path
from unittest.mock import AsyncMock, patch
import pytest
import httpx
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

# Set test environment
os.environ["TESTING"] = "true"

# Add backend/src to path
backend_src = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(backend_src))

@pytest.fixture(scope="function")
async def async_client():
    """Create an async test client for FastAPI app."""
    from src.config import settings
    from sqlalchemy.ext.asyncio import create_async_engine
    from sqlalchemy import text
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
    
    # Mock init_db to prevent re-initialization
    with patch('src.db.init_db.init_db', new_callable=AsyncMock):
        from main import app
        from src.db.base import get_db
        
        # Override database dependency
        async def override_get_db():
            async with TestAsyncSessionLocal() as session:
                try:
                    yield session
                except Exception:
                    await session.rollback()
                    raise
                finally:
                    await session.close()
        
        app.dependency_overrides[get_db] = override_get_db
        
        # Create async client using ASGI transport
        transport = httpx.ASGITransport(app=app)
        
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            yield client
        
        # Clean up
        app.dependency_overrides.clear()


@pytest.fixture(scope="function")
async def async_test_db():
    """Create an async database session for testing."""
    from src.config import settings
    from sqlalchemy.ext.asyncio import create_async_engine
    from sqlalchemy import text
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

    # Create and yield session
    async with TestAsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

    # Clean up
    await test_engine.dispose()
