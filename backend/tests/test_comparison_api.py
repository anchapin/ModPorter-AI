import uuid
from fastapi.testclient import TestClient
from src.main import app


def test_comparison_api_endpoints_exist():
    """Test that comparison API endpoints exist and have proper routing."""
    client = TestClient(app)

    # Test invalid UUID gives validation error (not 404)
    response = client.post(
        "/api/v1/comparisons/",
        json={
            "conversion_id": "invalid-uuid",
            "java_mod_path": "/path/to/java/mod",
            "bedrock_addon_path": "/path/to/bedrock/addon",
        },
    )
    assert response.status_code == 400
    assert "Invalid conversion_id format" in response.json()["detail"]

    # Test missing fields gives validation error
    response = client.post(
        "/api/v1/comparisons/",
        json={
            "conversion_id": str(uuid.uuid4())
            # Missing required fields
        },
    )
    assert response.status_code == 422

    # Test GET endpoint exists
    response = client.get("/api/v1/comparisons/invalid-uuid")
    assert response.status_code == 400
    assert "Invalid comparison_id format" in response.json()["detail"]


def test_create_comparison_invalid_conversion_id():
    """Test comparison creation with invalid conversion ID."""
    client = TestClient(app)

    request_data = {
        "conversion_id": "invalid-uuid",
        "java_mod_path": "/path/to/java/mod",
        "bedrock_addon_path": "/path/to/bedrock/addon",
    }

    response = client.post("/api/v1/comparisons/", json=request_data)

    assert response.status_code == 400
    assert "Invalid conversion_id format" in response.json()["detail"]


def test_create_comparison_missing_fields():
    """Test comparison creation with missing required fields."""
    client = TestClient(app)

    incomplete_data = {
        "conversion_id": str(uuid.uuid4()),
        # Missing java_mod_path and bedrock_addon_path
    }

    response = client.post("/api/v1/comparisons/", json=incomplete_data)

    assert response.status_code == 422  # Validation error


def test_get_comparison_invalid_id():
    """Test comparison retrieval with invalid ID."""
    client = TestClient(app)

    response = client.get("/api/v1/comparisons/invalid-uuid")

    assert response.status_code == 400
    assert "Invalid comparison_id format" in response.json()["detail"]
