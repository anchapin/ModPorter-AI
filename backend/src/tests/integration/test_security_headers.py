import pytest
from fastapi.testclient import TestClient

def test_security_headers_presence(client: TestClient):
    """
    Test that security headers are present in the response.
    """
    response = client.get("/api/v1/health")
    assert response.status_code == 200

    headers = response.headers
    assert headers.get("X-Content-Type-Options") == "nosniff"
    assert headers.get("X-Frame-Options") == "DENY"
    assert headers.get("X-XSS-Protection") == "1; mode=block"
    assert headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"

def test_security_headers_on_404(client: TestClient):
    """
    Test that security headers are present even on error responses.
    """
    response = client.get("/api/v1/non-existent-endpoint")
    assert response.status_code == 404

    headers = response.headers
    assert headers.get("X-Content-Type-Options") == "nosniff"
    assert headers.get("X-Frame-Options") == "DENY"
