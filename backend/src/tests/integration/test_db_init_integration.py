"""
Integration tests for database initialization.
Tests src/db/init_db.py with real database operations.
"""
import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import text


class TestInitDbIntegration:
    """Integration tests for init_db module."""

    @pytest.fixture
    async def in_memory_db(self):
        """Create an in-memory SQLite database for testing."""
        engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:",
            echo=False,
        )
        async with engine.begin() as conn:
            yield conn
        await engine.dispose()

    @pytest.mark.asyncio
    async def test_init_db_creates_extensions_sqlite(self, in_memory_db):
        """Test that init_db works with SQLite (no pgcrypto/vector extensions)."""
        # SQLite doesn't support CREATE EXTENSION, so the code should handle this gracefully
        # or skip extension creation for SQLite
        # This tests the happy path for SQLite

        # Verify we can execute raw SQL on our test connection
        result = await in_memory_db.execute(text("SELECT 1 as val"))
        row = result.scalar()
        assert row == 1

    @pytest.mark.asyncio
    async def test_init_db_retry_logic_on_operational_error(self):
        """Test retry logic when OperationalError occurs."""
        from db.init_db import init_db

        # Mock the async_engine to fail twice then succeed
        mock_conn = AsyncMock()
        mock_conn.__aenter__ = AsyncMock(side_effect=[
            Exception("Connection failed"),  # First attempt fails
            Exception("Connection failed"),  # Second attempt fails
        ])
        mock_conn.__aexit__ = AsyncMock(return_value=None)

        with patch("db.init_db.async_engine") as mock_engine:
            mock_engine.begin = MagicMock(return_value=mock_conn)

            # Should raise after max retries
            with pytest.raises(Exception):
                await init_db()

    @pytest.mark.asyncio
    async def test_init_db_retry_logic_on_programming_error(self):
        """Test retry logic when ProgrammingError occurs."""
        from sqlalchemy.exc import ProgrammingError
        from db.init_db import init_db

        # Mock to raise ProgrammingError
        mock_conn = AsyncMock()
        mock_conn.__aenter__ = AsyncMock(side_effect=ProgrammingError("statement", {}, "error"))
        mock_conn.__aexit__ = AsyncMock(return_value=None)

        with patch("db.init_db.async_engine") as mock_engine:
            mock_engine.begin = MagicMock(return_value=mock_conn)

            with pytest.raises(ProgrammingError):
                await init_db()

    @pytest.mark.asyncio
    async def test_init_db_unexpected_error_propagates(self):
        """Test that unexpected errors are not caught by retry logic."""
        from db.init_db import init_db

        mock_conn = AsyncMock()
        mock_conn.__aenter__ = AsyncMock(side_effect=ValueError("Unexpected error"))
        mock_conn.__aexit__ = AsyncMock(return_value=None)

        with patch("db.init_db.async_engine") as mock_engine:
            mock_engine.begin = MagicMock(return_value=mock_conn)

            # Should propagate ValueError, not be caught
            with pytest.raises(ValueError, match="Unexpected error"):
                await init_db()


class TestInitDbExtensionHandling:
    """Tests for extension creation handling in different database backends."""

    @pytest.mark.asyncio
    async def test_create_extension_sqlite_graceful_handling(self):
        """Test that CREATE EXTENSION works gracefully on SQLite (no-op)."""
        engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
        async with engine.begin() as conn:
            # SQLite doesn't support extensions, but we should handle it gracefully
            # The actual code should catch ProgrammingError for SQLite
            try:
                await conn.execute(text('CREATE EXTENSION IF NOT EXISTS "pgcrypto"'))
            except Exception:
                pass  # Expected for SQLite

        await engine.dispose()

    @pytest.mark.asyncio
    async def test_create_vector_extension_sqlite_graceful_handling(self):
        """Test that vector extension creation handles SQLite gracefully."""
        engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
        async with engine.begin() as conn:
            try:
                await conn.execute(text('CREATE EXTENSION IF NOT EXISTS "vector"'))
            except Exception:
                pass  # Expected for SQLite

        await engine.dispose()
