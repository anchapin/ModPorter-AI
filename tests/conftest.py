"""
Pytest configuration and fixtures for ModPorter AI tests.
"""

import os
import sys
import pytest
from pathlib import Path

# Set test environment
os.environ["TESTING"] = "true"

# Add backend/src directory to Python path for imports
project_root = Path(__file__).parent.parent
backend_src_path = project_root / "backend" / "src"
sys.path.insert(0, str(backend_src_path))

# Set working directory to backend/src for relative imports
original_cwd = os.getcwd()
os.chdir(str(backend_src_path))

@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """Setup test environment and cleanup after all tests."""
    # Setup
    yield
    # Cleanup: restore original working directory
    os.chdir(original_cwd)