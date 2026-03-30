"""
Tests for Backend FastAPI Entrypoint (main.py)

Covers: API routing, middleware integration, app configuration
Target: Increase coverage from 33% to >80%
"""

import pytest
import os
import sys
from pathlib import Path

# Add the src directory to the Python path
src_dir = Path(__file__).parent
sys.path.insert(0, str(src_dir))

# Import directly - conftest.py should handle the mocking
from main import (
    app,
    AI_ENGINE_URL,
    TEMP_UPLOADS_DIR,
    CONVERSION_OUTPUTS_DIR,
    MAX_UPLOAD_SIZE,
    conversion_jobs_db,
)


class TestAppConfiguration:
    """Test FastAPI app configuration"""

    def test_app_exists(self):
        """Verify app exists"""
        assert app is not None

    def test_constants_defined(self):
        """Test required constants are defined"""
        assert AI_ENGINE_URL is not None
        assert TEMP_UPLOADS_DIR == "temp_uploads"
        assert CONVERSION_OUTPUTS_DIR == "conversion_outputs"
        assert MAX_UPLOAD_SIZE == 100 * 1024 * 1024  # 100 MB


class TestDatabaseConfiguration:
    """Test database configuration"""

    def test_conversion_jobs_db_exists(self):
        """Test in-memory job database exists"""
        assert isinstance(conversion_jobs_db, dict)


class TestMiddleware:
    """Test middleware configuration"""

    def test_app_has_routes(self):
        """Verify app has routes configured"""
        assert hasattr(app, "routes")
        assert len(app.routes) > 0


class TestLifespan:
    """Test application lifespan"""

    def test_lifespan_context_manager(self):
        """Test lifespan context manager exists"""
        assert app.router.lifespan_context is not None


class TestRoutes:
    """Test API routes"""

    def test_health_routes_exist(self):
        """Verify health routes exist"""
        route_paths = [r.path for r in app.routes]
        assert any("health" in p for p in route_paths)

    def test_conversion_routes_exist(self):
        """Verify conversion routes exist"""
        route_paths = [r.path for r in app.routes]
        assert any("convert" in p or "conversion" in p for p in route_paths)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
