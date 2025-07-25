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
def client():
    """Create a test client for the FastAPI app."""
    # Mock the init_db function to prevent database initialization during tests
    with patch('db.init_db.init_db', new_callable=AsyncMock) as mock_init_db:
        # Import main AFTER setting up the mock
        from main import app
        
        # Create TestClient - init_db will be mocked and won't actually run
        with TestClient(app) as test_client:
            yield test_client
