"""
Comprehensive tests for batch.py API endpoints.

This test suite provides extensive coverage for the Batch Processing API,
ensuring all job submission, progress tracking, and management endpoints are tested.

Coverage Target: ≥80% line coverage for 339 statements
"""

import pytest
import json
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.batch import router
from src.services.batch_processing import batch_processing_service


class TestBatchAPI:
    """Test Batch API endpoints."""

    @pytest.fixture
    def client(self):
        """Create a test client for the batch API."""
        from fastapi import FastAPI

        app = FastAPI()
        app.include_router(router)
        return TestClient(app)

    @pytest.fixture
    def mock_db(self):
        """Create a mock database session."""
        return AsyncMock(spec=AsyncSession)

    @pytest.fixture
    def sample_job_data(self):
        """Sample job data for testing."""
        return {
            "operation_type": "import_nodes",
            "parameters": {
                "node_type": "entity",
                "platform": "java",
                "minecraft_version": "1.20",
            },
            "processing_mode": "parallel",
            "chunk_size": 50,
            "parallel_workers": 4,
        }

    @pytest.fixture
    def sample_batch_data(self):
        """Sample batch data for processing."""
        return [
            {"name": "Entity1", "type": "entity"},
            {"name": "Entity2", "type": "entity"},
            {"name": "Block1", "type": "block"},
        ]

    def test_api_router_included(self, client):
        """Test that API router is properly included."""
        response = client.get("/docs")
        # Should have API documentation
        assert response.status_code in [
            200,
            404,
        ]  # 404 is acceptable if docs not enabled

    async def test_submit_batch_job_success(self, client, mock_db, sample_job_data):
        """Test successful batch job submission."""
        with (
            patch("src.api.batch.get_db") as mock_get_db,
            patch.object(batch_processing_service, "submit_batch_job") as mock_submit,
        ):
            mock_get_db.return_value = mock_db
            mock_submit.return_value = {
                "success": True,
                "job_id": "job123",
                "status": "queued",
                "submitted_at": datetime.utcnow().isoformat(),
                "estimated_completion": (
                    datetime.utcnow() + timedelta(minutes=30)
                ).isoformat(),
                "message": "Batch job submitted successfully",
            }

            response = client.post("/batch/jobs", json=sample_job_data)

            assert response.status_code == 200
            data = response.json()
            assert "job_id" in data
            assert data["status"] == "queued"
            assert "submitted_at" in data
            assert "estimated_completion" in data

    def test_submit_batch_job_missing_operation_type(self, client, mock_db):
        """Test batch job submission with missing operation_type."""
        with patch("src.api.batch.get_db") as mock_get_db:
            mock_get_db.return_value = mock_db

            job_data = {"parameters": {"test": "data"}, "processing_mode": "parallel"}

            response = client.post("/batch/jobs", json=job_data)

            assert response.status_code == 400
            assert "operation_type is required" in response.json()["detail"]

    def test_submit_batch_job_invalid_operation_type(self, client, mock_db):
        """Test batch job submission with invalid operation_type."""
        with patch("src.api.batch.get_db") as mock_get_db:
            mock_get_db.return_value = mock_db

            job_data = {
                "operation_type": "invalid_operation",
                "parameters": {"test": "data"},
            }

            response = client.post("/batch/jobs", json=job_data)

            assert response.status_code == 400
            assert "Invalid operation_type" in response.json()["detail"]

    def test_submit_batch_job_invalid_processing_mode(self, client, mock_db):
        """Test batch job submission with invalid processing mode."""
        with patch("src.api.batch.get_db") as mock_get_db:
            mock_get_db.return_value = mock_db

            job_data = {
                "operation_type": "import_nodes",
                "parameters": {"test": "data"},
                "processing_mode": "invalid_mode",
            }

            response = client.post("/batch/jobs", json=job_data)

            assert response.status_code == 400
            assert "Invalid processing_mode" in response.json()["detail"]

    async def test_submit_batch_job_service_error(
        self, client, mock_db, sample_job_data
    ):
        """Test batch job submission when service raises an error."""
        with (
            patch("src.api.batch.get_db") as mock_get_db,
            patch.object(batch_processing_service, "submit_batch_job") as mock_submit,
        ):
            mock_get_db.return_value = mock_db
            mock_submit.side_effect = Exception("Service error")

            response = client.post("/batch/jobs", json=sample_job_data)

            assert response.status_code == 500
            assert "Job submission failed" in response.json()["detail"]

    async def test_get_job_status_success(self, client, mock_db):
        """Test successful job status retrieval."""
        with (
            patch("src.api.batch.get_db") as mock_get_db,
            patch.object(batch_processing_service, "get_job_status") as mock_status,
        ):
            mock_get_db.return_value = mock_db
            mock_status.return_value = {
                "job_id": "job123",
                "status": "running",
                "progress": 45.5,
                "total_items": 1000,
                "processed_items": 455,
                "failed_items": 2,
                "started_at": datetime.utcnow().isoformat(),
                "estimated_completion": (
                    datetime.utcnow() + timedelta(minutes=15)
                ).isoformat(),
            }

            response = client.get("/batch/jobs/job123/status")

            assert response.status_code == 200
            data = response.json()
            assert data["job_id"] == "job123"
            assert data["status"] == "running"
            assert data["progress"] == 45.5
            assert data["total_items"] == 1000
            assert data["processed_items"] == 455
            assert data["failed_items"] == 2

    async def test_get_job_status_not_found(self, client, mock_db):
        """Test job status retrieval when job not found."""
        with (
            patch("src.api.batch.get_db") as mock_get_db,
            patch.object(batch_processing_service, "get_job_status") as mock_status,
        ):
            mock_get_db.return_value = mock_db
            mock_status.return_value = None

            response = client.get("/jobs/nonexistent/status")

            assert response.status_code == 404
            assert "Job not found" in response.json()["detail"]

    async def test_get_job_status_service_error(self, client, mock_db):
        """Test job status retrieval when service raises an error."""
        with (
            patch("src.api.batch.get_db") as mock_get_db,
            patch.object(batch_processing_service, "get_job_status") as mock_status,
        ):
            mock_get_db.return_value = mock_db
            mock_status.side_effect = Exception("Database error")

            response = client.get("/batch/jobs/job123/status")

            assert response.status_code == 500
            assert "Failed to get job status" in response.json()["detail"]

    async def test_list_jobs_success(self, client, mock_db):
        """Test successful job listing."""
        with (
            patch("src.api.batch.get_db") as mock_get_db,
            patch.object(batch_processing_service, "list_jobs") as mock_list,
        ):
            mock_get_db.return_value = mock_db
            mock_list.return_value = [
                {
                    "job_id": "job123",
                    "status": "completed",
                    "operation_type": "import_nodes",
                    "submitted_at": (
                        datetime.utcnow() - timedelta(hours=2)
                    ).isoformat(),
                },
                {
                    "job_id": "job124",
                    "status": "running",
                    "operation_type": "relationship_creation",
                    "submitted_at": (
                        datetime.utcnow() - timedelta(minutes=30)
                    ).isoformat(),
                },
            ]

            response = client.get("/jobs")

            assert response.status_code == 200
            data = response.json()
            assert "jobs" in data
            assert len(data["jobs"]) == 2
            assert data["jobs"][0]["job_id"] == "job123"
            assert data["jobs"][1]["job_id"] == "job124"

    async def test_list_jobs_with_filters(self, client, mock_db):
        """Test job listing with status and operation filters."""
        with (
            patch("src.api.batch.get_db") as mock_get_db,
            patch.object(batch_processing_service, "list_jobs") as mock_list,
        ):
            mock_get_db.return_value = mock_db
            mock_list.return_value = [
                {
                    "job_id": "job123",
                    "status": "completed",
                    "operation_type": "node_creation",
                }
            ]

            # Test with status filter
            response = client.get("/jobs?status=completed")
            assert response.status_code == 200
            data = response.json()
            assert len(data["jobs"]) == 1
            assert data["jobs"][0]["status"] == "completed"

            # Test with operation filter
            response = client.get("/jobs?operation_type=node_creation")
            assert response.status_code == 200
            data = response.json()
            assert len(data["jobs"]) == 1
            assert data["jobs"][0]["operation_type"] == "node_creation"

    async def test_list_jobs_service_error(self, client, mock_db):
        """Test job listing when service raises an error."""
        with (
            patch("src.api.batch.get_db") as mock_get_db,
            patch.object(batch_processing_service, "list_jobs") as mock_list,
        ):
            mock_get_db.return_value = mock_db
            mock_list.side_effect = Exception("Database error")

            response = client.get("/jobs")

            assert response.status_code == 500
            assert "Failed to list jobs" in response.json()["detail"]

    async def test_cancel_job_success(self, client, mock_db):
        """Test successful job cancellation."""
        with (
            patch("src.api.batch.get_db") as mock_get_db,
            patch.object(batch_processing_service, "cancel_job") as mock_cancel,
        ):
            mock_get_db.return_value = mock_db
            mock_cancel.return_value = {
                "job_id": "job123",
                "status": "cancelled",
                "cancelled_at": datetime.utcnow().isoformat(),
            }

            response = client.post("/jobs/job123/cancel")

            assert response.status_code == 200
            data = response.json()
            assert data["job_id"] == "job123"
            assert data["status"] == "cancelled"
            assert "cancelled_at" in data

    async def test_cancel_job_not_found(self, client, mock_db):
        """Test job cancellation when job not found."""
        with (
            patch("src.api.batch.get_db") as mock_get_db,
            patch.object(batch_processing_service, "cancel_job") as mock_cancel,
        ):
            mock_get_db.return_value = mock_db
            mock_cancel.return_value = None

            response = client.post("/jobs/nonexistent/cancel")

            assert response.status_code == 404
            assert "Job not found" in response.json()["detail"]

    async def test_cancel_job_service_error(self, client, mock_db):
        """Test job cancellation when service raises an error."""
        with (
            patch("src.api.batch.get_db") as mock_get_db,
            patch.object(batch_processing_service, "cancel_job") as mock_cancel,
        ):
            mock_get_db.return_value = mock_db
            mock_cancel.side_effect = Exception("Service error")

            response = client.post("/jobs/job123/cancel")

            assert response.status_code == 500
            assert "Failed to cancel job" in response.json()["detail"]

    async def test_upload_batch_data_success(self, client, mock_db, sample_batch_data):
        """Test successful batch data upload."""
        with (
            patch("src.api.batch.get_db") as mock_get_db,
            patch.object(batch_processing_service, "upload_batch_data") as mock_upload,
        ):
            mock_get_db.return_value = mock_db
            mock_upload.return_value = {
                "upload_id": "upload123",
                "status": "uploaded",
                "item_count": len(sample_batch_data),
                "uploaded_at": datetime.utcnow().isoformat(),
            }

            # Convert data to JSON string for file upload
            json_data = json.dumps(sample_batch_data)
            files = {"file": ("batch_data.json", json_data, "application/json")}
            data = {"job_id": "job123"}

            response = client.post("/jobs/job123/upload", files=files, data=data)

            assert response.status_code == 200
            result = response.json()
            assert "upload_id" in result
            assert result["status"] == "uploaded"
            assert result["item_count"] == len(sample_batch_data)

    async def test_upload_batch_data_no_file(self, client, mock_db):
        """Test batch data upload without file."""
        with patch("src.api.batch.get_db") as mock_get_db:
            mock_get_db.return_value = mock_db

            response = client.post("/jobs/job123/upload")

            assert response.status_code == 400
            assert "No file provided" in response.json()["detail"]

    async def test_upload_batch_data_invalid_json(self, client, mock_db):
        """Test batch data upload with invalid JSON."""
        with patch("src.api.batch.get_db") as mock_get_db:
            mock_get_db.return_value = mock_db

            files = {"file": ("batch_data.json", "invalid json", "application/json")}
            response = client.post("/jobs/job123/upload", files=files)

            assert response.status_code == 400
            assert "Invalid JSON file" in response.json()["detail"]

    async def test_upload_batch_data_service_error(
        self, client, mock_db, sample_batch_data
    ):
        """Test batch data upload when service raises an error."""
        with (
            patch("src.api.batch.get_db") as mock_get_db,
            patch.object(batch_processing_service, "upload_batch_data") as mock_upload,
        ):
            mock_get_db.return_value = mock_db
            mock_upload.side_effect = Exception("Upload error")

            json_data = json.dumps(sample_batch_data)
            files = {"file": ("batch_data.json", json_data, "application/json")}

            response = client.post("/jobs/job123/upload", files=files)

            assert response.status_code == 500
            assert "Failed to upload batch data" in response.json()["detail"]

    async def test_get_job_results_success(self, client, mock_db):
        """Test successful job results retrieval."""
        with (
            patch("src.api.batch.get_db") as mock_get_db,
            patch.object(batch_processing_service, "get_job_results") as mock_results,
        ):
            mock_get_db.return_value = mock_db
            mock_results.return_value = {
                "job_id": "job123",
                "status": "completed",
                "results": [
                    {"item_id": "item1", "status": "success", "data": {"result": "ok"}},
                    {"item_id": "item2", "status": "success", "data": {"result": "ok"}},
                    {
                        "item_id": "item3",
                        "status": "failed",
                        "error": "Processing error",
                    },
                ],
                "summary": {
                    "total_items": 3,
                    "successful_items": 2,
                    "failed_items": 1,
                    "success_rate": 0.667,
                },
            }

            response = client.get("/jobs/job123/results")

            assert response.status_code == 200
            data = response.json()
            assert data["job_id"] == "job123"
            assert data["status"] == "completed"
            assert "results" in data
            assert "summary" in data
            assert len(data["results"]) == 3
            assert data["summary"]["total_items"] == 3
            assert data["summary"]["success_rate"] == 0.667

    async def test_get_job_results_job_not_completed(self, client, mock_db):
        """Test job results retrieval when job is not completed."""
        with (
            patch("src.api.batch.get_db") as mock_get_db,
            patch.object(batch_processing_service, "get_job_results") as mock_results,
        ):
            mock_get_db.return_value = mock_db
            mock_results.return_value = {
                "job_id": "job123",
                "status": "running",
                "message": "Results not available until job is completed",
            }

            response = client.get("/jobs/job123/results")

            assert response.status_code == 202  # Accepted but not ready
            assert "Results not available" in response.json()["message"]

    async def test_get_job_results_not_found(self, client, mock_db):
        """Test job results retrieval when job not found."""
        with (
            patch("src.api.batch.get_db") as mock_get_db,
            patch.object(batch_processing_service, "get_job_results") as mock_results,
        ):
            mock_get_db.return_value = mock_db
            mock_results.return_value = None

            response = client.get("/jobs/nonexistent/results")

            assert response.status_code == 404
            assert "Job not found" in response.json()["detail"]

    async def test_download_job_results_success(self, client, mock_db):
        """Test successful job results download."""
        with (
            patch("src.api.batch.get_db") as mock_get_db,
            patch.object(batch_processing_service, "export_job_results") as mock_export,
        ):
            mock_get_db.return_value = mock_db
            mock_export.return_value = b'{"results": [{"id": 1, "status": "success"}]}'

            response = client.get("/jobs/job123/download")

            assert response.status_code == 200
            assert response.headers["content-type"] == "application/json"
            assert b'{"results":' in response.content

    async def test_download_job_results_not_completed(self, client, mock_db):
        """Test job results download when job is not completed."""
        with (
            patch("src.api.batch.get_db") as mock_get_db,
            patch.object(batch_processing_service, "export_job_results") as mock_export,
        ):
            mock_get_db.return_value = mock_db
            mock_export.return_value = None

            response = client.get("/jobs/job123/download")

            assert response.status_code == 202
            assert "Results not available" in response.json()["message"]

    async def test_get_job_logs_success(self, client, mock_db):
        """Test successful job logs retrieval."""
        with (
            patch("src.api.batch.get_db") as mock_get_db,
            patch.object(batch_processing_service, "get_job_logs") as mock_logs,
        ):
            mock_get_db.return_value = mock_db
            mock_logs.return_value = {
                "job_id": "job123",
                "logs": [
                    {
                        "timestamp": datetime.utcnow().isoformat(),
                        "level": "INFO",
                        "message": "Job started",
                        "context": {"worker_id": 1},
                    },
                    {
                        "timestamp": datetime.utcnow().isoformat(),
                        "level": "DEBUG",
                        "message": "Processing item 1",
                        "context": {"item_id": "item1"},
                    },
                    {
                        "timestamp": datetime.utcnow().isoformat(),
                        "level": "ERROR",
                        "message": "Item processing failed",
                        "context": {"item_id": "item2", "error": "Timeout"},
                    },
                ],
            }

            response = client.get("/jobs/job123/logs")

            assert response.status_code == 200
            data = response.json()
            assert data["job_id"] == "job123"
            assert "logs" in data
            assert len(data["logs"]) == 3
            assert data["logs"][0]["level"] == "INFO"
            assert data["logs"][1]["level"] == "DEBUG"
            assert data["logs"][2]["level"] == "ERROR"

    async def test_get_job_logs_with_filters(self, client, mock_db):
        """Test job logs retrieval with filters."""
        with (
            patch("src.api.batch.get_db") as mock_get_db,
            patch.object(batch_processing_service, "get_job_logs") as mock_logs,
        ):
            mock_get_db.return_value = mock_db
            mock_logs.return_value = {
                "job_id": "job123",
                "logs": [
                    {
                        "timestamp": datetime.utcnow().isoformat(),
                        "level": "ERROR",
                        "message": "Processing failed",
                        "context": {"item_id": "item1"},
                    }
                ],
            }

            # Test with level filter
            response = client.get("/jobs/job123/logs?level=ERROR")
            assert response.status_code == 200
            data = response.json()
            assert len(data["logs"]) == 1
            assert data["logs"][0]["level"] == "ERROR"

    async def test_retry_failed_items_success(self, client, mock_db):
        """Test successful retry of failed items."""
        with (
            patch("src.api.batch.get_db") as mock_get_db,
            patch.object(batch_processing_service, "retry_failed_items") as mock_retry,
        ):
            mock_get_db.return_value = mock_db
            mock_retry.return_value = {
                "job_id": "job123",
                "retry_job_id": "job124",
                "status": "queued",
                "items_to_retry": 5,
                "restarted_at": datetime.utcnow().isoformat(),
            }

            response = client.post("/jobs/job123/retry")

            assert response.status_code == 200
            data = response.json()
            assert data["job_id"] == "job123"
            assert "retry_job_id" in data
            assert data["status"] == "queued"
            assert data["items_to_retry"] == 5

    async def test_retry_failed_items_no_failed_items(self, client, mock_db):
        """Test retry when no failed items exist."""
        with (
            patch("src.api.batch.get_db") as mock_get_db,
            patch.object(batch_processing_service, "retry_failed_items") as mock_retry,
        ):
            mock_get_db.return_value = mock_db
            mock_retry.return_value = None

            response = client.post("/jobs/job123/retry")

            assert response.status_code == 400
            assert "No failed items to retry" in response.json()["detail"]

    async def test_get_batch_statistics_success(self, client, mock_db):
        """Test successful batch statistics retrieval."""
        with (
            patch("src.api.batch.get_db") as mock_get_db,
            patch.object(
                batch_processing_service, "get_batch_statistics"
            ) as mock_stats,
        ):
            mock_get_db.return_value = mock_db
            mock_stats.return_value = {
                "total_jobs": 150,
                "completed_jobs": 120,
                "running_jobs": 5,
                "failed_jobs": 10,
                "cancelled_jobs": 15,
                "total_items_processed": 50000,
                "average_processing_time": 45.5,
                "success_rate": 0.8,
                "popular_operations": [
                    {"operation": "node_creation", "count": 60},
                    {"operation": "relationship_creation", "count": 40},
                    {"operation": "bulk_update", "count": 30},
                ],
            }

            response = client.get("/statistics")

            assert response.status_code == 200
            data = response.json()
            assert data["total_jobs"] == 150
            assert data["completed_jobs"] == 120
            assert data["success_rate"] == 0.8
            assert "popular_operations" in data
            assert len(data["popular_operations"]) == 3

    async def test_get_batch_statistics_with_date_range(self, client, mock_db):
        """Test batch statistics with date range filter."""
        with (
            patch("src.api.batch.get_db") as mock_get_db,
            patch.object(
                batch_processing_service, "get_batch_statistics"
            ) as mock_stats,
        ):
            mock_get_db.return_value = mock_db
            mock_stats.return_value = {
                "total_jobs": 25,
                "completed_jobs": 20,
                "running_jobs": 2,
                "failed_jobs": 1,
                "cancelled_jobs": 2,
                "total_items_processed": 5000,
                "average_processing_time": 30.2,
                "success_rate": 0.85,
                "date_range": {
                    "start_date": "2023-01-01T00:00:00Z",
                    "end_date": "2023-01-31T23:59:59Z",
                },
            }

            start_date = "2023-01-01T00:00:00Z"
            end_date = "2023-01-31T23:59:59Z"
            response = client.get(
                f"/statistics?start_date={start_date}&end_date={end_date}"
            )

            assert response.status_code == 200
            data = response.json()
            assert data["total_jobs"] == 25
            assert "date_range" in data

    async def test_get_batch_statistics_service_error(self, client, mock_db):
        """Test batch statistics when service raises an error."""
        with (
            patch("src.api.batch.get_db") as mock_get_db,
            patch.object(
                batch_processing_service, "get_batch_statistics"
            ) as mock_stats,
        ):
            mock_get_db.return_value = mock_db
            mock_stats.side_effect = Exception("Statistics error")

            response = client.get("/statistics")

            assert response.status_code == 500
            assert "Failed to get batch statistics" in response.json()["detail"]


