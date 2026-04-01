"""Global pytest configuration for ai-engine."""

import os
import sys
from pathlib import Path

# Add ONLY the ai-engine directory to Python path
# Do NOT add project root as it causes conflicts with the models package
# (backend/src/models vs ai-engine/models)
ai_engine_root = Path(__file__).parent

# Remove ai-engine if it's already in sys.path to ensure it's at the front
if str(ai_engine_root) in sys.path:
    sys.path.remove(str(ai_engine_root))

# Insert ai-engine at the FRONT of sys.path to ensure models import resolves correctly
sys.path.insert(0, str(ai_engine_root))

# Also remove backend/src from sys.path if present to prevent conflicts
backend_src = ai_engine_root.parent / "backend" / "src"
backend_src_str = str(backend_src.resolve())
if backend_src_str in sys.path:
    sys.path.remove(backend_src_str)

# Remove backend/src from sys.path to prevent package conflicts
backend_src_path = str(ai_engine_root.parent / "backend" / "src")
if backend_src_path in sys.path:
    sys.path.remove(backend_src_path)

# Ensure ai-engine is at the front of sys.path
if str(ai_engine_root) in sys.path:
    sys.path.remove(str(ai_engine_root))
    sys.path.insert(0, str(ai_engine_root))

# Set testing environment
os.environ["TESTING"] = "true"

# Load test fixtures
# NOTE: Use relative import for fixtures to work from both ai-engine and root test runs
# pytest_plugins expects module paths, not relative paths
# This is commented out for now as it causes issues with fixture discovery
# Instead, conftest.py in tests/fixtures/__init__.py will handle fixture imports
# pytest_plugins = [
#     "tests.fixtures.search_fixtures",
# ]

# Explicitly exclude the problematic test file from collection
collect_ignore = ["test_smart_assumptions.py"]
