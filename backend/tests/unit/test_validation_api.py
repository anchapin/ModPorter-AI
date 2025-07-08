"""
Unit tests for the validation API endpoints
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch
import uuid
import json

from src.main import app
from src.api.validation import MockValidationAgent, ValidationRequest, ValidationJob


@pytest.fixture
def client():
    """Test client fixture"""
    return TestClient(app)


@pytest.fixture
def mock_validation_agent():
    """Mock validation agent fixture"""
    return MockValidationAgent()


@pytest.fixture
def sample_validation_request():
    """Sample validation request fixture"""
    return {
        "conversion_id": "test_conversion_123",
        "java_code_snippet": "System.out.println('Hello World');",
        "bedrock_code_snippet": "console.log('Hello World');",
        "asset_file_paths": ["textures/block.png", "sounds/click.ogg"],
        "manifest_content": {
            "format_version": 2,
            "header": {
                "name": "Test Pack",
                "description": "Test pack description",
                "uuid": str(uuid.uuid4()),
                "version": [1, 0, 0]
            },
            "modules": [{
                "type": "data",
                "uuid": str(uuid.uuid4()),
                "version": [1, 0, 0]
            }]
        }
    }


class TestValidationAPI:
    """Test class for validation API endpoints"""
    
    def test_start_validation_job_success(self, client, sample_validation_request):
        """Test successful validation job creation"""
        response = client.post("/api/v1/validation/", json=sample_validation_request)
        
        assert response.status_code == 202
        data = response.json()
        assert "job_id" in data
        assert data["conversion_id"] == sample_validation_request["conversion_id"]
        assert data["status"] in ["queued", "pending"]
    
    def test_start_validation_job_missing_conversion_id(self, client):
        """Test validation job creation with missing conversion_id"""
        request_data = {
            "java_code_snippet": "System.out.println('Hello');"
        }
        
        response = client.post("/api/v1/validation/", json=request_data)
        
        assert response.status_code == 422  # Validation error for missing required field
    
    def test_get_validation_job_status_success(self, client, sample_validation_request):
        """Test getting validation job status"""
        # First create a job
        create_response = client.post("/api/v1/validation/", json=sample_validation_request)
        job_id = create_response.json()["job_id"]
        
        # Then get its status
        response = client.get(f"/api/v1/validation/{job_id}/status")
        
        assert response.status_code == 200
        data = response.json()
        assert data["job_id"] == job_id
        assert "status" in data
    
    def test_get_validation_job_status_not_found(self, client):
        """Test getting status for non-existent job"""
        fake_job_id = str(uuid.uuid4())
        
        response = client.get(f"/api/v1/validation/{fake_job_id}/status")
        
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()
    
    @patch('time.sleep')  # Mock sleep to speed up tests
    def test_get_validation_report_success(self, mock_sleep, client, sample_validation_request):
        """Test getting validation report for completed job"""
        # Create a job
        create_response = client.post("/api/v1/validation/", json=sample_validation_request)
        job_id = create_response.json()["job_id"]
        
        # Wait a moment for background task to complete
        import time
        time.sleep(0.1)
        
        # Get the report
        response = client.get(f"/api/v1/validation/{job_id}/report")
        
        # Job might still be processing, so check for either success or 400
        if response.status_code == 200:
            data = response.json()
            assert data["validation_job_id"] == job_id
            assert "conversion_id" in data
            assert "semantic_analysis" in data
            assert "behavior_prediction" in data
            assert "asset_integrity" in data
            assert "manifest_validation" in data
            assert "overall_confidence" in data
            assert "recommendations" in data
        elif response.status_code == 400:
            # Job still processing
            assert "not yet available" in response.json()["detail"].lower()
    
    def test_get_validation_report_not_found(self, client):
        """Test getting report for non-existent job"""
        fake_job_id = str(uuid.uuid4())
        
        response = client.get(f"/api/v1/validation/{fake_job_id}/report")
        
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()


class TestMockValidationAgent:
    """Test class for the mock validation agent"""
    
    def test_validate_conversion_with_full_data(self, mock_validation_agent):
        """Test validation with complete conversion artifacts"""
        artifacts = {
            "conversion_id": "test_123",
            "java_code": "System.out.println('Hello');",
            "bedrock_code": "console.log('Hello');",
            "asset_files": ["texture.png"],
            "manifest_data": {"format_version": 2}
        }
        
        result = mock_validation_agent.validate_conversion(artifacts)
        
        assert result.conversion_id == "test_123"
        assert isinstance(result.overall_confidence, float)
        assert 0 <= result.overall_confidence <= 1
        assert isinstance(result.recommendations, list)
    
    def test_validate_conversion_minimal_data(self, mock_validation_agent):
        """Test validation with minimal data"""
        artifacts = {
            "conversion_id": "test_minimal"
        }
        
        result = mock_validation_agent.validate_conversion(artifacts)
        
        assert result.conversion_id == "test_minimal"
        assert isinstance(result.overall_confidence, float)


class TestValidationModels:
    """Test validation Pydantic models"""
    
    def test_validation_request_model(self):
        """Test ValidationRequest model validation"""
        data = {
            "conversion_id": "test_123",
            "java_code_snippet": "System.out.println('test');",
            "bedrock_code_snippet": "console.log('test');",
            "asset_file_paths": ["texture.png"],
            "manifest_content": {"format_version": 2}
        }
        
        request = ValidationRequest(**data)
        
        assert request.conversion_id == "test_123"
        assert request.java_code_snippet == "System.out.println('test');"
        assert request.asset_file_paths == ["texture.png"]
    
    def test_validation_job_model(self):
        """Test ValidationJob model"""
        job_id = str(uuid.uuid4())
        
        job = ValidationJob(
            job_id=job_id,
            conversion_id="test_conversion",
            status="pending"
        )
        
        assert job.job_id == job_id
        assert job.conversion_id == "test_conversion"
        assert job.status == "pending"
        assert job.message is None  # Optional field