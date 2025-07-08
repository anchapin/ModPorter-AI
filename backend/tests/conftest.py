import sys
import os

# Add project root to sys.path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest
import asyncio
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool
from unittest.mock import AsyncMock, MagicMock

from src.main import app
from src.db.base import get_db
from src.db.declarative_base import Base

# Test database configuration - use SQLite in-memory for tests by default
# This ensures tests are isolated and don't require external database setup
TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL", "sqlite+aiosqlite:///:memory:")
POSTGRES_TEST_URL = os.getenv(
    "DATABASE_URL", "postgresql+asyncpg://postgres:password@localhost:5432/modporter"
)


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    asyncio.set_event_loop(loop)
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def test_engine():
    """Create a test database engine."""
    try:
        # Use SQLite for tests by default for better isolation and no external dependencies
        if TEST_DATABASE_URL.startswith("sqlite"):
            engine = create_async_engine(
                TEST_DATABASE_URL,
                echo=False,
                poolclass=StaticPool,
                connect_args={
                    "check_same_thread": False,
                },
            )
        else:
            # PostgreSQL configuration for integration tests
            engine = create_async_engine(
                TEST_DATABASE_URL,
                echo=False,
                pool_pre_ping=True,
            )

        # Create all tables
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        yield engine

        # Clean up
        await engine.dispose()
    except Exception as e:
        # If database connection fails, skip database-dependent tests
        pytest.skip(f"Database connection failed: {e}")


@pytest.fixture
async def test_db_session(test_engine):
    """Create a test database session with proper transaction handling."""
    async_session = async_sessionmaker(
        bind=test_engine, class_=AsyncSession, expire_on_commit=False
    )

    async with async_session() as session:
        # For SQLite, we don't need transaction rollback as each test gets a fresh in-memory DB
        # For PostgreSQL, we use transaction rollback for cleanup
        if TEST_DATABASE_URL.startswith("sqlite"):
            yield session
        else:
            # Start a transaction for PostgreSQL
            transaction = await session.begin()
            try:
                yield session
            finally:
                # Rollback the transaction to clean up
                await transaction.rollback()


@pytest.fixture
def mock_db_session():
    """Create a mock database session for tests that don't need real database."""
    mock_session = AsyncMock(spec=AsyncSession)
    mock_session.commit = AsyncMock()
    mock_session.rollback = AsyncMock()
    mock_session.close = AsyncMock()
    mock_session.add = MagicMock()
    mock_session.refresh = AsyncMock()

    # Mock execute to return proper results for different queries
    mock_result = AsyncMock()
    mock_result.scalar_one_or_none = AsyncMock(
        return_value=None
    )  # Return None for non-existent jobs
    mock_result.scalars = AsyncMock()
    mock_result.scalars.return_value.all = AsyncMock(
        return_value=[]
    )  # Return empty list for job listings
    mock_session.execute = AsyncMock(return_value=mock_result)

    return mock_session


@pytest.fixture
def mock_conversion_job():
    """Create a mock conversion job for testing."""
    from src.db.models import ConversionJob, JobProgress
    import uuid
    from datetime import datetime

    job_id = str(uuid.uuid4())
    mock_job = MagicMock(spec=ConversionJob)
    mock_job.id = job_id
    mock_job.status = "queued"
    mock_job.input_data = {
        "file_id": "mock-file-id",
        "original_filename": "test-mod.jar",
        "target_version": "1.20.0",
        "options": {},
    }
    mock_job.created_at = datetime.utcnow()
    mock_job.updated_at = datetime.utcnow()

    # Mock progress relationship
    mock_progress = MagicMock(spec=JobProgress)
    mock_progress.progress = 0
    mock_progress.job_id = job_id
    mock_job.progress = mock_progress

    return mock_job


@pytest.fixture
def client_with_db(test_db_session):
    """Create a test client for the FastAPI app with real test database."""

    async def override_get_db():
        yield test_db_session

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    # Clean up
    app.dependency_overrides.clear()


@pytest.fixture
def client(mock_db_session):
    """Create a test client for the FastAPI app with mocked database."""
    from unittest.mock import patch
    from src.db import crud
    import uuid
    from datetime import datetime

    # Mock CRUD functions to return proper objects instead of coroutines
    async def mock_get_job(session, job_id):
        # Return None for non-existent jobs (like the test expects)
        return None

    async def mock_create_job(session, **kwargs):
        # Create a mock job object with proper attributes
        class MockJob:
            def __init__(self):
                self.id = uuid.uuid4()
                self.status = "queued"
                self.created_at = datetime.now()
                self.updated_at = datetime.now()
                self.input_data = kwargs
                self.progress = None  # Will be set separately

        return MockJob()

    async def mock_list_jobs(session):
        return []

    async def mock_update_job_status(session, job_id, status):
        class MockJob:
            def __init__(self):
                self.id = job_id
                self.status = status
                self.created_at = datetime.now()
                self.updated_at = datetime.now()
                self.input_data = {}
                self.progress = None

        return MockJob()

    async def override_get_db():
        yield mock_db_session

    app.dependency_overrides[get_db] = override_get_db

    with patch.object(crud, "get_job", mock_get_job), patch.object(
        crud, "create_job", mock_create_job
    ), patch.object(crud, "list_jobs", mock_list_jobs), patch.object(
        crud, "update_job_status", mock_update_job_status
    ):

        with TestClient(app) as test_client:
            yield test_client

    # Clean up
    app.dependency_overrides.clear()


@pytest.fixture
def sample_mod_file():
    """Create a sample mod file for testing."""
    import io
    import zipfile

    # Create a simple zip file in memory
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w") as zip_file:
        zip_file.writestr("mod.json", '{"name": "TestMod", "version": "1.0.0"}')
        zip_file.writestr("main.java", "public class Main {}")

    zip_buffer.seek(0)
    return zip_buffer


@pytest.fixture
def mock_ai_response():
    """Mock AI service response."""
    return {
        "job_id": "test_job_123",
        "status": "completed",
        "result": {
            "converted_files": ["output.mcaddon"],
            "report": "Conversion successful",
        },
    }


@pytest.fixture
def mock_cache_service():
    """Mock cache service for testing."""
    mock_cache = AsyncMock()
    mock_cache.get_job_status.return_value = None
    mock_cache.set_job_status.return_value = None
    mock_cache.get_conversion_result.return_value = None
    mock_cache.cache_conversion_result.return_value = None
    return mock_cache


@pytest.fixture
def mock_background_tasks():
    """Mock background tasks for testing."""
    return MagicMock()


# Environment variable setup for tests
@pytest.fixture(autouse=True)
def setup_test_env():
    """Set up test environment variables."""
    # Set test environment
    os.environ["TESTING"] = "true"
    os.environ["ENVIRONMENT"] = "test"
    os.environ["PYTEST_CURRENT_TEST"] = "true"  # Skip database init in main app

    # Set database URL for tests - use SQLite by default
    os.environ["DATABASE_URL"] = TEST_DATABASE_URL

    # Set Redis URL for tests - use a mock Redis URL that will be handled by cache service
    os.environ["REDIS_URL"] = "redis://localhost:6379"

    # Disable Redis for unit tests to avoid connection issues
    os.environ["DISABLE_REDIS"] = "true"

    yield

    # Clean up - only remove if we set them
    if os.environ.get("TESTING") == "true":
        os.environ.pop("TESTING", None)
    if os.environ.get("ENVIRONMENT") == "test":
        os.environ.pop("ENVIRONMENT", None)
    # Don't remove PYTEST_CURRENT_TEST as pytest manages it
