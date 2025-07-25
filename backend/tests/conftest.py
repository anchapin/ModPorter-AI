"""Pytest configuration for backend tests."""
import os
import sys
import pytest
import asyncio
from pathlib import Path

# Add the backend/src directory to the Python path
backend_src = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(backend_src))

# Set testing environment variable
os.environ["TESTING"] = "true"

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(autouse=True)
def setup_test_env():
    """Set up test environment variables."""
    os.environ["TESTING"] = "true"
    os.environ["LOG_LEVEL"] = "DEBUG"
    # Use in-memory SQLite for tests
    os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
    yield
