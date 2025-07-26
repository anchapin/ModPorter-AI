import os
import sys
import pytest
import asyncio
from pathlib import Path
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import event
from db.base import async_engine, AsyncSessionLocal

# Add the src directory to the Python path
src_dir = Path(__file__).parent.parent
sys.path.insert(0, str(src_dir))

# Set testing environment variable BEFORE importing main
os.environ["TESTING"] = "true"

# Global flag to track database initialization
_db_initialized = False

def pytest_sessionstart(session):
    """Initialize database once at the start of the test session."""
    global _db_initialized
    if not _db_initialized:
        try:
            # Run database initialization synchronously
            import asyncio
            from db.init_db import init_db
            
            # Create a new event loop for this operation
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(init_db())
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
    connection = await async_engine.connect()
    transaction = await connection.begin()
    
    session = AsyncSession(bind=connection, expire_on_commit=False)
    
    yield session
    
    await session.close()
    await transaction.rollback()
    await connection.close()

@pytest.fixture
def client():
    """Create a test client for the FastAPI app with clean database per test."""
    # Mock the init_db function to prevent re-initialization during TestClient startup
    with patch('db.init_db.init_db', new_callable=AsyncMock) as mock_init_db:
        # Import dependencies
        from main import app
        from db.base import get_db
        
        # Override the database dependency to use isolated sessions
        async def override_get_db():
            connection = await async_engine.connect()
            transaction = await connection.begin()
            session = AsyncSession(bind=connection, expire_on_commit=False)
            try:
                yield session
            finally:
                await session.close()
                await transaction.rollback()
                await connection.close()
        
        app.dependency_overrides[get_db] = override_get_db
        
        # Create TestClient - init_db will be mocked since we already initialized it
        with TestClient(app) as test_client:
            yield test_client
        
        # Clean up dependency override
        app.dependency_overrides.clear()
