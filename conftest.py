"""
pytest configuration - root conftest with async and fixture support
"""

import sys
import os
import asyncio
from pathlib import Path
import pytest
from unittest.mock import MagicMock, patch

# DEBUG: Print when conftest is loaded
print(f"[ROOT CONFTEST] Loading at {Path(__file__).resolve()}")
print(f"[ROOT CONFTEST] Current sys.path: {sys.path[:3]}")

# Add ai-engine to path for module imports
project_root = Path(__file__).parent.resolve()

# Add backend to path FIRST for higher priority
backend_path = project_root / "backend" / "src"
if backend_path.exists():
    if str(backend_path) not in sys.path:
        sys.path.insert(0, str(backend_path))
        print(f"[ROOT CONFTEST] Added backend/src to sys.path: {backend_path}")

# Add ai-engine to path (BEFORE project root to ensure modules are found)
ai_engine_path = project_root / "ai-engine"
if ai_engine_path.exists():
    if str(ai_engine_path) not in sys.path:
        sys.path.insert(0, str(ai_engine_path))
        print(f"[ROOT CONFTEST] Added ai-engine to sys.path: {ai_engine_path}")

# Add project root
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

print(f"[ROOT CONFTEST] Final sys.path: {sys.path[:5]}")

# ============================================================================
# PYTEST CONFIGURATION
# ============================================================================

def pytest_configure(config):
    """Configure pytest with markers and settings"""
    config.addinivalue_line(
        "markers", "asyncio: mark test as async (deselect with '-m \"not asyncio\"')"
    )
    config.addinivalue_line(
        "markers", "integration: mark test as integration test"
    )
    config.addinivalue_line(
        "markers", "unit: mark test as unit test"
    )

# ============================================================================
# ASYNC TEST SUPPORT (pytest-asyncio)
# ============================================================================

@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

# ============================================================================
# ENVIRONMENT & CONFIGURATION FIXTURES
# ============================================================================

@pytest.fixture(autouse=True)
def setup_env():
    """Setup environment variables for all tests"""
    os.environ.setdefault("SECRET_KEY", "test-secret-key-do-not-use-in-production")
    os.environ.setdefault("DEBUG", "True")
    os.environ.setdefault("TESTING", "True")
    yield
    # Cleanup (optional)

@pytest.fixture(scope="function")
def django_settings_override():
    """Fixture to override Django settings per test"""
    try:
        from django.conf import settings
        original_debug = settings.DEBUG
        settings.DEBUG = True
        yield settings
        settings.DEBUG = original_debug
    except ImportError:
        yield None

# ============================================================================
# DEPENDENCY INJECTION & SERVICE MOCKS
# ============================================================================

@pytest.fixture
def mock_service_factory():
    """Factory for creating mock services"""
    def _create_mock_service(name, **methods):
        mock = MagicMock(name=name)
        for method_name, method_impl in methods.items():
            setattr(mock, method_name, method_impl)
        return mock
    return _create_mock_service

@pytest.fixture
def mock_analytics_service():
    """Mock analytics service"""
    mock = MagicMock()
    mock.track_event = MagicMock(return_value=None)
    mock.track_feedback_submitted = MagicMock(return_value=None)
    mock.get_metrics = MagicMock(return_value={})
    return mock

@pytest.fixture
def mock_email_service():
    """Mock email service"""
    mock = MagicMock()
    mock.send_email = MagicMock(return_value=True)
    mock.send_batch = MagicMock(return_value=[])
    return mock

@pytest.fixture
def mock_storage_service():
    """Mock storage service"""
    mock = MagicMock()
    mock.upload_file = MagicMock(return_value="https://example.com/file.txt")
    mock.download_file = MagicMock(return_value=b"file content")
    mock.delete_file = MagicMock(return_value=True)
    return mock

# ============================================================================
# DATABASE FIXTURES
# ============================================================================

@pytest.fixture
def db_transaction(db):
    """Fixture for database transactions with rollback"""
    from django.db import transaction
    with transaction.atomic():
        yield db
        # Rollback happens automatically with transaction context manager

@pytest.fixture
def clean_db():
    """Clean database between tests"""
    try:
        from django.core.management import call_command
        call_command('flush', '--noinput', verbosity=0)
        yield
        call_command('flush', '--noinput', verbosity=0)
    except ImportError:
        yield

# ============================================================================
# EXTERNAL DEPENDENCY MOCKS
# ============================================================================

@pytest.fixture(autouse=True)
def mock_external_deps():
    """Mock external dependencies that might not be available"""
    # Mock modules at sys.modules level
    import sys
    old_modules = {}
    
    # Try to mock if modules don't exist
    try:
        import markdown
    except ImportError:
        sys.modules['markdown'] = MagicMock()
        old_modules['markdown'] = 'new'
    
    try:
        import bs4
    except ImportError:
        sys.modules['bs4'] = MagicMock()
        old_modules['bs4'] = 'new'
    
    try:
        import aiohttp
    except ImportError:
        sys.modules['aiohttp'] = MagicMock()
        old_modules['aiohttp'] = 'new'
    
    yield
    
    # Cleanup
    for mod_name, status in old_modules.items():
        if status == 'new':
            del sys.modules[mod_name]
