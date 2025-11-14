"""
Pytest configuration and fixtures for ModPorter AI tests.
"""

import os
import pytest
from pathlib import Path

# Set test environment (pytest.ini also sets this via env section)
os.environ["TESTING"] = "true"

# Define project root fixture for consistent path resolution


@pytest.fixture(scope="session")
def project_root():
    """Provide project root path for consistent fixture paths."""
    return Path(__file__).parent.parent

