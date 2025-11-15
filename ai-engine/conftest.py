"""Global pytest configuration for ai-engine."""
import os
import sys
from pathlib import Path

# Mock magic library before any imports that might use it
sys.modules['magic'] = type(sys)('magic')
sys.modules['magic'].open = lambda *args, **kwargs: None
sys.modules['magic'].from_buffer = lambda buffer, mime=False: 'application/octet-stream' if mime else 'data'
sys.modules['magic'].from_file = lambda filename, mime=False: 'application/octet-stream' if mime else 'data'

# Add ai-engine and project root directories to Python path
ai_engine_root = Path(__file__).parent
project_root = ai_engine_root.parent
sys.path.insert(0, str(ai_engine_root))
sys.path.insert(0, str(project_root))

# Set testing environment
os.environ["TESTING"] = "true"
