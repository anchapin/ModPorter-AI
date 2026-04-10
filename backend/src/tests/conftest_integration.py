"""
Integration test configuration with real services.

This conftest provides fixtures for tests that run against real services
(PostgreSQL, Redis, etc.) when USE_REAL_SERVICES=1 is set.

Usage:
    USE_REAL_SERVICES=1 pytest tests/integration/test_real_services.py -v

The fixture discovery order ensures this conftest is NOT loaded for regular
unit tests (which should use mocks and be fast).
"""

import os
import sys
import pytest

# Check if real services should be used
USE_REAL_SERVICES = os.getenv("USE_REAL_SERVICES", "0") == "1"
REAL_DB_URL = os.getenv(
    "TEST_DATABASE_URL", "postgresql://postgres:password@localhost:5433/modporter_test"
)
REAL_REDIS_URL = os.getenv("TEST_REDIS_URL", "redis://localhost:6379/0")
REAL_AI_ENGINE_URL = os.getenv("TEST_AI_ENGINE_URL", "http://localhost:8080")


def pytest_configure(config):
    """Register markers for real-service tests."""
    config.addinivalue_line(
        "markers", "real_service: tests that require real service instances (postgres, redis, etc.)"
    )
    config.addinivalue_line(
        "markers", "integration: integration tests that may use real or mocked services"
    )


# Skip all tests in this conftest's directory if not running with USE_REAL_SERVICES
# unless explicitly marked with --run-real-services
def pytest_collection_modifyitems(config, items):
    """Auto-skip real-service tests unless USE_REAL_SERVICES=1."""
    if not USE_REAL_SERVICES:
        skip_real = pytest.mark.skip(
            reason="Set USE_REAL_SERVICES=1 to run real-service integration tests"
        )
        for item in items:
            if "real_service" in item.keywords or "integration" in item.keywords:
                # Only skip if not explicitly running with --run-real-services
                if not config.getoption("--run-real-services", default=False):
                    item.add_marker(skip_real)


def pytest_addoption(parser):
    """Add --run-real-services flag."""
    parser.addoption(
        "--run-real-services",
        action="store_true",
        default=False,
        help="Run tests that require real services (PostgreSQL, Redis, etc.)",
    )


# ============================================================================
# Real Service Fixtures
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
# Real Database Fixtures (for when real PostgreSQL is available)
# ============================================================================


@pytest.fixture(scope="session")
async def real_db_engine():
    """
    Create a real async engine connected to PostgreSQL.

    Only available when USE_REAL_SERVICES=1 and PostgreSQL is reachable.
    """
    if not USE_REAL_SERVICES:
        pytest.skip("USE_REAL_SERVICES not enabled")

    try:
        from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
        from sqlalchemy import text

        engine = create_async_engine(
            REAL_DB_URL,
            echo=False,
            pool_size=5,
            max_overflow=10,
            pool_pre_ping=True,
        )

        # Verify connection
        async with engine.begin() as conn:
            await conn.execute(text("SELECT 1"))

        yield engine

        await engine.dispose()
    except ImportError:
        pytest.skip("asyncpg not installed")
    except Exception as e:
        pytest.skip(f"PostgreSQL not available: {e}")


@pytest.fixture(scope="session")
async def real_db_session_maker(real_db_engine):
    """Create a session maker for the real database."""
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

    return async_sessionmaker(
        bind=real_db_engine,
        expire_on_commit=False,
        class_=AsyncSession,
    )


@pytest.fixture
async def real_db_session(real_db_session_maker):
    """
    Provide a database session connected to real PostgreSQL.

    Each test gets a session. The session is rolled back after the test
    to ensure isolation.
    """
    async with real_db_session_maker() as session:
        try:
            yield session
        finally:
            await session.rollback()
            await session.close()


# ============================================================================
# Real Redis Fixtures
# ============================================================================


@pytest.fixture(scope="session")
def real_redis_client():
    """
    Create a real Redis client.

    Only available when USE_REAL_SERVICES=1 and Redis is reachable.
    """
    if not USE_REAL_SERVICES:
        pytest.skip("USE_REAL_SERVICES not enabled")

    try:
        import redis.asyncio as aioredis

        client = aioredis.from_url(
            REAL_REDIS_URL,
            decode_responses=True,
            socket_connect_timeout=5,
        )

        return client
    except Exception as e:
        pytest.skip(f"Redis not available: {e}")


@pytest.fixture
async def real_redis():
    """
    Provide a Redis client connected to real Redis.

    The Redis is flushed after each test to ensure isolation.
    """
    import redis.asyncio as aioredis

    client = aioredis.from_url(
        REAL_REDIS_URL,
        decode_responses=True,
    )

    try:
        yield client
    finally:
        # Flush all keys after test for isolation
        await client.flushdb()
        await client.close()


# ============================================================================
# Real Service Test Client (FastAPI with real backend)
# ============================================================================


@pytest.fixture
async def real_service_client(real_db_session_maker):
    """
    Create a TestClient with real database backend.

    This uses the real PostgreSQL database instead of SQLite mocks.
    """
    from fastapi.testclient import TestClient
    from unittest.mock import patch, AsyncMock
    import os

    # Set testing mode with real DB
    os.environ["TESTING"] = "true"

    # Import app
    with patch("db.init_db.init_db", new_callable=AsyncMock):
        from src.main import app
        from db.base import get_db

        # Override database dependency with real sessions
        async def override_get_db():
            async with real_db_session_maker() as session:
                try:
                    yield session
                except Exception:
                    await session.rollback()
                    raise
                finally:
                    await session.close()

        app.dependency_overrides[get_db] = override_get_db

        with TestClient(app) as client:
            yield client

        app.dependency_overrides.clear()


# ============================================================================
# Service-Specific Real Test Fixtures
# ============================================================================


@pytest.fixture
async def real_rate_limiter():
    """
    Provide a rate limiter backed by real Redis.

    This tests actual rate limiting behavior against Redis,
    not mocked in-memory state.
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

        # Cleanup: flush rate limit data
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


# ============================================================================
# AI Engine Contract Test Fixtures
# ============================================================================


@pytest.fixture(scope="session")
def ai_engine_mock_server():
    """
    Start a mock AI Engine server for contract testing.

    When AI_ENGINE_MOCK=1, this provides a mock that returns
    valid response shapes without calling the real model.
    """
    if not USE_REAL_SERVICES and os.getenv("AI_ENGINE_MOCK", "0") != "1":
        pytest.skip("AI engine mock not enabled")

    # For contract tests, we just verify the mock server responds
    # In real usage, you'd start a separate process here
    # For now, we provide the URL configuration
    yield REAL_AI_ENGINE_URL


@pytest.fixture
async def real_conversion_with_redis():
    """
    Test a full conversion workflow with real Redis for job queue.

    This exercises the real conversion pipeline with Redis-backed
    task queue instead of mocked queues.
    """
    if not USE_REAL_SERVICES:
        pytest.skip("USE_REAL_SERVICES not enabled")

    # This would set up:
    # 1. Real PostgreSQL for job storage
    # 2. Real Redis for task queue
    # 3. Mock AI engine (for contract testing)
    # 4. Real file processing

    pytest.skip("Full real-service conversion test not yet implemented")
