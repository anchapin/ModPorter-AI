"""
Working tests for batch.py API
Created to improve coverage from 25% to 70%+
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
import sys
import os
from fastapi import HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import actual modules we're testing
from src.api.batch import (
    submit_batch_job,
    get_job_status,
    cancel_job,
    pause_job,
    resume_job,
)
from src.api.batch import get_active_jobs, get_job_history, import_nodes
from src.api.batch import (
    export_graph,
    batch_delete_nodes,
    batch_validate_graph,
    get_operation_types,
)
from src.api.batch import (
    get_processing_modes,
    get_status_summary,
    get_performance_stats,
)


class TestBatchJobSubmission:
    """Test batch job submission endpoints"""

    @pytest.fixture
    def mock_db(self):
        """Mock database session"""
        return AsyncMock(spec=AsyncSession)

    @pytest.fixture
    def mock_service(self):
        """Mock batch processing service"""
        with patch("src.api.batch.batch_processing_service") as mock:
            yield mock

    async def test_submit_batch_job_success_import_nodes(self, mock_db, mock_service):
        """Test successful batch job submission for import nodes"""
        job_data = {
            "operation_type": "import_nodes",
            "parameters": {"source": "test.csv"},
            "processing_mode": "sequential",
            "chunk_size": 50,
            "parallel_workers": 2,
        }

        mock_service.submit_batch_job = AsyncMock(
            return_value={
                "success": True,
                "job_id": "test-job-123",
                "status": "submitted",
            }
        )

        result = await submit_batch_job(job_data, mock_db)

        assert result["success"] is True
        assert result["job_id"] == "test-job-123"

    async def test_submit_batch_job_missing_operation_type(self, mock_db):
        """Test batch job submission with missing operation type"""
        job_data = {"parameters": {}}

        with pytest.raises(HTTPException) as exc_info:
            await submit_batch_job(job_data, mock_db)

        assert exc_info.value.status_code == 400
        assert "operation_type is required" in str(exc_info.value.detail)

    async def test_submit_batch_job_invalid_operation_type(self, mock_db):
        """Test batch job submission with invalid operation type"""
        job_data = {"operation_type": "invalid_operation", "parameters": {}}

        with pytest.raises(HTTPException) as exc_info:
            await submit_batch_job(job_data, mock_db)

        assert exc_info.value.status_code == 400
        assert "Invalid operation_type" in str(exc_info.value.detail)


class TestBatchJobStatus:
    """Test batch job status endpoints"""

    @pytest.fixture
    def mock_service(self):
        """Mock batch processing service"""
        with patch("src.api.batch.batch_processing_service") as mock:
            yield mock

    async def test_get_job_status_success(self, mock_service):
        """Test successful job status retrieval"""
        job_id = "test-job-123"

        mock_service.get_job_status = AsyncMock(
            return_value={
                "job_id": job_id,
                "status": "running",
                "progress": 45.5,
                "total_items": 100,
                "processed_items": 45,
            }
        )

        result = await get_job_status(job_id)

        assert result["job_id"] == job_id
        assert result["status"] == "running"
        assert result["progress"] == 45.5

    async def test_get_job_status_not_found(self, mock_service):
        """Test job status retrieval for non-existent job"""
        job_id = "non-existent-job"

        mock_service.get_job_status = AsyncMock(return_value=None)

        with pytest.raises(HTTPException) as exc_info:
            await get_job_status(job_id)

        assert exc_info.value.status_code == 404
        assert "Job not found" in str(exc_info.value.detail)


class TestBatchJobControl:
    """Test batch job control endpoints"""

    @pytest.fixture
    def mock_service(self):
        """Mock batch processing service"""
        with patch("src.api.batch.batch_processing_service") as mock:
            yield mock

    async def test_cancel_job_success(self, mock_service):
        """Test successful job cancellation"""
        job_id = "test-job-123"

        mock_service.cancel_job = AsyncMock(
            return_value={"success": True, "job_id": job_id, "status": "cancelled"}
        )

        result = await cancel_job(job_id)

        assert result["success"] is True
        assert result["status"] == "cancelled"

    async def test_pause_job_success(self, mock_service):
        """Test successful job pause"""
        job_id = "test-job-123"

        mock_service.pause_job = AsyncMock(
            return_value={"success": True, "job_id": job_id, "status": "paused"}
        )

        result = await pause_job(job_id)

        assert result["success"] is True
        assert result["status"] == "paused"

    async def test_resume_job_success(self, mock_service):
        """Test successful job resume"""
        job_id = "test-job-123"

        mock_service.resume_job = AsyncMock(
            return_value={"success": True, "job_id": job_id, "status": "running"}
        )

        result = await resume_job(job_id)

        assert result["success"] is True
        assert result["status"] == "running"


class TestBatchJobManagement:
    """Test batch job management endpoints"""

    @pytest.fixture
    def mock_service(self):
        """Mock batch processing service"""
        with patch("src.api.batch.batch_processing_service") as mock:
            yield mock

    async def test_get_active_jobs_success(self, mock_service):
        """Test successful active jobs retrieval"""
        mock_service.get_active_jobs = AsyncMock(
            return_value={
                "success": True,
                "jobs": [
                    {"job_id": "job-1", "status": "running"},
                    {"job_id": "job-2", "status": "paused"},
                ],
            }
        )

        result = await get_active_jobs()

        assert result["success"] is True
        assert len(result["jobs"]) == 2

    async def test_get_job_history_success(self, mock_service):
        """Test successful job history retrieval"""
        mock_service.get_job_history = AsyncMock(
            return_value={
                "success": True,
                "jobs": [
                    {"job_id": "job-1", "status": "completed"},
                    {"job_id": "job-2", "status": "failed"},
                ],
            }
        )

        result = await get_job_history()

        assert result["success"] is True
        assert len(result["jobs"]) == 2

    async def test_get_operation_types_success(self):
        """Test successful operation types retrieval"""
        result = await get_operation_types()

        assert isinstance(result, dict)
        assert "import_nodes" in result
        assert "export_graph" in result

    async def test_get_processing_modes_success(self):
        """Test successful processing modes retrieval"""
        result = await get_processing_modes()

        assert isinstance(result, dict)
        assert "sequential" in result
        assert "parallel" in result

    async def test_get_status_summary_success(self, mock_service):
        """Test successful status summary retrieval"""
        mock_service.get_status_summary = AsyncMock(
            return_value={
                "success": True,
                "summary": {
                    "total_jobs": 100,
                    "running": 5,
                    "completed": 80,
                    "failed": 10,
                    "cancelled": 5,
                },
            }
        )

        result = await get_status_summary()

        assert result["success"] is True
        assert result["summary"]["total_jobs"] == 100

    async def test_get_performance_stats_success(self, mock_service):
        """Test successful performance stats retrieval"""
        mock_service.get_performance_stats = AsyncMock(
            return_value={
                "success": True,
                "stats": {
                    "avg_processing_time": 120.5,
                    "total_processed": 1000,
                    "success_rate": 0.95,
                },
            }
        )

        result = await get_performance_stats()

        assert result["success"] is True
        assert result["stats"]["avg_processing_time"] == 120.5


class TestBatchImportExport:
    """Test batch import/export endpoints"""

    @pytest.fixture
    def mock_db(self):
        """Mock database session"""
        return AsyncMock(spec=AsyncSession)

    @pytest.fixture
    def mock_service(self):
        """Mock batch processing service"""
        with patch("src.api.batch.batch_processing_service") as mock:
            yield mock

    async def test_import_nodes_success(self, mock_db, mock_service):
        """Test successful nodes import"""
        file_content = "id,type,name\n1,person,John\n2,organization,Acme"

        # Create a mock upload file
        mock_file = Mock(spec=UploadFile)
        mock_file.filename = "nodes.csv"
        mock_file.read = AsyncMock(return_value=file_content.encode())

        mock_service.submit_batch_job = AsyncMock(
            return_value={
                "success": True,
                "job_id": "import-job-123",
                "status": "submitted",
            }
        )

        result = await import_nodes(mock_file, db=mock_db)

        assert result["success"] is True
        assert "job_id" in result

    async def test_export_graph_success(self, mock_service):
        """Test successful graph export"""
        mock_service.submit_batch_job = AsyncMock(
            return_value={
                "success": True,
                "job_id": "export-job-456",
                "status": "submitted",
            }
        )

        result = await export_graph(
            format="json",
            filters={},
            processing_mode="sequential",
            chunk_size=100,
            parallel_workers=4,
        )

        assert result["success"] is True
        assert "job_id" in result

    async def test_batch_delete_nodes_success(self, mock_service):
        """Test successful batch node deletion"""
        delete_data = {"filters": {"type": "person"}, "dry_run": False}

        mock_service.submit_batch_job = AsyncMock(
            return_value={
                "success": True,
                "job_id": "delete-job-789",
                "status": "submitted",
            }
        )

        result = await batch_delete_nodes(delete_data)

        assert result["success"] is True
        assert "job_id" in result

    async def test_batch_validate_graph_success(self, mock_service):
        """Test successful graph validation"""
        validation_data = {"check_integrity": True, "check_duplicates": False}

        mock_service.submit_batch_job = AsyncMock(
            return_value={
                "success": True,
                "job_id": "validate-job-101",
                "status": "submitted",
            }
        )

        result = await batch_validate_graph(validation_data)

        assert result["success"] is True
        assert "job_id" in result


class TestBatchErrorHandling:
    """Test batch API error handling"""

    @pytest.fixture
    def mock_service(self):
        """Mock batch processing service"""
        with patch("src.api.batch.batch_processing_service") as mock:
            yield mock

    async def test_service_unavailable_error(self, mock_service):
        """Test handling when service is unavailable"""
        mock_service.cancel_job = AsyncMock(
            side_effect=Exception("Service unavailable")
        )

        with pytest.raises(HTTPException) as exc_info:
            await cancel_job("test-job")

        assert exc_info.value.status_code == 500

    async def test_database_error_handling(self, mock_service):
        """Test handling database errors"""
        mock_service.get_job_status = AsyncMock(
            side_effect=Exception("Database connection failed")
        )

        with pytest.raises(HTTPException) as exc_info:
            await get_job_status("test-job")

        assert exc_info.value.status_code == 500

    async def test_batch_delete_no_filters_error(self):
        """Test batch delete with no filters"""
        delete_data = {"dry_run": False}

        with pytest.raises(HTTPException) as exc_info:
            await batch_delete_nodes(delete_data)

        assert exc_info.value.status_code == 400
        assert "filters are required" in str(exc_info.value.detail)


class TestBatchUtilityFunctions:
    """Test batch utility helper functions"""

    def test_get_operation_description(self):
        """Test operation description parsing"""
        from src.api.batch import _get_operation_description

        result = _get_operation_description("import_nodes")
        assert "import" in result.lower()

    def test_operation_file_requirements(self):
        """Test operation file requirement checking"""
        from src.api.batch import _operation_requires_file

        result = _operation_requires_file("import_nodes")
        assert result is True

    def test_processing_mode_descriptions(self):
        """Test processing mode descriptions"""
        from src.api.batch import _get_processing_mode_description

        result = _get_processing_mode_description("sequential")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_processing_mode_use_cases(self):
        """Test processing mode use cases"""
        from src.api.batch import _get_processing_mode_use_cases

        result = _get_processing_mode_use_cases("parallel")
        assert isinstance(result, list)

    def test_processing_mode_recommendations(self):
        """Test processing mode recommendations"""
        from src.api.batch import _get_processing_mode_recommendations

        result = _get_processing_mode_recommendations("chunked")
        assert isinstance(result, list)


class TestCSVParsing:
    """Test CSV parsing utilities"""

    async def test_parse_csv_nodes(self):
        """Test CSV nodes parsing"""
        from src.api.batch import _parse_csv_nodes

        csv_content = "id,type,name\n1,person,John\n2,organization,Acme"
        result = await _parse_csv_nodes(csv_content)

        assert len(result) == 2
        assert result[0]["id"] == "1"
        assert result[0]["type"] == "person"
        assert result[0]["name"] == "John"

    async def test_parse_csv_relationships(self):
        """Test CSV relationships parsing"""
        from src.api.batch import _parse_csv_relationships

        csv_content = "source,target,type\n1,2,WORKS_FOR\n2,3,LOCATED_IN"
        result = await _parse_csv_relationships(csv_content)

        assert len(result) == 2
        assert result[0]["source"] == "1"
        assert result[0]["target"] == "2"
        assert result[0]["type"] == "WORKS_FOR"
