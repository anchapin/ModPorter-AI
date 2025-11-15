from fastapi.testclient import TestClient
from src.main import app
import io

client = TestClient(app)

def test_health_check():
    """
    Tests the /api/v1/health endpoint.
    """
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json() == {
        "status": "healthy",
        "version": "1.0.0",
        "timestamp": response.json()["timestamp"]  # Allow for dynamic timestamp
    }

def test_upload_file_success():
    """
    Tests the /api/v1/upload endpoint with a supported file type.
    """
    file_content = b"dummy zip content"
    file_like = io.BytesIO(file_content)
    files = {"file": ("test.zip", file_like, "application/zip")}
    response = client.post("/api/v1/upload", files=files)
    assert response.status_code == 200
    json_response = response.json()
    assert "file_id" in json_response
    assert json_response["original_filename"] == "test.zip"
    assert json_response["size"] == len(file_content)

def test_upload_file_unsupported_type():
    """
    Tests the /api/v1/upload endpoint with an unsupported file type.
    """
    file_content = b"dummy text content"
    file_like = io.BytesIO(file_content)
    files = {"file": ("test.txt", file_like, "text/plain")}
    response = client.post("/api/v1/upload", files=files)
    assert response.status_code == 400
    assert "File type .txt not supported" in response.json()["detail"]
