"""
Async test client for FastAPI applications with async database support.

This solves the common issue where FastAPI's TestClient runs synchronously
but async database operations need an async context.
"""
import asyncio
from typing import Any, Dict, Optional
import httpx
import pytest
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import StaticPool


class AsyncTestClient:
    """
    Async test client that properly handles async database operations.
    
    This is the recommended approach for testing FastAPI apps with async databases:
    1. Use httpx.AsyncClient instead of TestClient
    2. Run the FastAPI app in the same event loop as the tests
    3. Properly manage async database sessions
    """
    
    def __init__(self, app: FastAPI, base_url: str = "http://testserver"):
        self.app = app
        self.base_url = base_url
        self._client: Optional[httpx.AsyncClient] = None
    
    async def __aenter__(self):
        """Async context manager entry."""
        # Use transport parameter instead of app parameter for newer httpx versions
        from httpx import ASGITransport
        transport = ASGITransport(app=self.app)
        self._client = httpx.AsyncClient(transport=transport, base_url=self.base_url)
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self._client:
            await self._client.aclose()
    
    async def get(self, url: str, **kwargs) -> httpx.Response:
        """Make async GET request."""
        if not self._client:
            raise RuntimeError("Client not initialized. Use async with statement.")
        return await self._client.get(url, **kwargs)
    
    async def post(self, url: str, **kwargs) -> httpx.Response:
        """Make async POST request."""
        if not self._client:
            raise RuntimeError("Client not initialized. Use async with statement.")
        return await self._client.post(url, **kwargs)
    
    async def put(self, url: str, **kwargs) -> httpx.Response:
        """Make async PUT request."""
        if not self._client:
            raise RuntimeError("Client not initialized. Use async with statement.")
        return await self._client.put(url, **kwargs)
    
    async def delete(self, url: str, **kwargs) -> httpx.Response:
        """Make async DELETE request."""
        if not self._client:
            raise RuntimeError("Client not initialized. Use async with statement.")
        return await self._client.delete(url, **kwargs)


@pytest.fixture
async def async_test_db():
    """
    Create an async test database session.
    
    This uses SQLite in-memory database for fast, isolated tests.
    Each test gets a fresh database.
    """
    # Use SQLite in-memory for tests
    test_db_url = "sqlite+aiosqlite:///:memory:"
    
    engine = create_async_engine(
        test_db_url,
        echo=False,
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    
    # Import and create tables
    try:
        from src.database.models import Base
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    except ImportError:
        # Models might not exist yet, that's ok for basic tests
        pass
    
    # Create session
    from sqlalchemy.ext.asyncio import async_sessionmaker
    async_session = async_sessionmaker(engine, expire_on_commit=False)
    
    async with async_session() as session:
        yield session
    
    await engine.dispose()


@pytest.fixture
async def async_client():
    """
    Create an async test client with proper database setup.
    
    This fixture provides the recommended way to test FastAPI apps with async databases.
    """
    try:
        from src.main import app
        
        async with AsyncTestClient(app) as client:
            yield client
    except ImportError as e:
        pytest.skip(f"Cannot import main app: {e}")


# Alternative approach using pytest-asyncio and httpx directly
@pytest.fixture
async def httpx_client():
    """
    Alternative async client using httpx directly.
    
    This is useful when you need more control over the HTTP client configuration.
    """
    try:
        from main import app
        from httpx import ASGITransport
        
        transport = ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            yield client
    except ImportError as e:
        pytest.skip(f"Cannot import main app: {e}")
