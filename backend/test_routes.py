#!/usr/bin/env python3
"""Debug script to check if version compatibility routes are registered"""

import sys
from pathlib import Path

# Add src to path
src_dir = Path(__file__).parent / "src"
sys.path.insert(0, str(src_dir))

print(f"Src dir: {src_dir}")
print(f"Path: {sys.path[:3]}...")

try:
    from main import app
    print(f"App loaded: {app}")
    
    # Get all routes
    for route in app.routes:
        if hasattr(route, 'path'):
            print(f"Route: {route.path} -> {route.endpoint if hasattr(route, 'endpoint') else 'Unknown'}")
        elif hasattr(route, 'routes'):  # For APIRouter
            print(f"Router: {route.prefix if hasattr(route, 'prefix') else 'No prefix'}")
            for subroute in route.routes:
                print(f"  Subroute: {subroute.path} -> {subroute.endpoint if hasattr(subroute, 'endpoint') else 'Unknown'}")
except Exception as e:
    print(f"Error loading app: {e}")
    import traceback
    traceback.print_exc()
