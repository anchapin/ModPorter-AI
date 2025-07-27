"""Global pytest configuration for ai-engine."""
import os
import sys
from pathlib import Path

# Add the ai-engine and project root directories to Python path
ai_engine_root = Path(__file__).parent
project_root = ai_engine_root.parent
sys.path.insert(0, str(ai_engine_root))
sys.path.insert(0, str(project_root))

# Set testing environment
os.environ["TESTING"] = "true"
