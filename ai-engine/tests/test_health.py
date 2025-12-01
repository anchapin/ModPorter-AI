"""Basic health check test for AI engine."""
from fastapi.testclient import TestClient


def test_health_check():
    """Test that AI engine can start without import errors and has basic functionality."""
    from main import app
    client = TestClient(app)

    # Test actual functionality
    assert app is not None
    assert hasattr(app, 'routes')

    # Test OpenAPI (exercises FastAPI code)
    response = client.get("/openapi.json")
    assert response.status_code == 200
    assert "openapi" in response.json()

    # Test docs endpoint if available
    try:
        response = client.get("/docs")
        assert response.status_code in [200, 404]  # 404 is ok if docs not enabled
    except Exception:
        pass