import pytest
import pytest_asyncio
import asyncio
from fastapi.testclient import TestClient
from httpx import AsyncClient

from src.main import app


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def client():
    """Create a test client for the FastAPI app."""
    # Clear the in-memory database before each test
    from src.main import conversions_db, uploaded_files

    conversions_db.clear()
    uploaded_files.clear()

    # Mock the database dependency to avoid database connections in tests
    from src.db.base import get_db
    from unittest.mock import patch, AsyncMock
    
    async def mock_get_db():
        """Mock database session that doesn't connect to real database."""
        # Return a mock session that won't actually perform database operations
        from unittest.mock import AsyncMock
        
        mock_session = AsyncMock()
        
        # Configure the mock to raise an exception for database operations
        # This will trigger the fallback to in-memory storage
        mock_session.add.side_effect = Exception("Mock database error - using in-memory storage")
        mock_session.commit.side_effect = Exception("Mock database error - using in-memory storage")
        mock_session.execute.side_effect = Exception("Mock database error - using in-memory storage")
        
        yield mock_session
    
    app.dependency_overrides[get_db] = mock_get_db

    # Mock Redis cache operations
    with patch('src.main.cache') as mock_cache:
        mock_cache.set_job_status = AsyncMock()
        mock_cache.set_progress = AsyncMock()
        mock_cache.get_job_status = AsyncMock(return_value=None)
        mock_cache.update_job_status = AsyncMock()
        mock_cache.update_progress = AsyncMock()
        
        with TestClient(app) as c:
            yield c
    
    # Clean up dependency overrides
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def async_client():
    """Create an async test client for the FastAPI app."""
    from httpx import ASGITransport

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


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
