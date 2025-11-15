#!/usr/bin/env python3
"""Test script to verify API modules can be imported and routers created."""

import sys
import os
from pathlib import Path

# Add src to path
src_path = Path(__file__).parent / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

def test_api_imports():
    """Test that all API modules can be imported."""
    try:
        # Test imports
        from api.knowledge_graph_fixed import router as kg_router
        print("SUCCESS: Knowledge graph API imported successfully")
        
        from api.peer_review_fixed import router as pr_router
        print("SUCCESS: Peer review API imported successfully")
        
        from api.version_compatibility_fixed import router as vc_router
        print("SUCCESS: Version compatibility API imported successfully")
        
        from api.conversion_inference_fixed import router as ci_router
        print("SUCCESS: Conversion inference API imported successfully")
        
        from api.expert_knowledge import router as ek_router
        print("SUCCESS: Expert knowledge API imported successfully")
        
        # Test FastAPI app creation
        from fastapi import FastAPI
        app = FastAPI(title="Test API")
        
        # Include routers
        app.include_router(kg_router, prefix="/api/v1/knowledge-graph", tags=["knowledge-graph"])
        app.include_router(pr_router, prefix="/api/v1/peer-review", tags=["peer-review"]) 
        app.include_router(vc_router, prefix="/api/v1/version-compatibility", tags=["version-compatibility"])
        app.include_router(ci_router, prefix="/api/v1/conversion-inference", tags=["conversion-inference"])
        app.include_router(ek_router, prefix="/api/v1/expert", tags=["expert-knowledge"])
        
        print("SUCCESS: FastAPI app created with all routers included")
        
        # Get all routes
        routes = []
        for route in app.routes:
            if hasattr(route, 'path') and hasattr(route, 'methods'):
                for method in route.methods:
                    if method != 'HEAD':  # Skip HEAD methods
                        routes.append(f"{method} {route.path}")
        
        print(f"SUCCESS: Total routes created: {len(routes)}")
        print("\nAvailable API endpoints:")
        for route in sorted(routes):
            print(f"  - {route}")
        
        return True
        
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_api_imports()
    if success:
        print("\nSUCCESS: All API modules are working correctly!")
        sys.exit(0)
    else:
        print("\nERROR: API modules have issues that need to be fixed.")
        sys.exit(1)
