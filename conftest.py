"""
pytest configuration - root conftest
"""

import sys
from pathlib import Path

# DEBUG: Print when conftest is loaded
print(f"[ROOT CONFTEST] Loading at {Path(__file__).resolve()}")
print(f"[ROOT CONFTEST] Current sys.path: {sys.path[:3]}")

# Add ai-engine to path for module imports
project_root = Path(__file__).parent.resolve()
ai_engine_path = project_root / "ai-engine"

if ai_engine_path.exists():
    if str(ai_engine_path) not in sys.path:
        sys.path.insert(0, str(ai_engine_path))
        print(f"[ROOT CONFTEST] Added ai-engine to sys.path: {ai_engine_path}")

# Add backend to path
backend_path = project_root / "backend" / "src"
if backend_path.exists():
    if str(backend_path) not in sys.path:
        sys.path.insert(0, str(backend_path))
        print(f"[ROOT CONFTEST] Added backend/src to sys.path: {backend_path}")

print(f"[ROOT CONFTEST] Final sys.path: {sys.path[:5]}")
