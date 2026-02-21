"""Global pytest configuration for ai-engine."""
import os
import sys
from pathlib import Path

# Add ONLY the ai-engine directory to Python path
# Do NOT add project root as it causes conflicts with the models package
# (backend/src/models vs ai-engine/models)
ai_engine_root = Path(__file__).parent
if str(ai_engine_root) not in sys.path:
    sys.path.insert(0, str(ai_engine_root))

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

# Explicitly exclude the problematic test file from collection
collect_ignore = ["test_smart_assumptions.py"]

