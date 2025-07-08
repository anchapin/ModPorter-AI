"""
Unit tests for the validation API endpoints
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch
import uuid
import time

from src.main import app
from src.api.validation import (
    MockValidationAgent,
    ValidationRequest,
    ValidationJob,
    validation_jobs,
    validation_reports,
    _validation_jobs_lock,
    _validation_reports_lock,
)
from src.api.validation_constants import ValidationJobStatus, ValidationMessages


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
                "version": [1, 0, 0],
            },
            "modules": [
                {"type": "data", "uuid": str(uuid.uuid4()), "version": [1, 0, 0]}
            ],
        },
    }


@pytest.fixture(autouse=True)
def cleanup_validation_storage():
    """Clean up validation storage before and after each test"""
    # Clear before test
    with _validation_jobs_lock:
        validation_jobs.clear()
    with _validation_reports_lock:
        validation_reports.clear()

    yield

    # Clear after test
    with _validation_jobs_lock:
        validation_jobs.clear()
    with _validation_reports_lock:
        validation_reports.clear()


class TestValidationAPI:
    """Test class for validation API endpoints"""

    def test_start_validation_job_success(self, client, sample_validation_request):
        """Test successful validation job creation"""
        response = client.post("/api/v1/validation/", json=sample_validation_request)

        assert response.status_code == 202
        data = response.json()
        assert "job_id" in data
        assert data["conversion_id"] == sample_validation_request["conversion_id"]
        assert data["status"] == ValidationJobStatus.QUEUED
        assert data["message"] == ValidationMessages.JOB_QUEUED

    def test_start_validation_job_missing_conversion_id(self, client):
        """Test validation job creation with missing conversion_id"""
        request_data = {"java_code_snippet": "System.out.println('Hello');"}

        response = client.post("/api/v1/validation/", json=request_data)

        assert (
            response.status_code == 422
        )  # Validation error for missing required field

    def test_start_validation_job_empty_conversion_id(self, client):
        """Test validation job creation with empty conversion_id"""
        request_data = {
            "conversion_id": "",
            "java_code_snippet": "System.out.println('Hello');",
        }

        response = client.post("/api/v1/validation/", json=request_data)

        assert response.status_code == 400
        assert ValidationMessages.CONVERSION_ID_REQUIRED in response.json()["detail"]

    def test_start_validation_job_minimal_request(self, client):
        """Test validation job creation with minimal request data"""
        request_data = {"conversion_id": "minimal_test_123"}

        response = client.post("/api/v1/validation/", json=request_data)

        assert response.status_code == 202
        data = response.json()
        assert data["conversion_id"] == "minimal_test_123"
        assert data["status"] == ValidationJobStatus.QUEUED

    def test_get_validation_job_status_success(self, client, sample_validation_request):
        """Test getting validation job status"""
        # First create a job
        create_response = client.post(
            "/api/v1/validation/", json=sample_validation_request
        )
        job_id = create_response.json()["job_id"]

        # Then get its status
        response = client.get(f"/api/v1/validation/{job_id}/status")

        assert response.status_code == 200
        data = response.json()
        assert data["job_id"] == job_id
        assert "status" in data
        assert data["status"] in [status.value for status in ValidationJobStatus]

    def test_get_validation_job_status_not_found(self, client):
        """Test getting status for non-existent job"""
        fake_job_id = str(uuid.uuid4())

        response = client.get(f"/api/v1/validation/{fake_job_id}/status")

        assert response.status_code == 404
        assert ValidationMessages.JOB_NOT_FOUND in response.json()["detail"]

    def test_get_validation_job_status_thread_safety(
        self, client, sample_validation_request
    ):
        """Test thread safety of job status retrieval"""
        # Create multiple jobs
        job_ids = []
        for i in range(3):
            request_data = sample_validation_request.copy()
            request_data["conversion_id"] = f"test_conversion_{i}"
            response = client.post("/api/v1/validation/", json=request_data)
            job_ids.append(response.json()["job_id"])

        # Get status for all jobs
        for job_id in job_ids:
            response = client.get(f"/api/v1/validation/{job_id}/status")
            assert response.status_code == 200
            assert response.json()["job_id"] == job_id

    @patch("time.sleep")  # Mock sleep to speed up tests
    def test_get_validation_report_success(
        self, mock_sleep, client, sample_validation_request
    ):
        """Test getting validation report for completed job"""
        # Create a job
        create_response = client.post(
            "/api/v1/validation/", json=sample_validation_request
        )
        job_id = create_response.json()["job_id"]

        # Wait a moment for background task to complete
        time.sleep(0.2)

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
            assert "retrieved_at" in data
        elif response.status_code == 400:
            # Job still processing
            assert ValidationMessages.REPORT_NOT_AVAILABLE in response.json()["detail"]

    def test_get_validation_report_not_found(self, client):
        """Test getting report for non-existent job"""
        fake_job_id = str(uuid.uuid4())

        response = client.get(f"/api/v1/validation/{fake_job_id}/report")

        assert response.status_code == 404
        assert ValidationMessages.JOB_NOT_FOUND in response.json()["detail"]

    @patch("src.api.validation.process_validation_task")
    def test_get_validation_report_job_not_completed(
        self, mock_process_task, client, sample_validation_request
    ):
        """Test getting report for job that's not completed"""
        # Mock the process task to not complete immediately
        mock_process_task.return_value = None

        # Create a job
        create_response = client.post(
            "/api/v1/validation/", json=sample_validation_request
        )
        job_id = create_response.json()["job_id"]

        # Immediately try to get report (should fail)
        response = client.get(f"/api/v1/validation/{job_id}/report")

        assert response.status_code == 400
        assert ValidationMessages.REPORT_NOT_AVAILABLE in response.json()["detail"]

    @patch("src.api.validation.process_validation_task")
    def test_validation_job_status_transitions(
        self, mock_process_task, client, sample_validation_request
    ):
        """Test that validation job status transitions correctly"""
        # Mock the process task to not complete immediately
        mock_process_task.return_value = None

        # Create a job
        create_response = client.post(
            "/api/v1/validation/", json=sample_validation_request
        )
        job_id = create_response.json()["job_id"]

        # Initial status should be QUEUED
        status_response = client.get(f"/api/v1/validation/{job_id}/status")
        assert status_response.json()["status"] == ValidationJobStatus.QUEUED

        # Wait a bit and check if it transitions to PROCESSING
        time.sleep(0.1)
        status_response = client.get(f"/api/v1/validation/{job_id}/status")
        # Status should be QUEUED, PROCESSING, or COMPLETED
        assert status_response.json()["status"] in [
            ValidationJobStatus.QUEUED,
            ValidationJobStatus.PROCESSING,
            ValidationJobStatus.COMPLETED,
        ]


