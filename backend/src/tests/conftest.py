import os
import sys
import pytest
from pathlib import Path
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch, MagicMock
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

# Add the src directory to the Python path
src_dir = Path(__file__).parent.parent
sys.path.insert(0, str(src_dir))

# Set testing environment variable BEFORE importing main
os.environ["TESTING"] = "true"
os.environ["SECRET_KEY"] = "test-secret-key-for-testing-only-12345678901234567890"
os.environ["REFRESH_TOKEN_SECRET"] = "test-refresh-secret-key-for-testing-only-123456789012"
os.environ["JWT_SECRET_KEY"] = "test-jwt-secret-key-for-testing-only-123456789012345678"

_mock_secrets = {
    "SECRET_KEY": "test-secret-key-for-testing-only-12345678901234567890",
    "REFRESH_TOKEN_SECRET": "test-refresh-secret-key-for-testing-only-123456789012",
    "JWT_SECRET_KEY": "test-jwt-secret-key-for-testing-only-123456789012345678",
}


def _mock_get_secret(key: str) -> str:
    return _mock_secrets.get(key, "")


def pytest_configure(config):
    import sys
    from types import ModuleType
    from unittest.mock import MagicMock

    _mock_secrets_store = _mock_secrets

    def _mock_get_secret(key: str) -> str:
        return _mock_secrets_store.get(key) or ""

    # Only mock aiohttp if not available - don't mock markdown/bs4
    # since ingestion processor tests need real code
    for _mod_name, _mock_class in [
        ("aiohttp", MagicMock),
        ("aiohttp.client_exceptions", MagicMock),
    ]:
        if _mod_name not in sys.modules:
            _mod = ModuleType(_mod_name)
            sys.modules[_mod_name] = _mod

    # Note: markdown and bs4 are NOT mocked anymore - they run real code
    # This allows ingestion processor tests to use actual markdown/BeautifulSoup

    try:
        from core import secrets

        original = secrets.get_secret

        def patched(key: str) -> str:
            return _mock_secrets_store.get(key) or original(key)

        secrets.get_secret = patched
        import core.auth

        core.auth.get_secret = patched
        import security.auth

        security.auth.get_secret = patched
        security.auth.SECRET_KEY = _mock_secrets_store["SECRET_KEY"]
    except ImportError:
        pass


# Set up async engine for tests
from config import settings

from sqlalchemy import text, event
from sqlalchemy.engine import Engine

# Configuration depends on database type
db_url = settings.database_url


# Enable foreign keys for SQLite - only for the test engine
def _set_sqlite_pragma(dbapi_connection, connection_record):
    if db_url.startswith("sqlite"):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


engine_kwargs = {
    "echo": False,
}

# Only add pooling parameters for PostgreSQL
if not db_url.startswith("sqlite"):
    engine_kwargs.update(
        {
            "pool_size": 1,
            "max_overflow": 0,
            "pool_pre_ping": True,
            "pool_recycle": 3600,
            "connect_args": {
                "server_settings": {
                    "application_name": "portkit_test",
                }
            },
        }
    )

test_engine = create_async_engine(db_url, **engine_kwargs)

TestAsyncSessionLocal = async_sessionmaker(
    bind=test_engine, expire_on_commit=False, class_=AsyncSession
)

# Global flag to track database initialization
_db_initialized = False


def pytest_sessionstart(session):
    """Initialize database once at the start of the test session."""
    global _db_initialized
    if not _db_initialized:
        try:
            # Run database initialization synchronously
            import asyncio

            async def init_test_db():
                from db.declarative_base import Base
                from db import models
                from sqlalchemy import text

                async with test_engine.begin() as conn:
                    # Only add extensions for PostgreSQL
                    if not db_url.startswith("sqlite"):
                        await conn.execute(text('CREATE EXTENSION IF NOT EXISTS "pgcrypto"'))
                        await conn.execute(text('CREATE EXTENSION IF NOT EXISTS "vector"'))
                    await conn.run_sync(Base.metadata.create_all)

            # Create a new event loop for this operation
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(init_test_db())
                _db_initialized = True
                print("Test database initialized successfully")
            finally:
                loop.close()
        except Exception as e:
            print(f"Warning: Database initialization failed: {e}")
            _db_initialized = False


