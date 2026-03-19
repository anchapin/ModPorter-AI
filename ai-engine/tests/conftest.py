"""
pytest configuration for ai-engine tests
"""

import sys
import os
from pathlib import Path

# Add ai-engine directory to path
ai_engine_dir = Path(__file__).parent.parent.resolve()
if str(ai_engine_dir) not in sys.path:
    sys.path.insert(0, str(ai_engine_dir))

# Add backend src to path for cross-module imports
backend_src = ai_engine_dir.parent / "backend" / "src"
if backend_src.exists() and str(backend_src) not in sys.path:
    sys.path.insert(0, str(backend_src))
