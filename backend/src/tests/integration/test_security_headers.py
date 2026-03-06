import pytest
from fastapi.testclient import TestClient

def test_security_headers_presence(client: TestClient):
    """
    Test that security headers are present in the response.
    """
    response = client.get("/api/v1/health")
    assert response.status_code == 200

    headers = response.headers

    # Check for X-Content-Type-Options
    assert "x-content-type-options" in headers
    assert headers["x-content-type-options"] == "nosniff"

    # Check for X-Frame-Options
    assert "x-frame-options" in headers
    assert headers["x-frame-options"] == "DENY"

    # Check for X-XSS-Protection
    assert "x-xss-protection" in headers
    assert headers["x-xss-protection"] == "1; mode=block"

    # Check for Referrer-Policy
    assert "referrer-policy" in headers
    assert headers["referrer-policy"] == "strict-origin-when-cross-origin"
