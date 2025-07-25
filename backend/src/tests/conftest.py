import os
import sys
import pytest
from pathlib import Path
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch

# Add the src directory to the Python path
src_dir = Path(__file__).parent.parent
sys.path.insert(0, str(src_dir))

# Set testing environment variable BEFORE importing main
os.environ["TESTING"] = "true"

# Import fixtures and setup code here

@pytest.fixture
def project_root():
    """Get the project root directory for accessing test fixtures."""
    # Navigate from backend/src/tests/conftest.py to project root
    current_dir = Path(__file__).parent  # tests/
    src_dir = current_dir.parent         # src/
    backend_dir = src_dir.parent         # backend/
    project_root = backend_dir.parent    # project root
    return project_root

@pytest.fixture
def client():
    """Create a test client for the FastAPI app."""
    # For integration tests, we need the database to be properly initialized
    # Import main to create the app
    from main import app
    
    # Create TestClient - this will trigger startup events including init_db
    with TestClient(app) as test_client:
        yield test_client