@pytest.fixture
def project_root():
    """Get the project root directory for accessing test fixtures."""
    # Navigate from backend/src/tests/conftest.py to project root
    current_dir = Path(__file__).parent  # tests/
    src_dir = current_dir.parent  # src/
    backend_dir = src_dir.parent  # backend/
    project_root = backend_dir.parent  # project root
    return project_root


import pytest_asyncio


@pytest_asyncio.fixture(scope="function")
async def db_session():
    """Create a database session for each test with transaction rollback."""
    async with test_engine.begin() as connection:
        session = AsyncSession(bind=connection, expire_on_commit=False)
        try:
            yield session
        finally:
            await session.close()


@pytest_asyncio.fixture(scope="function")
async def clean_db():
    """Create a clean database session that rolls back after each test."""
    async with test_engine.begin() as connection:
        session = AsyncSession(bind=connection, expire_on_commit=False)
        try:
            yield session
        finally:
            await session.rollback()
            await session.close()


@pytest_asyncio.fixture(scope="function")
async def async_client():
    """Create an async HTTP client for testing FastAPI endpoints."""
    from unittest.mock import patch, AsyncMock
    from httpx import AsyncClient, ASGITransport
    from src.main import app
    from db.base import get_db

    test_session_maker = async_sessionmaker(
        bind=test_engine, expire_on_commit=False, class_=AsyncSession
    )

    async def override_get_db():
        async with test_session_maker() as session:
            try:
                yield session
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client

    app.dependency_overrides.clear()


@pytest_asyncio.fixture(scope="function")
async def auth_headers():
    """Create authentication headers for a test user with a real database entry."""
    from datetime import timedelta
    from security.auth import create_access_token
    from db.models import User
    import uuid

    test_user_id = uuid.uuid4()
    unique_email = f"test-{uuid.uuid4().hex[:8]}@example.com"

    test_session_maker = async_sessionmaker(
        bind=test_engine, expire_on_commit=False, class_=AsyncSession
    )
    async with test_session_maker() as session:
        test_user = User(
            id=test_user_id,
            email=unique_email,
            password_hash="$2b$12$test_hash_for_testing_only",
            is_verified=True,
        )
        session.add(test_user)
        await session.commit()

    token = create_access_token(
        user_id=str(test_user_id),
        expires_delta=timedelta(hours=1),
    )

    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(autouse=True)
def reset_feature_flag_manager():
    """Reset the feature flag manager singleton between tests to prevent state pollution."""
    import os
    import services.feature_flags as ff_module

    legacy_env_vars = [
        "FEATURE_USER_ACCOUNTS",
        "FEATURE_PREMIUM_FEATURES",
        "FEATURE_API_KEYS",
    ]

    original_manager = ff_module._default_manager
    original_env = {var: os.environ.get(var) for var in legacy_env_vars}

    ff_module._default_manager = None
    for var in legacy_env_vars:
        os.environ.pop(var, None)

    yield

    ff_module._default_manager = None
    for var in legacy_env_vars:
        os.environ.pop(var, None)
    for var, val in original_env.items():
        if val is not None:
            os.environ[var] = val

    if original_manager is not None:
        ff_module._default_manager = original_manager


@pytest.fixture(autouse=True)
def reset_storage_env():
    """Reset storage and redis environment variables between tests to prevent state pollution."""
    import os

    storage_and_redis_env_vars = [
        "STORAGE_BACKEND",
        "STORAGE_PATH",
        "S3_BUCKET",
        "AWS_REGION",
        "AWS_ACCESS_KEY_ID",
        "AWS_SECRET_ACCESS_KEY",
        "REDIS_URL",
        "REDIS_MAX_CONNECTIONS",
        "REDIS_SOCKET_TIMEOUT",
        "REDIS_SOCKET_CONNECT_TIMEOUT",
        "REDIS_SOCKET_KEEPALIVE",
        "REDIS_RETRY_ON_TIMEOUT",
        "REDIS_HEALTH_CHECK_INTERVAL",
    ]

    original_env = {var: os.environ.get(var) for var in storage_and_redis_env_vars}

    for var in storage_and_redis_env_vars:
        os.environ.pop(var, None)

    yield

    for var in storage_and_redis_env_vars:
        os.environ.pop(var, None)
    for var, val in original_env.items():
        if val is not None:
            os.environ[var] = val


# clean_feature_flag_env removed - feature_flag_env fixture handles this properly
# with explicit control over when environment is set vs when it's cleaned up


