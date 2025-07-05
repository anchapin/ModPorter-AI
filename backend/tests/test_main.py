"""
Modern test suite for ModPorter AI backend
"""

from fastapi.testclient import TestClient
from src.main import app

client = TestClient(app)

def test_health_check():
    """Test health endpoint"""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["version"] == "1.0.0"

def test_convert_endpoint_without_input():
    """Test conversion endpoint validation"""
    response = client.post("/api/v1/convert")
    assert response.status_code == 400
    assert "must be provided" in response.json()["detail"]

def test_convert_endpoint_with_url():
    """Test conversion endpoint with URL"""
    response = client.post(
        "/api/v1/convert",
        params={"mod_url": "https://example.com/mod.jar"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["conversion_id"] == "mock-conversion-id"
    assert data["status"] == "processing"

def test_convert_endpoint_response_structure():
    """Test that response has correct structure"""
    response = client.post(
        "/api/v1/convert",
        params={"mod_url": "https://example.com/mod.jar"}
    )
    assert response.status_code == 200
    data = response.json()
    
    # Check required fields
    required_fields = [
        "conversion_id", "status", "overall_success_rate",
        "converted_mods", "failed_mods", "smart_assumptions_applied",
        "detailed_report"
    ]
    
    for field in required_fields:
        assert field in data, f"Missing required field: {field}"