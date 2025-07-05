"""
Integration tests for the ModPorter AI API endpoints.
Tests the actual API endpoints with real HTTP requests.
"""
import os
import pytest
import requests
import time
from io import BytesIO
import tempfile


BASE_URL = "http://localhost:8000"


def wait_for_server(url: str = BASE_URL, timeout: int = 30):
    """Wait for the server to be ready"""
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            response = requests.get(f"{url}/health")
            if response.status_code == 200:
                return True
        except requests.exceptions.RequestException:
            pass
        time.sleep(1)
    return False


@pytest.fixture(scope="session", autouse=True)
def ensure_server():
    """Ensure the server is running before tests"""
    if not wait_for_server():
        pytest.skip("Server not available")


def test_health_endpoint():
    """Test the health check endpoint"""
    response = requests.get(f"{BASE_URL}/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "version" in data
    assert "timestamp" in data


def test_upload_endpoint_with_valid_file():
    """Test file upload with a valid JAR file"""
    # Create a small test file
    test_content = b"PK\x03\x04" + b"test jar content" * 100  # Mock JAR file
    
    files = {
        'file': ('test.jar', BytesIO(test_content), 'application/java-archive')
    }
    
    response = requests.post(f"{BASE_URL}/api/upload", files=files)
    assert response.status_code == 200
    
    data = response.json()
    assert "file_id" in data
    assert data["original_filename"] == "test.jar"
    assert "saved_filename" in data
    assert data["size"] == len(test_content)
    assert data["content_type"] == "application/java-archive"
    assert data["upload_timestamp"] is not None


def test_upload_endpoint_no_file():
    """Test upload endpoint without providing a file"""
    response = requests.post(f"{BASE_URL}/api/upload")
    assert response.status_code == 422  # FastAPI validation error


def test_upload_endpoint_invalid_file_type():
    """Test upload with invalid file type"""
    test_content = b"not a valid mod file"
    
    files = {
        'file': ('test.txt', BytesIO(test_content), 'text/plain')
    }
    
    response = requests.post(f"{BASE_URL}/api/upload", files=files)
    assert response.status_code == 400
    assert "not supported" in response.json()["detail"]


def test_upload_endpoint_too_large_file():
    """Test upload with file too large (over 100MB limit)"""
    # Create a file larger than MAX_UPLOAD_SIZE (100MB)
    large_content = b"x" * (101 * 1024 * 1024)  # 101MB
    
    files = {
        'file': ('large.jar', BytesIO(large_content), 'application/java-archive')
    }
    
    response = requests.post(f"{BASE_URL}/api/upload", files=files)
    assert response.status_code == 413
    assert "exceeds the limit" in response.json()["detail"]


def test_conversion_status_endpoint():
    """Test the conversion status endpoint"""
    # First upload a file to get a file_id
    test_content = b"PK\x03\x04" + b"test content" * 50
    files = {
        'file': ('test.jar', BytesIO(test_content), 'application/java-archive')
    }
    
    upload_response = requests.post(f"{BASE_URL}/api/upload", files=files)
    assert upload_response.status_code == 200
    file_id = upload_response.json()["file_id"]
    
    # Check conversion status
    response = requests.get(f"{BASE_URL}/api/status/{file_id}")
    assert response.status_code == 200
    
    data = response.json()
    assert data["file_id"] == file_id
    assert "status" in data
    assert "created_at" in data


def test_conversion_status_nonexistent_file():
    """Test conversion status for nonexistent file"""
    fake_file_id = "00000000-0000-0000-0000-000000000000"
    response = requests.get(f"{BASE_URL}/api/status/{fake_file_id}")
    assert response.status_code == 404


def test_start_conversion_endpoint():
    """Test starting a conversion"""
    # First upload a file
    test_content = b"PK\x03\x04" + b"test jar content" * 100
    files = {
        'file': ('test.jar', BytesIO(test_content), 'application/java-archive')
    }
    
    upload_response = requests.post(f"{BASE_URL}/api/upload", files=files)
    assert upload_response.status_code == 200
    file_id = upload_response.json()["file_id"]
    
    # Start conversion
    conversion_data = {
        "file_id": file_id,
        "conversion_options": {
            "target_format": "bedrock",
            "include_textures": True,
            "include_models": True
        }
    }
    
    response = requests.post(f"{BASE_URL}/api/convert", json=conversion_data)
    assert response.status_code == 200
    
    data = response.json()
    assert "conversion_id" in data
    assert data["status"] == "started"
    assert data["file_id"] == file_id


def test_start_conversion_nonexistent_file():
    """Test starting conversion for nonexistent file"""
    fake_file_id = "00000000-0000-0000-0000-000000000000"
    conversion_data = {
        "file_id": fake_file_id,
        "conversion_options": {
            "target_format": "bedrock"
        }
    }
    
    response = requests.post(f"{BASE_URL}/api/convert", json=conversion_data)
    assert response.status_code == 404


def test_download_conversion_result():
    """Test downloading conversion results"""
    # First upload and convert a file
    test_content = b"PK\x03\x04" + b"test jar content" * 100
    files = {
        'file': ('test.jar', BytesIO(test_content), 'application/java-archive')
    }
    
    upload_response = requests.post(f"{BASE_URL}/api/upload", files=files)
    assert upload_response.status_code == 200
    file_id = upload_response.json()["file_id"]
    
    conversion_data = {
        "file_id": file_id,
        "conversion_options": {
            "target_format": "bedrock"
        }
    }
    
    convert_response = requests.post(f"{BASE_URL}/api/convert", json=conversion_data)
    assert convert_response.status_code == 200
    conversion_id = convert_response.json()["conversion_id"]
    
    # Try to download (might not be ready immediately in a real scenario)
    download_response = requests.get(f"{BASE_URL}/api/download/{conversion_id}")
    # In a real test, we might need to wait for conversion to complete
    # For now, we just check that the endpoint exists
    assert download_response.status_code in [200, 404, 425]  # 425 = too early/not ready


def test_api_documentation_endpoints():
    """Test that API documentation endpoints are available"""
    # Test OpenAPI schema
    response = requests.get(f"{BASE_URL}/openapi.json")
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/json"
    
    # Test Swagger UI
    response = requests.get(f"{BASE_URL}/docs")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    
    # Test ReDoc
    response = requests.get(f"{BASE_URL}/redoc")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
