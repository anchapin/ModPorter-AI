import pytest
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.sql import text
from backend.src.config import settings

@pytest.mark.asyncio
async def test_supabase_connection():
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
