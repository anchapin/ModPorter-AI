import sys
import os
from pathlib import Path
from unittest.mock import MagicMock

# Mock problematic dependencies before any imports to prevent collection errors
# Mock neo4j to avoid import issues during test collection
neo4j_mock = MagicMock()
neo4j_exceptions_mock = MagicMock()
neo4j_exceptions_mock.ServiceUnavailable = Exception
neo4j_exceptions_mock.AuthError = Exception
neo4j_mock.exceptions = neo4j_exceptions_mock
neo4j_mock.GraphDatabase = MagicMock()
neo4j_mock.Driver = MagicMock()
neo4j_mock.Session = MagicMock()
sys.modules["neo4j"] = neo4j_mock
sys.modules["neo4j.exceptions"] = neo4j_exceptions_mock

# Apply Redis mock properly to avoid recursion issues
try:
    from tests.mocks.redis_mock import apply_redis_mock

    apply_redis_mock()
except ImportError:
    # Fallback mock if redis_mock.py is not available
    redis_mock = MagicMock()
    redis_asyncio_mock = MagicMock()
    redis_mock.asyncio = redis_asyncio_mock
    sys.modules["redis"] = redis_mock
    sys.modules["redis.asyncio"] = redis_asyncio_mock

# Mock Prometheus to avoid metric registration conflicts
prometheus_mock = MagicMock()
prometheus_mock.Counter = MagicMock()
prometheus_mock.Histogram = MagicMock()
prometheus_mock.Gauge = MagicMock()
prometheus_mock.generate_latest = MagicMock(return_value=b"# Mock Prometheus data")
sys.modules["prometheus_client"] = prometheus_mock

# Add the standard library path to the beginning of the sys.path
# to avoid name collision with the local 'types' module.
stdlib_path = str(Path(sys.executable).parent / "Lib")
sys.path.insert(0, stdlib_path)

# Add backend src to path for test imports
backend_src = Path(__file__).parent.parent / "src"
if str(backend_src) not in sys.path:
    sys.path.insert(0, str(backend_src))

# Apply test environment setup
try:
    # Try to import and apply our custom mocks if available
    from tests.mocks import setup_test_environment

    setup_test_environment()
except ImportError:
    # Fallback to basic environment setup if mocks aren't available
    os.environ["TESTING"] = "true"
    os.environ["DISABLE_REDIS"] = "true"
    os.environ["TEST_DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"

# Configure logging for tests
import logging

logging.getLogger().setLevel(logging.WARNING)  # Reduce noise during tests
