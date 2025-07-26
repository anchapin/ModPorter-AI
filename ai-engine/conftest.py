"""Global pytest configuration for ai-engine."""
import os
import sys
from pathlib import Path

# Add the ai-engine/src directory to Python path
ai_engine_src = Path(__file__).parent / "src"
sys.path.insert(0, str(ai_engine_src))

# Set testing environment
os.environ["TESTING"] = "true"
