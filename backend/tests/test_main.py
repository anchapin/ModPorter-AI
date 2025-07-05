"""
Modern test suite for ModPorter AI backend
"""

from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_health_check():
    """Test health endpoint"""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["version"] == "1.0.0"

def test_convert_endpoint_without_input():
    """Test conversion endpoint validation"""
    response = client.post("/api/convert")
    assert response.status_code == 400
    assert "must be provided" in response.json()["detail"]

def test_convert_endpoint_with_url():
    """Test conversion endpoint with URL"""
    response = client.post(
        "/api/convert",
        json={"file_id": "mock_file_id", "original_filename": "mock_mod.jar"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "job_id" in data
    assert isinstance(data["job_id"], str)
    assert data["status"] == "processing"

def test_convert_endpoint_response_structure():
    """Test that response has correct structure"""
    response = client.post(
        "/api/convert",
        json={"file_id": "mock_file_id", "original_filename": "mock_mod.jar"}
    )
    assert response.status_code == 200
    data = response.json()
    
    # Check required fields
    required_fields = [
        "job_id", "status", "message", "estimated_time"
    ]
    
    for field in required_fields:
        assert field in data, f"Missing required field: {field}"