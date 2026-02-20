"""Global pytest configuration for ai-engine."""
import os
import sys
from pathlib import Path

# Add the ai-engine directory to Python path FIRST (before project root)
# This ensures ai-engine/models is found before any other models package
ai_engine_root = Path(__file__).parent
project_root = ai_engine_root.parent

# Insert ai_engine_root first, then project_root
# We use append for project_root to ensure ai_engine_root takes precedence
sys.path.insert(0, str(ai_engine_root))
if str(project_root) not in sys.path:
    sys.path.append(str(project_root))

# Set testing environment
os.environ["TESTING"] = "true"