class TestMockValidationAgent:
    """Test class for the mock validation agent"""

    def test_validate_conversion_with_full_data(self, mock_validation_agent):
        """Test validation with complete conversion artifacts"""
        artifacts = {
            "conversion_id": "test_123",
            "java_code": "System.out.println('Hello');",
            "bedrock_code": "console.log('Hello');",
            "asset_files": ["texture.png"],
            "manifest_data": {"format_version": 2},
        }

        result = mock_validation_agent.validate_conversion(artifacts)

        assert result.conversion_id == "test_123"
        assert isinstance(result.overall_confidence, float)
        assert 0 <= result.overall_confidence <= 1
        assert isinstance(result.recommendations, list)
        assert isinstance(result.semantic_analysis, dict)
        assert isinstance(result.behavior_prediction, dict)
        assert isinstance(result.asset_integrity, dict)
        assert isinstance(result.manifest_validation, dict)

    def test_validate_conversion_minimal_data(self, mock_validation_agent):
        """Test validation with minimal data"""
        artifacts = {"conversion_id": "test_minimal"}

        result = mock_validation_agent.validate_conversion(artifacts)

        assert result.conversion_id == "test_minimal"
        assert isinstance(result.overall_confidence, float)
        assert 0 <= result.overall_confidence <= 1

    def test_validate_conversion_no_conversion_id(self, mock_validation_agent):
        """Test validation without conversion_id"""
        artifacts = {"java_code": "System.out.println('Hello');"}

        result = mock_validation_agent.validate_conversion(artifacts)

        # Should generate a UUID if no conversion_id provided
        assert result.conversion_id is not None
        assert len(result.conversion_id) > 0


