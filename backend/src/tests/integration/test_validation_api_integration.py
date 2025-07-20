"""
Integration tests for the validation API endpoints
Tests the full flow including background task execution
"""

import pytest
import time
from fastapi.testclient import TestClient
from unittest.mock import patch
import uuid

from src.main import app
from src.api.validation import (
    validation_jobs,
    validation_reports,
    _validation_jobs_lock,
    _validation_reports_lock,
)
from backend.src.api.validation_constants import ValidationJobStatus, ValidationMessages


@pytest.fixture
def client():
    """Test client fixture"""
    return TestClient(app)


@pytest.fixture
def sample_validation_request():
    """Sample validation request fixture"""
    return {
        "conversion_id": "integration_test_123",
        "java_code_snippet": "System.out.println('Hello World');",
        "bedrock_code_snippet": "console.log('Hello World');",
        "asset_file_paths": ["textures/block.png", "sounds/click.ogg"],
        "manifest_content": {
            "format_version": 2,
            "header": {
                "name": "Integration Test Pack",
                "description": "Test pack for integration testing",
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


class TestValidationAPIIntegration:
    """Integration tests for validation API endpoints"""

    def test_full_validation_workflow(self, client, sample_validation_request):
        """Test complete validation workflow from job creation to report retrieval"""
        # Step 1: Create validation job
        create_response = client.post(
            "/api/v1/validation/", json=sample_validation_request
        )
        assert create_response.status_code == 202

        create_data = create_response.json()
        job_id = create_data["job_id"]
        assert (
            create_data["conversion_id"] == sample_validation_request["conversion_id"]
        )
        assert create_data["status"] == ValidationJobStatus.QUEUED

        # Step 2: Check initial status
        status_response = client.get(f"/api/v1/validation/{job_id}/status")
        assert status_response.status_code == 200

        status_data = status_response.json()
        assert status_data["job_id"] == job_id
        # Status could be QUEUED, PROCESSING, or COMPLETED depending on timing
        assert status_data["status"] in [
            ValidationJobStatus.QUEUED,
            ValidationJobStatus.PROCESSING,
            ValidationJobStatus.COMPLETED,
        ]

        # Step 3: Wait for background task to complete
        max_wait_time = 5  # seconds
        start_time = time.time()
        final_status = None

        while (time.time() - start_time) < max_wait_time:
            status_response = client.get(f"/api/v1/validation/{job_id}/status")
            status_data = status_response.json()
            final_status = status_data["status"]

            if final_status == ValidationJobStatus.COMPLETED:
                break
            elif final_status == ValidationJobStatus.FAILED:
                pytest.fail(
                    f"Validation job failed: {status_data.get('message', 'Unknown error')}"
                )

            time.sleep(0.1)

        assert (
            final_status == ValidationJobStatus.COMPLETED
        ), f"Job did not complete in time. Final status: {final_status}"

        # Step 4: Retrieve validation report
        report_response = client.get(f"/api/v1/validation/{job_id}/report")
        assert report_response.status_code == 200

        report_data = report_response.json()
        assert report_data["validation_job_id"] == job_id
        assert (
            report_data["conversion_id"] == sample_validation_request["conversion_id"]
        )
        assert "semantic_analysis" in report_data
        assert "behavior_prediction" in report_data
        assert "asset_integrity" in report_data
        assert "manifest_validation" in report_data
        assert "overall_confidence" in report_data
        assert "recommendations" in report_data
        assert "retrieved_at" in report_data

        # Verify report structure
        assert isinstance(report_data["semantic_analysis"], dict)
        assert isinstance(report_data["behavior_prediction"], dict)
        assert isinstance(report_data["asset_integrity"], dict)
        assert isinstance(report_data["manifest_validation"], dict)
        assert isinstance(report_data["overall_confidence"], float)
        assert isinstance(report_data["recommendations"], list)
        assert 0 <= report_data["overall_confidence"] <= 1

    def test_multiple_concurrent_validations(self, client):
        """Test handling of multiple concurrent validation jobs"""
        num_jobs = 3
        job_ids = []

        # Create multiple validation jobs
        for i in range(num_jobs):
            request_data = {
                "conversion_id": f"concurrent_test_{i}",
                "java_code_snippet": f"System.out.println('Test {i}');",
                "bedrock_code_snippet": f"console.log('Test {i}');",
                "asset_file_paths": [f"textures/block_{i}.png"],
            }

            response = client.post("/api/v1/validation/", json=request_data)
            assert response.status_code == 202
            job_ids.append(response.json()["job_id"])

        # Wait for all jobs to complete
        max_wait_time = 10  # seconds
        start_time = time.time()

        while (time.time() - start_time) < max_wait_time:
            completed_jobs = 0
            failed_jobs = 0

            for job_id in job_ids:
                status_response = client.get(f"/api/v1/validation/{job_id}/status")
                status = status_response.json()["status"]

                if status == ValidationJobStatus.COMPLETED:
                    completed_jobs += 1
                elif status == ValidationJobStatus.FAILED:
                    failed_jobs += 1

            if completed_jobs == num_jobs:
                break
            elif failed_jobs > 0:
                pytest.fail("One or more validation jobs failed")

            time.sleep(0.1)

        assert (
            completed_jobs == num_jobs
        ), f"Only {completed_jobs} out of {num_jobs} jobs completed"

        # Verify all reports can be retrieved
        for job_id in job_ids:
            report_response = client.get(f"/api/v1/validation/{job_id}/report")
            assert report_response.status_code == 200

            report_data = report_response.json()
            assert report_data["validation_job_id"] == job_id

    def test_validation_with_complex_manifest(self, client):
        """Test validation with a complex manifest structure"""
        complex_manifest = {
            "format_version": 2,
            "header": {
                "name": "Complex Test Pack",
                "description": "A complex test pack with multiple modules",
                "uuid": str(uuid.uuid4()),
                "version": [1, 2, 3],
                "min_engine_version": [1, 19, 0],
            },
            "modules": [
                {"type": "data", "uuid": str(uuid.uuid4()), "version": [1, 0, 0]},
                {"type": "resources", "uuid": str(uuid.uuid4()), "version": [1, 0, 0]},
                {
                    "type": "script",
                    "uuid": str(uuid.uuid4()),
                    "version": [1, 0, 0],
                    "entry": "scripts/main.js",
                },
            ],
            "dependencies": [{"uuid": str(uuid.uuid4()), "version": [1, 0, 0]}],
        }

        request_data = {
            "conversion_id": "complex_manifest_test",
            "java_code_snippet": "public class ComplexMod { /* complex logic */ }",
            "bedrock_code_snippet": "// Complex Bedrock script\nclass ComplexAddon { }",
            "asset_file_paths": [
                "textures/blocks/custom_block.png",
                "textures/items/custom_item.png",
                "sounds/custom_sound.ogg",
                "models/entity/custom_entity.json",
            ],
            "manifest_content": complex_manifest,
        }

        # Create validation job
        create_response = client.post("/api/v1/validation/", json=request_data)
        assert create_response.status_code == 202
        job_id = create_response.json()["job_id"]

        # Wait for completion
        max_wait_time = 5
        start_time = time.time()

        while (time.time() - start_time) < max_wait_time:
            status_response = client.get(f"/api/v1/validation/{job_id}/status")
            status = status_response.json()["status"]

            if status == ValidationJobStatus.COMPLETED:
                break
            elif status == ValidationJobStatus.FAILED:
                pytest.fail("Validation job failed")

            time.sleep(0.1)

        # Get report
        report_response = client.get(f"/api/v1/validation/{job_id}/report")
        assert report_response.status_code == 200

        report_data = report_response.json()
        assert report_data["conversion_id"] == "complex_manifest_test"

        # Verify manifest validation handled the complex structure
        manifest_validation = report_data["manifest_validation"]
        assert isinstance(manifest_validation, dict)
        assert "is_valid" in manifest_validation
        assert "errors" in manifest_validation
        assert "warnings" in manifest_validation

    def test_validation_error_handling(self, client):
        """Test error handling in validation workflow"""
        # Test with invalid conversion_id
        request_data = {
            "conversion_id": "",  # Empty conversion_id
            "java_code_snippet": "System.out.println('Hello');",
        }

        response = client.post("/api/v1/validation/", json=request_data)
        assert response.status_code == 400
        assert ValidationMessages.CONVERSION_ID_REQUIRED in response.json()["detail"]

    def test_validation_job_persistence(self, client, sample_validation_request):
        """Test that validation jobs persist correctly in storage"""
        # Create a job
        create_response = client.post(
            "/api/v1/validation/", json=sample_validation_request
        )
        job_id = create_response.json()["job_id"]

        # Verify job is in storage
        with _validation_jobs_lock:
            assert job_id in validation_jobs
            stored_job = validation_jobs[job_id]
            assert (
                stored_job.conversion_id == sample_validation_request["conversion_id"]
            )
            # Status could be QUEUED, PROCESSING, or COMPLETED depending on timing
            assert stored_job.status in [
                ValidationJobStatus.QUEUED,
                ValidationJobStatus.PROCESSING,
                ValidationJobStatus.COMPLETED,
            ]

        # Wait for completion
        max_wait_time = 5
        start_time = time.time()

        while (time.time() - start_time) < max_wait_time:
            status_response = client.get(f"/api/v1/validation/{job_id}/status")
            if status_response.json()["status"] == ValidationJobStatus.COMPLETED:
                break
            time.sleep(0.1)

        # Verify report is in storage
        with _validation_reports_lock:
            assert job_id in validation_reports
            stored_report = validation_reports[job_id]
            assert (
                stored_report.conversion_id
                == sample_validation_request["conversion_id"]
            )

    def test_validation_with_minimal_data(self, client):
        """Test validation with minimal request data"""
        minimal_request = {"conversion_id": "minimal_integration_test"}

        # Create validation job
        create_response = client.post("/api/v1/validation/", json=minimal_request)
        assert create_response.status_code == 202
        job_id = create_response.json()["job_id"]

        # Wait for completion
        max_wait_time = 5
        start_time = time.time()

        while (time.time() - start_time) < max_wait_time:
            status_response = client.get(f"/api/v1/validation/{job_id}/status")
            if status_response.json()["status"] == ValidationJobStatus.COMPLETED:
                break
            time.sleep(0.1)

        # Get report
        report_response = client.get(f"/api/v1/validation/{job_id}/report")
        assert report_response.status_code == 200

        report_data = report_response.json()
        assert report_data["conversion_id"] == "minimal_integration_test"

        # Should still have all required fields even with minimal input
        assert "semantic_analysis" in report_data
        assert "behavior_prediction" in report_data
        assert "asset_integrity" in report_data
        assert "manifest_validation" in report_data
        assert "overall_confidence" in report_data
        assert "recommendations" in report_data

    @patch("src.api.validation.MockValidationAgent.validate_conversion")
    def test_validation_agent_error_handling(
        self, mock_validate, client, sample_validation_request
    ):
        """Test error handling when validation agent fails"""
        # Mock validation agent to raise an exception
        mock_validate.side_effect = Exception("Mock validation error")

        # Create validation job
        create_response = client.post(
            "/api/v1/validation/", json=sample_validation_request
        )
        assert create_response.status_code == 202
        job_id = create_response.json()["job_id"]

        # Wait for job to fail
        max_wait_time = 5
        start_time = time.time()

        while (time.time() - start_time) < max_wait_time:
            status_response = client.get(f"/api/v1/validation/{job_id}/status")
            status_data = status_response.json()

            if status_data["status"] == ValidationJobStatus.FAILED:
                assert ValidationMessages.JOB_FAILED in status_data["message"]
                assert "Mock validation error" in status_data["message"]
                break

            time.sleep(0.1)
        else:
            pytest.fail("Job did not fail as expected")

        # Try to get report (should fail)
        report_response = client.get(f"/api/v1/validation/{job_id}/report")
        assert report_response.status_code == 400
        assert (
            ValidationMessages.REPORT_NOT_AVAILABLE in report_response.json()["detail"]
        )
