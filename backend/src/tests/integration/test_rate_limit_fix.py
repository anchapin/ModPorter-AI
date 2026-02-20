import pytest
from fastapi.testclient import TestClient

def test_upload_rate_limit(client: TestClient):
    """
    Test that the upload endpoint is rate limited correctly (20 requests per minute).
    This test reproduces the issue where the rate limit was configured for the wrong path
    (/api/v1/uploads/init instead of /api/v1/upload).
    """
    # Send requests up to the intended limit (20)
    limit = 20
    for i in range(limit):
        # We send a dummy file
        files = {'file': ('test.txt', b'dummy content', 'text/plain')}
        response = client.post("/api/v1/upload", files=files)

        # We expect a success (200) or validation error (400) because .txt is not allowed
        # But rate limit check happens before endpoint logic.
        # If rate limit is hit, we get 429.
        assert response.status_code != 429, f"Request {i+1} failed with 429 unexpectedly"

    # The 21st request should fail with 429 Too Many Requests
    files = {'file': ('test.txt', b'dummy content', 'text/plain')}
    response = client.post("/api/v1/upload", files=files)

    # Assert that we get a 429 response
    # This assertion will fail if the rate limit is not applied correctly (i.e. default limit of 60 is used)
    assert response.status_code == 429, f"Rate limit not enforced on upload endpoint. expected 429, got {response.status_code}"
