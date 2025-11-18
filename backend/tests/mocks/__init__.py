"""
Mock initialization module for backend tests.

This module provides a centralized place to initialize all necessary mocks
before running tests, avoiding dependency issues with external libraries.
"""

import sys
import os
from unittest.mock import MagicMock

# Import and apply our custom mocks
from .redis_mock import apply_redis_mock

def apply_all_mocks():
    """Apply all necessary mocks for testing."""
    # Apply Redis mock to prevent connection errors
    apply_redis_mock()

    # sklearn is now properly installed, no mock needed

    # Mock other external dependencies as needed
    mock_pgvector()
    mock_magic()

    # Set environment variables for testing
    os.environ["TESTING"] = "true"
    os.environ["DISABLE_REDIS"] = "true"
    os.environ["TEST_DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"


def mock_pgvector():
    """Mock pgvector extension."""
    # Create a mock for pgvector
    mock_pgvector = MagicMock()
    mock_pgvector.sqlalchemy = MagicMock()
    mock_pgvector.sqlalchemy.VECTOR = MagicMock()

    # Add to sys.modules
    sys.modules['pgvector'] = mock_pgvector
    sys.modules['pgvector.sqlalchemy'] = mock_pgvector.sqlalchemy


def mock_magic():
    """Mock python-magic library for file type detection."""
    # Create a mock magic module
    mock_magic = MagicMock()

    # Mock the magic.open function
    mock_open = MagicMock()
    mock_open.return_value.__enter__.return_value = mock_open
    mock_open.return_value.__exit__.return_value = None

    # Mock file type detection
    mock_magic.open = lambda *args, **kwargs: mock_open
    mock_magic.from_buffer = lambda buffer, mime=False: 'application/octet-stream' if mime else 'data'
    mock_magic.from_file = lambda filename, mime=False: 'application/octet-stream' if mime else 'data'

    # Add to sys.modules
    sys.modules['magic'] = mock_magic


def setup_test_environment():
    """
    Set up the complete test environment with all mocks applied.
    Call this function at the beginning of your test suite.
    """
    apply_all_mocks()

    # Configure logging for tests
    import logging
    logging.getLogger().setLevel(logging.INFO)

    # Ensure test environment is set
    os.environ["PYTEST_CURRENT_TEST"] = "true"
