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

# Set testing environment
os.environ["TESTING"] = "true"