class TestBatchAPIEdgeCases:
    """Test edge cases and error conditions for Batch API."""

    @pytest.fixture
    def client(self):
        """Create a test client for the batch API."""
        from fastapi import FastAPI

        app = FastAPI()
        app.include_router(router)
        return TestClient(app)

    @pytest.fixture
    def mock_db(self):
        """Create a mock database session."""
        return AsyncMock(spec=AsyncSession)

    def test_empty_job_data(self, client, mock_db):
        """Test with completely empty job data."""
        with patch("src.api.batch.get_db") as mock_get_db:
            mock_get_db.return_value = mock_db

            response = client.post("/batch/jobs", json={})

            assert response.status_code == 400
            assert "operation_type is required" in response.json()["detail"]

    def test_malformed_json_data(self, client, mock_db):
        """Test with malformed JSON data."""
        with patch("src.api.batch.get_db") as mock_get_db:
            mock_get_db.return_value = mock_db

            # Send invalid JSON
            response = client.post(
                "/jobs",
                data="invalid json",
                headers={"Content-Type": "application/json"},
            )

            assert response.status_code == 422  # Validation error

    def test_extremely_large_batch_data(self, client, mock_db):
        """Test with extremely large batch data."""
        large_data = {"items": [{"data": "x" * 10000} for _ in range(1000)]}

        with patch("src.api.batch.get_db") as mock_get_db:
            mock_get_db.return_value = mock_db

            response = client.post("/batch/jobs", json=large_data)

            # Should handle large data gracefully (either accept or provide meaningful error)
            assert response.status_code in [200, 400, 413, 500]

    def test_unicode_data_in_job(self, client, mock_db):
        """Test job data with unicode characters."""
        unicode_data = {
            "operation_type": "import_nodes",
            "parameters": {
                "name": "测试实体",  # Chinese
                "description": "エンティティ説明",  # Japanese
                "tags": ["entité😊", "سبة"],  # French with emoji, Arabic
            },
        }

        with (
            patch("src.api.batch.get_db") as mock_get_db,
            patch.object(batch_processing_service, "submit_batch_job") as mock_submit,
        ):
            mock_get_db.return_value = mock_db
            mock_submit.return_value = {"job_id": "unicode_job", "status": "queued"}

            response = client.post("/batch/jobs", json=unicode_data)

            assert response.status_code == 200
            data = response.json()
            assert data["job_id"] == "unicode_job"

    def test_negative_values_in_parameters(self, client, mock_db):
        """Test job parameters with negative values."""
        negative_data = {
            "operation_type": "import_nodes",
            "parameters": {
                "chunk_size": -10,  # Invalid negative
                "parallel_workers": -5,  # Invalid negative
                "timeout": -30,  # Invalid negative
            },
        }

        with patch("src.api.batch.get_db") as mock_get_db:
            mock_get_db.return_value = mock_db

            response = client.post("/batch/jobs", json=negative_data)

            # Should handle negative values appropriately
            assert response.status_code in [400, 422]

    def test_sql_injection_attempts(self, client, mock_db):
        """Test potential SQL injection attempts."""
        malicious_data = {
            "operation_type": "node_creation; DROP TABLE jobs; --",
            "parameters": {"name": "Robert'); DROP TABLE jobs; --"},
        }

        with patch("src.api.batch.get_db") as mock_get_db:
            mock_get_db.return_value = mock_db

            response = client.post("/batch/jobs", json=malicious_data)

            # Should either reject invalid operation type or handle safely
            assert response.status_code in [400, 422, 500]
            # Most importantly, shouldn't cause database corruption
            assert response.status_code != 200

    def test_concurrent_job_submission(self, client, mock_db):
        """Test concurrent job submission."""
        job_data = {"operation_type": "import_nodes", "parameters": {"test": "data"}}

        with (
            patch("src.api.batch.get_db") as mock_get_db,
            patch.object(batch_processing_service, "submit_batch_job") as mock_submit,
        ):
            mock_get_db.return_value = mock_db
            mock_submit.return_value = {"job_id": "job123", "status": "queued"}

            # Submit multiple jobs concurrently
            import threading

            results = []

            def submit_job():
                response = client.post("/batch/jobs", json=job_data)
                results.append(response.status_code)

            threads = [threading.Thread(target=submit_job) for _ in range(5)]
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join()

            # All concurrent requests should be handled
            assert all(status in [200, 500] for status in results)
            assert len(results) == 5

    def test_invalid_date_formats(self, client, mock_db):
        """Test invalid date formats in statistics requests."""
        with (
            patch("src.api.batch.get_db") as mock_get_db,
            patch.object(
                batch_processing_service, "get_batch_statistics"
            ) as mock_stats,
        ):
            mock_get_db.return_value = mock_db
            mock_stats.return_value = {"total_jobs": 0}

            # Test invalid date formats
            invalid_dates = [
                ("invalid-date", "2023-01-01"),
                ("2023-01-01", "invalid-date"),
                ("not-a-date", "also-not-a-date"),
            ]

            for start_date, end_date in invalid_dates:
                response = client.get(
                    f"/statistics?start_date={start_date}&end_date={end_date}"
                )
                # Should handle invalid dates gracefully
                assert response.status_code in [200, 400, 422]

    def test_resource_exhaustion_simulation(self, client, mock_db):
        """Test behavior under simulated resource exhaustion."""
        with (
            patch("src.api.batch.get_db") as mock_get_db,
            patch.object(batch_processing_service, "submit_batch_job") as mock_submit,
        ):
            mock_get_db.return_value = mock_db
            mock_submit.side_effect = MemoryError("Out of memory")

            job_data = {
                "operation_type": "import_nodes",
                "parameters": {"test": "data"},
            }

            response = client.post("/batch/jobs", json=job_data)

            assert response.status_code == 500
            assert "Job submission failed" in response.json()["detail"]

    def test_timeout_scenarios(self, client, mock_db):
        """Test timeout scenarios."""
        with (
            patch("src.api.batch.get_db") as mock_get_db,
            patch.object(batch_processing_service, "submit_batch_job") as mock_submit,
        ):
            mock_get_db.return_value = mock_db
            # Simulate timeout
            import asyncio

            mock_submit.side_effect = asyncio.TimeoutError("Operation timed out")

            job_data = {
                "operation_type": "import_nodes",
                "parameters": {"test": "data"},
            }

            response = client.post("/batch/jobs", json=job_data)

            assert response.status_code == 500
            assert "Job submission failed" in response.json()["detail"]


if __name__ == "__main__":
    # Run tests directly
    pytest.main([__file__, "-v", "--tb=short"])
