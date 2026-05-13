import uuid
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient
from main import app


@pytest.fixture
def client():
    """Test client with auth bypass (issue #1417: comparison endpoints now require auth).

    These tests assert request-validation behavior (400/422), not auth itself,
    so we override get_current_user to a stub authenticated user.
    """
    from api._authz import get_current_user

    user = MagicMock()
    user.id = "11111111-1111-4111-a111-111111111111"
    app.dependency_overrides[get_current_user] = lambda: user
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_comparison_api_endpoints_exist(client):
    """Test that comparison API endpoints exist and have proper routing."""
    # Test invalid UUID gives validation error (not 404)
    response = client.post(
        "/api/v1/comparison/",
        json={
            "conversion_id": "invalid-uuid",
            "java_mod_path": "/path/to/java/mod",
            "bedrock_addon_path": "/path/to/bedrock/addon",
        },
    )
    assert response.status_code == 400
    assert "Invalid conversion_id format" in response.json()["message"]

    # Test missing fields gives validation error
    response = client.post(
        "/api/v1/comparison/",
        json={
            "conversion_id": str(uuid.uuid4())
            # Missing required fields
        },
    )
    assert response.status_code == 422

    # Test GET endpoint exists
    response = client.get("/api/v1/comparison/invalid-uuid")
    assert response.status_code == 400
    assert "Invalid comparison_id format" in response.json()["message"]


def test_create_comparison_invalid_conversion_id(client):
    """Test comparison creation with invalid conversion ID."""
    request_data = {
        "conversion_id": "invalid-uuid",
        "java_mod_path": "/path/to/java/mod",
        "bedrock_addon_path": "/path/to/bedrock/addon",
    }

    response = client.post("/api/v1/comparison/", json=request_data)

    assert response.status_code == 400
    assert "Invalid conversion_id format" in response.json()["message"]


def test_create_comparison_missing_fields(client):
    """Test comparison creation with missing required fields."""
    incomplete_data = {
        "conversion_id": str(uuid.uuid4()),
        # Missing java_mod_path and bedrock_addon_path
    }

    response = client.post("/api/v1/comparison/", json=incomplete_data)

    assert response.status_code == 422  # Validation error


def test_get_comparison_invalid_id(client):
    """Test comparison retrieval with invalid ID."""
    response = client.get("/api/v1/comparison/invalid-uuid")

    assert response.status_code == 400
    assert "Invalid comparison_id format" in response.json()["message"]
