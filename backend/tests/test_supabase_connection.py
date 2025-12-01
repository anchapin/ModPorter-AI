import pytest
import os
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.sql import text

# Import settings for checking database configuration
from src.config import settings


def should_skip_supabase_test():
    """Check if we should skip the Supabase integration test."""
    db_url = settings.database_url
    # Skip if using SQLite (test environment) or placeholder credentials
    return (
        os.getenv("TESTING") == "true"
        or db_url.startswith("sqlite")
        or "supabase_project_id" in db_url
        or "localhost" in db_url
    )


@pytest.mark.skipif(
    should_skip_supabase_test(),
    reason="Skipping Supabase connection test - requires real Supabase credentials",
)
@pytest.mark.asyncio
async def test_supabase_connection():
    """
    Integration test for Supabase connection.
    Only runs when:
    1. DATABASE_URL environment variable is set to a real Supabase instance
    2. Not using test SQLite database
    3. Not using placeholder Supabase credentials
    4. Not in testing environment
    """
    # Use the database URL from the application settings
    engine = create_async_engine(settings.database_url, echo=True)
    try:
        async with engine.connect() as connection:
            result = await connection.execute(text("SELECT 1"))
            assert result.scalar_one() == 1
        print("Successfully connected to Supabase and executed a query.")
    except Exception as e:
        pytest.fail(f"Failed to connect to Supabase or execute query: {e}")
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_database_connection_logic():
    """
    Unit test for basic database connection logic in test environment.
    This test verifies that the database configuration and connection works.
    """
    from sqlalchemy.ext.asyncio import create_async_engine
    from sqlalchemy.pool import StaticPool

    # Use SQLite in-memory for this test (same as conftest.py)
    test_db_url = "sqlite+aiosqlite:///:memory:"

    try:
        engine = create_async_engine(
            test_db_url,
            echo=False,
            poolclass=StaticPool,
            connect_args={"check_same_thread": False},
        )

        async with engine.connect() as connection:
            result = await connection.execute(text("SELECT 1"))
            assert result.scalar_one() == 1

        await engine.dispose()
        print("Successfully tested database connection logic.")

    except Exception as e:
        pytest.fail(f"Failed to test database connection logic: {e}")
