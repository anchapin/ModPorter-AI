from fastapi.testclient import TestClient


def test_security_headers_presence(client: TestClient):
    """
    Test that security headers are present in the response.

    The deprecated X-XSS-Protection header was intentionally removed (PR #1421 /
    issue #1419) and replaced by Permissions-Policy.
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

    # Check for Referrer-Policy
    assert "referrer-policy" in headers
    assert headers["referrer-policy"] == "strict-origin-when-cross-origin"

    # Check for Permissions-Policy (replaces deprecated X-XSS-Protection)
    assert "permissions-policy" in headers
    permissions_value = headers["permissions-policy"]
    for feature in (
        "camera=()",
        "microphone=()",
        "geolocation=()",
        "payment=()",
        "usb=()",
        "accelerometer=()",
        "gyroscope=()",
    ):
        assert feature in permissions_value, f"Missing {feature} in {permissions_value}"

    # Regression: deprecated X-XSS-Protection header must NOT be present
    assert "x-xss-protection" not in headers