@pytest.fixture
def client():
    """Create a test client for the FastAPI app with clean database per test."""
    # Mock the init_db function to prevent re-initialization during TestClient startup
    with patch("db.init_db.init_db", new_callable=AsyncMock):
        # Import dependencies from src.main (not the root main.py which lacks middleware)
        from src.main import app
        from db.base import get_db

        # from db import models

        # Create a fresh session maker per test to avoid connection sharing
        test_session_maker = async_sessionmaker(
            bind=test_engine, expire_on_commit=False, class_=AsyncSession
        )

        # Override the database dependency to use isolated sessions
        async def override_get_db():
            async with test_session_maker() as session:
                try:
                    yield session
                except Exception:
                    await session.rollback()
                    raise
                finally:
                    await session.close()

        app.dependency_overrides[get_db] = override_get_db

        # Create TestClient - init_db will be mocked since we already initialized it
        with TestClient(app) as test_client:
            yield test_client

        # Clean up dependency override
        app.dependency_overrides.clear()


@pytest.fixture(autouse=True)
def reset_rate_limiter():
    """Reset rate limiter state between tests to avoid interference."""
    from services.rate_limiter import _rate_limiter

    if _rate_limiter:
        _rate_limiter._local_state.clear()

    yield


@pytest.fixture(autouse=True)
def reset_performance_mocks():
    """Reset performance module mock state between tests to avoid cross-test pollution."""
    try:
        from api.performance import mock_benchmark_runs, mock_benchmark_reports, mock_scenarios

        # Store original state
        default_scenario = {
            "baseline_idle_001": {
                "scenario_id": "baseline_idle_001",
                "scenario_name": "Idle Performance",
                "description": "Test scenario",
                "type": "baseline",
                "duration_seconds": 300,
                "parameters": {"load_level": "none"},
                "thresholds": {"cpu": 5, "memory": 50},
            }
        }

        # Clear before test
        mock_benchmark_runs.clear()
        mock_benchmark_reports.clear()
        mock_scenarios.clear()
        mock_scenarios.update(default_scenario)

        yield

        # Clear after test
        mock_benchmark_runs.clear()
        mock_benchmark_reports.clear()
        mock_scenarios.clear()
        mock_scenarios.update(default_scenario)
    except ImportError:
        yield  # Module not available, skip


@pytest.fixture
def feature_flag_env():
    """
    Set feature flag environment variables for a test.

    Usage:
        def test_something(self, feature_flag_env):
            feature_flag_env({"FEATURE_USER_ACCOUNTS": "false"})

    This properly isolates tests from each other and resets the
    feature flag manager between tests.
    """
    import os
    import services.feature_flags as ff_module

    original_values = {}
    flag_vars = [
        "FEATURE_USER_ACCOUNTS",
        "FEATURE_PREMIUM_FEATURES",
        "FEATURE_API_KEYS",
    ]

    def _set_flags(flags: dict):
        """Set feature flag environment variables."""
        nonlocal original_values
        # Clear all feature flags first
        for var in flag_vars:
            original_values[var] = os.environ.get(var)
            os.environ.pop(var, None)

        # Set new values
        for key, value in flags.items():
            if value is not None:
                os.environ[key] = value

        # Reset manager to pick up new environment
        ff_module._default_manager = None

    return _set_flags


@pytest.fixture
def feature_flag_manager_override():
    """
    Directly override feature flags via the manager.

    Usage:
        def test_something(self, feature_flag_manager_override):
            feature_flag_manager_override({"FEATURE_USER_ACCOUNTS": "true"})

    This bypasses environment variables and directly controls
    the feature flag manager state.
    """
    import services.feature_flags as ff_module
    from services.feature_flags import FeatureFlagManager, FeatureFlag, FeatureFlagType

    original_manager = ff_module._default_manager

    def _override(flags: dict):
        """Override feature flags directly in the manager."""
        # Reset manager
        ff_module._default_manager = None
        manager = ff_module.get_feature_flag_manager()

        # Apply overrides
        for name, value in flags.items():
            flag_name = name.replace("FEATURE_", "").lower()
            is_enabled = str(value).lower() in ("true", "1", "yes", "on")
            manager.register_flag(
                name=flag_name,
                flag_type=FeatureFlagType.BOOLEAN,
                enabled=is_enabled,
            )

    yield _override

    # Restore
    ff_module._default_manager = original_manager
