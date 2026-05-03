"""
Integration test configuration with real services.

This conftest provides fixtures for tests that run against real services
(PostgreSQL, Redis, etc.) when USE_REAL_SERVICES=1 is set.

Usage:
    USE_REAL_SERVICES=1 pytest src/tests/integration/test_real_*.py -v
"""

import os
import pytest

# Check if real services should be used
USE_REAL_SERVICES = os.getenv("USE_REAL_SERVICES", "0") == "1"
REAL_DB_URL = os.getenv(
    "TEST_DATABASE_URL", "postgresql+asyncpg://postgres:password@localhost:5436/modporter_test"
)
REAL_REDIS_URL = os.getenv("TEST_REDIS_URL", "redis://localhost:6381/0")
REAL_AI_ENGINE_URL = os.getenv("TEST_AI_ENGINE_URL", "http://localhost:8080")


def pytest_configure(config):
    """Register markers for real-service tests."""
    config.addinivalue_line(
        "markers", "real_service: tests that require real service instances (postgres, redis, etc.)"
    )


# ============================================================================
# Skip Logic - Auto-skip real-service tests unless USE_REAL_SERVICES=1
# ============================================================================


def pytest_collection_modifyitems(config, items):
    """Auto-skip real-service tests unless USE_REAL_SERVICES=1."""
    if not USE_REAL_SERVICES:
        skip_real = pytest.mark.skip(
            reason="Set USE_REAL_SERVICES=1 to run real-service integration tests"
        )
        for item in items:
            if "real_service" in item.keywords:
                item.add_marker(skip_real)


# ============================================================================
# Real Service Fixtures (only loaded when USE_REAL_SERVICES=1)
# ============================================================================


@pytest.fixture(scope="session")
def real_postgres_available():
    """Check if real PostgreSQL is available."""
    if not USE_REAL_SERVICES:
        return False
    try:
        import asyncpg
        import asyncio

        async def check():
            try:
                conn = await asyncpg.connect(REAL_DB_URL, timeout=5)
                await conn.close()
                return True
            except Exception:
                return False

        return asyncio.get_event_loop().run_until_complete(check())
    except Exception:
        return False


@pytest.fixture(scope="session")
def real_redis_available():
    """Check if real Redis is available."""
    if not USE_REAL_SERVICES:
        return False
    try:
        import redis

        client = redis.Redis.from_url(REAL_REDIS_URL, socket_connect_timeout=5)
        client.ping()
        return True
    except Exception:
        return False


@pytest.fixture(scope="session")
def real_postgres_url():
    """Return the real PostgreSQL connection URL."""
    return REAL_DB_URL


@pytest.fixture(scope="session")
def real_redis_url():
    """Return the real Redis connection URL."""
    return REAL_REDIS_URL


@pytest.fixture(scope="session")
def real_ai_engine_url():
    """Return the real AI Engine URL."""
    return REAL_AI_ENGINE_URL


# ============================================================================
# Real Database Fixtures - function scoped for proper async cleanup
# ============================================================================


@pytest.fixture
async def real_db_engine():
    """
    Create a real async engine connected to PostgreSQL.
    """
    if not USE_REAL_SERVICES:
        pytest.skip("USE_REAL_SERVICES not enabled")

    try:
        from sqlalchemy.ext.asyncio import create_async_engine
        from sqlalchemy import text

        engine = create_async_engine(
            REAL_DB_URL,
            echo=False,
            pool_size=5,
            max_overflow=10,
            pool_pre_ping=True,
        )

        # Verify connection and create tables
        async with engine.begin() as conn:
            await conn.execute(text("SELECT 1"))
            # Create extensions for PostgreSQL
            await conn.execute(text('CREATE EXTENSION IF NOT EXISTS "pgcrypto"'))
            await conn.execute(text('CREATE EXTENSION IF NOT EXISTS "vector"'))
            # Create all tables
            from db.declarative_base import Base

            await conn.run_sync(Base.metadata.create_all)

        yield engine

        await engine.dispose()
    except ImportError:
        pytest.skip("asyncpg not installed")
    except Exception as e:
        pytest.skip(f"PostgreSQL not available: {e}")


@pytest.fixture
async def real_db_session(real_db_engine):
    """
    Provide a database session connected to real PostgreSQL.
    """
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

    session_maker = async_sessionmaker(
        bind=real_db_engine,
        expire_on_commit=False,
        class_=AsyncSession,
    )

    async with session_maker() as session:
        try:
            yield session
        finally:
            await session.rollback()
            await session.close()


# ============================================================================
# Real Redis Fixtures
# ============================================================================


@pytest.fixture
async def real_redis():
    """
    Provide a Redis client connected to real Redis.
    """
    if not USE_REAL_SERVICES:
        pytest.skip("USE_REAL_SERVICES not enabled")

    try:
        import redis.asyncio as aioredis

        client = aioredis.from_url(
            REAL_REDIS_URL,
            decode_responses=True,
        )

        yield client

        # Flush for isolation
        await client.flushdb()
        await client.close()
    except Exception as e:
        pytest.skip(f"Redis not available: {e}")


# ============================================================================
# Real Rate Limiter Fixture
# ============================================================================


@pytest.fixture
async def real_rate_limiter():
    """
    Provide a rate limiter backed by real Redis.
    """
    if not USE_REAL_SERVICES:
        pytest.skip("USE_REAL_SERVICES not enabled")

    try:
        from services.rate_limiter import RateLimiter
        from services.rate_limiter import RateLimitConfig

        config = RateLimitConfig(
            requests_per_minute=60,
            requests_per_hour=1000,
            burst_size=10,
        )

        limiter = RateLimiter(config=config, redis_url=REAL_REDIS_URL)
        await limiter.initialize()

        yield limiter

        # Cleanup
        if limiter._redis:
            await limiter._redis.flushdb()
            await limiter._redis.close()
    except Exception as e:
        pytest.skip(f"Could not create rate limiter: {e}")


@pytest.fixture
async def real_redis_cache():
    """
    Provide a cache client backed by real Redis.
    """
    if not USE_REAL_SERVICES:
        pytest.skip("USE_REAL_SERVICES not enabled")

    try:
        import redis.asyncio as aioredis

        client = aioredis.from_url(
            REAL_REDIS_URL,
            decode_responses=True,
        )

        yield client

        await client.flushdb()
        await client.close()
    except Exception as e:
        pytest.skip(f"Redis cache not available: {e}")
