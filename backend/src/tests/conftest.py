import os
import sys
import pytest
from pathlib import Path
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

# Add the src directory to the Python path
src_dir = Path(__file__).parent.parent
sys.path.insert(0, str(src_dir))

# Set testing environment variable BEFORE importing main
os.environ["TESTING"] = "true"

# Set up async engine for tests
from config import settings

# Configuration depends on database type
db_url = settings.database_url
engine_kwargs = {
    "echo": False,
}

# Only add pooling parameters for PostgreSQL
if not db_url.startswith("sqlite"):
    engine_kwargs.update({
        "pool_size": 1,
        "max_overflow": 0,
        "pool_pre_ping": True,
        "pool_recycle": 3600,
        "connect_args": {
            "server_settings": {
                "application_name": "modporter_test",
            }
        }
    })

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
                from sqlalchemy import text
                async with test_engine.begin() as conn:
                    await conn.execute(text("CREATE EXTENSION IF NOT EXISTS \"pgcrypto\""))
                    await conn.execute(text("CREATE EXTENSION IF NOT EXISTS \"vector\""))
                    await conn.run_sync(Base.metadata.create_all)
            
            # Create a new event loop for this operation
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(init_test_db())
                _db_initialized = True
                print("✅ Test database initialized successfully")
            finally:
                loop.close()
        except Exception as e:
            print(f"⚠️ Warning: Database initialization failed: {e}")
            _db_initialized = False

@pytest.fixture
def project_root():
    """Get the project root directory for accessing test fixtures."""
    # Navigate from backend/src/tests/conftest.py to project root
    current_dir = Path(__file__).parent  # tests/
    src_dir = current_dir.parent         # src/
    backend_dir = src_dir.parent         # backend/
    project_root = backend_dir.parent    # project root
    return project_root

@pytest.fixture(scope="function")
async def db_session():
    """Create a database session for each test with transaction rollback."""
    async with test_engine.begin() as connection:
        session = AsyncSession(bind=connection, expire_on_commit=False)
        try:
            yield session
        finally:
            await session.close()

@pytest.fixture
def client():
    """Create a test client for the FastAPI app with clean database per test."""
    # Mock the init_db function to prevent re-initialization during TestClient startup
    with patch('db.init_db.init_db', new_callable=AsyncMock):
        # Import dependencies
        from main import app
        from db.base import get_db
        
        # Create a fresh session maker per test to avoid connection sharing
        test_session_maker = async_sessionmaker(
            bind=test_engine, 
            expire_on_commit=False, 
            class_=AsyncSession
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
