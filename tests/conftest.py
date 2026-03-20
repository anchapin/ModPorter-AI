"""
Pytest configuration and fixtures for ModPorter AI tests.
"""

import os
import sys
import pytest
from pathlib import Path

# Set test environment (pytest.ini also sets this via env section)
os.environ["TESTING"] = "true"

# Add ai-engine to path for imports
project_root = Path(__file__).parent.parent
ai_engine_root = project_root / "ai-engine"
if str(ai_engine_root) not in sys.path:
    sys.path.insert(0, str(ai_engine_root))

# Define project root fixture for consistent path resolution


@pytest.fixture(scope="session")
def project_root():
    """Provide project root path for consistent fixture paths."""
    return Path(__file__).parent.parent

