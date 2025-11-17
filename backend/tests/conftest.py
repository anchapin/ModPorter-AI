import sys
from pathlib import Path
from unittest.mock import MagicMock, Mock

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
sys.modules['neo4j'] = neo4j_mock
sys.modules['neo4j.exceptions'] = neo4j_exceptions_mock

# Mock redis to avoid import issues
redis_mock = MagicMock()
redis_asyncio_mock = MagicMock()
redis_mock.asyncio = redis_asyncio_mock
sys.modules['redis'] = redis_mock
sys.modules['redis.asyncio'] = redis_asyncio_mock

# Add the standard library path to the beginning of the sys.path
# to avoid name collision with the local 'types' module.
stdlib_path = str(Path(sys.executable).parent / "Lib")
sys.path.insert(0, stdlib_path)

# Add backend src to path for test imports
backend_src = Path(__file__).parent.parent / "src"
if str(backend_src) not in sys.path:
    sys.path.insert(0, str(backend_src))