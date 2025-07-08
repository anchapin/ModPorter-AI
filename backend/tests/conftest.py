import sys
import os

# Add project root to sys.path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
import pytest_asyncio
import asyncio
from fastapi.testclient import TestClient

from src.main import app


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    asyncio.set_event_loop(loop)
    yield loop
    loop.close()


@pytest.fixture
def client():
    """Create a test client for the FastAPI app."""
    return TestClient(app)




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
