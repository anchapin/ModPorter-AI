import os
import sys
import pytest
from pathlib import Path
from fastapi.testclient import TestClient

# Add the src directory to the Python path
src_dir = Path(__file__).parent.parent
sys.path.insert(0, str(src_dir))

# Set testing environment variable
os.environ["TESTING"] = "true"

# Import fixtures and setup code here

@pytest.fixture
def client():
    """Create a test client for the FastAPI app."""
    from main import app
    
    # TestClient will trigger startup events which includes init_db()
    with TestClient(app) as test_client:
        yield test_client