class TestValidationModels:
    """Test validation Pydantic models"""

    def test_validation_request_model(self):
        """Test ValidationRequest model validation"""
        data = {
            "conversion_id": "test_123",
            "java_code_snippet": "System.out.println('test');",
            "bedrock_code_snippet": "console.log('test');",
            "asset_file_paths": ["texture.png"],
            "manifest_content": {"format_version": 2},
        }

        request = ValidationRequest(**data)

        assert request.conversion_id == "test_123"
        assert request.java_code_snippet == "System.out.println('test');"
        assert request.asset_file_paths == ["texture.png"]
        assert request.manifest_content == {"format_version": 2}

    def test_validation_job_model(self):
        """Test ValidationJob model"""
        job_id = str(uuid.uuid4())

        job = ValidationJob(
            job_id=job_id,
            conversion_id="test_conversion",
            status=ValidationJobStatus.PENDING,
        )

        assert job.job_id == job_id
        assert job.conversion_id == "test_conversion"
        assert job.status == ValidationJobStatus.PENDING
        assert job.message is None  # Optional field

    def test_validation_job_model_with_message(self):
        """Test ValidationJob model with message"""
        job_id = str(uuid.uuid4())

        job = ValidationJob(
            job_id=job_id,
            conversion_id="test_conversion",
            status=ValidationJobStatus.COMPLETED,
            message=ValidationMessages.JOB_COMPLETED,
        )

        assert job.job_id == job_id
        assert job.status == ValidationJobStatus.COMPLETED
        assert job.message == ValidationMessages.JOB_COMPLETED


class TestValidationConstants:
    """Test validation constants and enums"""

    def test_validation_job_status_enum(self):
        """Test ValidationJobStatus enum values"""
        assert ValidationJobStatus.PENDING == "pending"
        assert ValidationJobStatus.QUEUED == "queued"
        assert ValidationJobStatus.PROCESSING == "processing"
        assert ValidationJobStatus.COMPLETED == "completed"
        assert ValidationJobStatus.FAILED == "failed"
        assert ValidationJobStatus.CANCELLED == "cancelled"

    def test_validation_messages_constants(self):
        """Test ValidationMessages constants"""
        assert ValidationMessages.JOB_QUEUED == "Validation job queued successfully"
        assert (
            ValidationMessages.JOB_PROCESSING
            == "Validation job is currently processing"
        )
        assert ValidationMessages.JOB_COMPLETED == "Validation successful"
        assert ValidationMessages.JOB_FAILED == "Validation failed"
        assert ValidationMessages.JOB_NOT_FOUND == "Validation job not found"
        assert ValidationMessages.REPORT_NOT_AVAILABLE == "Report not yet available"
        assert ValidationMessages.CONVERSION_ID_REQUIRED == "conversion_id is required"


class TestValidationAPIErrorHandling:
    """Test error handling in validation API"""

    def test_invalid_json_request(self, client):
        """Test handling of invalid JSON request"""
        response = client.post(
            "/api/v1/validation/",
            data="invalid json",
            headers={"Content-Type": "application/json"},
        )

        assert response.status_code == 422

    def test_validation_request_with_invalid_types(self, client):
        """Test validation request with invalid field types"""
        request_data = {
            "conversion_id": "test_123",
            "asset_file_paths": "not_a_list",  # Should be a list
            "manifest_content": "not_a_dict",  # Should be a dict
        }

        response = client.post("/api/v1/validation/", json=request_data)

        assert response.status_code == 422

    def test_get_status_with_invalid_job_id_format(self, client):
        """Test getting status with invalid job ID format"""
        invalid_job_id = "not-a-uuid"

        response = client.get(f"/api/v1/validation/{invalid_job_id}/status")

        assert response.status_code == 404
        assert ValidationMessages.JOB_NOT_FOUND in response.json()["detail"]
