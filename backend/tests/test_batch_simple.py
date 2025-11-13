"""
Simple working tests for batch.py API
Focus on core functionality to improve coverage
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock, MagicMock
import sys
import os
import json
from fastapi import HTTPException, UploadFile, File, Query
from sqlalchemy.ext.asyncio import AsyncSession

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import actual modules we're testing
from src.api.batch import (
    submit_batch_job, get_job_status, cancel_job, pause_job, resume_job,
    get_active_jobs, get_job_history, import_nodes, import_relationships,
    export_graph, batch_delete_nodes, batch_validate_graph, get_operation_types,
    get_processing_modes, get_status_summary, get_performance_stats,
    _get_operation_description, _operation_requires_file, _get_operation_duration,
    _get_processing_mode_description, _get_processing_mode_use_cases,
    _get_processing_mode_recommendations, _parse_csv_nodes, _parse_csv_relationships
)
from src.services.batch_processing import BatchOperationType, ProcessingMode


@pytest.mark.asyncio
class TestBatchAPIBasic:
    """Test basic batch API functionality"""

    @pytest.fixture
    def mock_db(self):
        """Mock database session"""
        return AsyncMock(spec=AsyncSession)
    
    @pytest.fixture
    def mock_service(self):
        """Mock batch processing service"""
        with patch('src.api.batch.batch_processing_service') as mock:
            yield mock

    async def test_submit_batch_job_basic_success(self, mock_db, mock_service):
        """Test basic successful batch job submission"""
        job_data = {
            "operation_type": "import_nodes",
            "parameters": {"source": "test.csv"},
            "processing_mode": "sequential",
            "chunk_size": 50,
            "parallel_workers": 2
        }
        
        mock_service.submit_batch_job = AsyncMock(return_value={
            "success": True,
            "job_id": "test-job-123",
            "status": "submitted",
            "estimated_total_items": 100
        })
        
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
        job_data = {
            "operation_type": "invalid_operation",
            "parameters": {}
        }
        
        with pytest.raises(HTTPException) as exc_info:
            await submit_batch_job(job_data, mock_db)
        
        assert exc_info.value.status_code == 400
        assert "Invalid operation_type" in str(exc_info.value.detail)

    async def test_submit_batch_job_invalid_processing_mode(self, mock_db):
        """Test batch job submission with invalid processing mode"""
        job_data = {
            "operation_type": "import_nodes",
            "parameters": {},
            "processing_mode": "invalid_mode"
        }
        
        with pytest.raises(HTTPException) as exc_info:
            await submit_batch_job(job_data, mock_db)
        
        assert exc_info.value.status_code == 400
        assert "Invalid processing_mode" in str(exc_info.value.detail)

    async def test_submit_batch_job_service_failure(self, mock_db, mock_service):
        """Test batch job submission when service fails"""
        job_data = {
            "operation_type": "import_nodes",
            "parameters": {}
        }
        
        mock_service.submit_batch_job = AsyncMock(return_value={
            "success": False,
            "error": "Service unavailable"
        })
        
        with pytest.raises(HTTPException) as exc_info:
            await submit_batch_job(job_data, mock_db)
        
        assert exc_info.value.status_code == 400
        assert "Service unavailable" in str(exc_info.value.detail)

    async def test_get_job_status_success(self, mock_service):
        """Test successful job status retrieval"""
        job_id = "test-job-123"
        
        mock_service.get_job_status = AsyncMock(return_value={
            "success": True,
            "job_id": job_id,
            "status": "running",
            "progress": 45.5,
            "total_items": 100,
            "processed_items": 45
        })
        
        result = await get_job_status(job_id)
        
        assert result["success"] is True
        assert result["job_id"] == job_id
        assert result["status"] == "running"

    async def test_get_job_status_not_found(self, mock_service):
        """Test job status retrieval for non-existent job"""
        job_id = "non-existent-job"
        
        mock_service.get_job_status = AsyncMock(return_value={
            "success": False,
            "error": "Job not found"
        })
        
        with pytest.raises(HTTPException) as exc_info:
            await get_job_status(job_id)
        
        assert exc_info.value.status_code == 404

    async def test_cancel_job_success(self, mock_service):
        """Test successful job cancellation"""
        job_id = "test-job-123"
        
        mock_service.cancel_job = AsyncMock(return_value={
            "success": True,
            "job_id": job_id,
            "status": "cancelled"
        })
        
        result = await cancel_job(job_id)
        
        assert result["success"] is True
        assert result["status"] == "cancelled"

    async def test_pause_job_success(self, mock_service):
        """Test successful job pause"""
        job_id = "test-job-123"
        
        mock_service.pause_job = AsyncMock(return_value={
            "success": True,
            "job_id": job_id,
            "status": "paused"
        })
        
        result = await pause_job(job_id)
        
        assert result["success"] is True
        assert result["status"] == "paused"

    async def test_resume_job_success(self, mock_service):
        """Test successful job resume"""
        job_id = "test-job-123"
        
        mock_service.resume_job = AsyncMock(return_value={
            "success": True,
            "job_id": job_id,
            "status": "running"
        })
        
        result = await resume_job(job_id)
        
        assert result["success"] is True
        assert result["status"] == "running"

    async def test_get_active_jobs_success(self, mock_service):
        """Test successful active jobs retrieval"""
        mock_service.get_active_jobs = AsyncMock(return_value={
            "success": True,
            "jobs": [
                {"job_id": "job-1", "status": "running"},
                {"job_id": "job-2", "status": "paused"}
            ]
        })
        
        result = await get_active_jobs()
        
        assert result["success"] is True
        assert len(result["jobs"]) == 2

    async def test_get_job_history_success(self, mock_service):
        """Test successful job history retrieval"""
        mock_service.get_job_history = AsyncMock(return_value={
            "success": True,
            "jobs": [
                {"job_id": "job-1", "status": "completed"},
                {"job_id": "job-2", "status": "failed"}
            ]
        })
        
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
        mock_service.get_status_summary = AsyncMock(return_value={
            "success": True,
            "summary": {
                "total_jobs": 100,
                "running": 5,
                "completed": 80,
                "failed": 10,
                "cancelled": 5
            }
        })
        
        result = await get_status_summary()
        
        assert result["success"] is True
        assert result["summary"]["total_jobs"] == 100

    async def test_get_performance_stats_success(self, mock_service):
        """Test successful performance stats retrieval"""
        mock_service.get_performance_stats = AsyncMock(return_value={
            "success": True,
            "stats": {
                "avg_processing_time": 120.5,
                "total_processed": 1000,
                "success_rate": 0.95
            }
        })
        
        result = await get_performance_stats()
        
        assert result["success"] is True
        assert result["stats"]["avg_processing_time"] == 120.5


class TestBatchUtilityFunctions:
    """Test batch utility helper functions"""

    def test_get_operation_description(self):
        """Test operation description parsing"""
        result = _get_operation_description(BatchOperationType.IMPORT_NODES)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_get_operation_description_unknown(self):
        """Test operation description for unknown operation"""
        result = _get_operation_description("unknown_operation")
        assert result == "Unknown operation"

    def test_operation_file_requirements(self):
        """Test operation file requirement checking"""
        result = _operation_requires_file(BatchOperationType.IMPORT_NODES)
        assert result is True

    def test_operation_file_requirements_false(self):
        """Test operation file requirement for non-file operation"""
        result = _operation_requires_file(BatchOperationType.EXPORT_GRAPH)
        assert result is False

    def test_get_operation_duration(self):
        """Test operation duration description"""
        result = _get_operation_duration(BatchOperationType.IMPORT_NODES)
        assert isinstance(result, str)
        assert "min" in result

    def test_get_processing_mode_description(self):
        """Test processing mode descriptions"""
        result = _get_processing_mode_description(ProcessingMode.SEQUENTIAL)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_get_processing_mode_use_cases(self):
        """Test processing mode use cases"""
        result = _get_processing_mode_use_cases(ProcessingMode.PARALLEL)
        assert isinstance(result, list)

    def test_get_processing_mode_recommendations(self):
        """Test processing mode recommendations"""
        result = _get_processing_mode_recommendations(ProcessingMode.CHUNKED)
        assert isinstance(result, list)

    async def test_parse_csv_nodes(self):
        """Test CSV nodes parsing"""
        csv_content = "id,type,name\n1,person,John\n2,organization,Acme"
        result = await _parse_csv_nodes(csv_content)
        
        assert len(result) == 2
        assert isinstance(result[0], dict)

    async def test_parse_csv_relationships(self):
        """Test CSV relationships parsing"""
        csv_content = "source,target,type\n1,2,WORKS_FOR\n2,3,LOCATED_IN"
        result = await _parse_csv_relationships(csv_content)
        
        assert len(result) == 2
        assert isinstance(result[0], dict)


class TestBatchErrorHandling:
    """Test batch API error handling"""

    @pytest.fixture
    def mock_service(self):
        """Mock batch processing service"""
        with patch('src.api.batch.batch_processing_service') as mock:
            yield mock

    async def test_service_unavailable_error(self, mock_service):
        """Test handling when service is unavailable"""
        mock_service.cancel_job = AsyncMock(side_effect=Exception("Service unavailable"))
        
        with pytest.raises(HTTPException) as exc_info:
            await cancel_job("test-job")
        
        assert exc_info.value.status_code == 500

    async def test_database_error_handling(self, mock_service):
        """Test handling database errors"""
        mock_service.get_job_status = AsyncMock(side_effect=Exception("Database connection failed"))
        
        with pytest.raises(HTTPException) as exc_info:
            await get_job_status("test-job")
        
        assert exc_info.value.status_code == 500

    async def test_submit_batch_job_exception_handling(self, mock_db, mock_service):
        """Test batch job submission with unexpected exception"""
        job_data = {
            "operation_type": "import_nodes",
            "parameters": {}
        }
        
        mock_service.submit_batch_job = AsyncMock(side_effect=Exception("Database error"))
        
        with pytest.raises(HTTPException) as exc_info:
            await submit_batch_job(job_data, mock_db)
        
        assert exc_info.value.status_code == 500
        assert "Job submission failed" in str(exc_info.value.detail)


# Simple test to increase coverage of utility functions
class TestBatchCoverageBoost:
    """Additional tests to boost coverage"""

    def test_all_operation_descriptions(self):
        """Test all operation type descriptions"""
        for op_type in BatchOperationType:
            result = _get_operation_description(op_type)
            assert isinstance(result, str)
            assert len(result) > 0

    def test_all_operation_durations(self):
        """Test all operation type durations"""
        for op_type in BatchOperationType:
            result = _get_operation_duration(op_type)
            assert isinstance(result, str)

    def test_all_processing_mode_descriptions(self):
        """Test all processing mode descriptions"""
        for mode in ProcessingMode:
            result = _get_processing_mode_description(mode)
            assert isinstance(result, str)
            assert len(result) > 0

    def test_all_processing_mode_use_cases(self):
        """Test all processing mode use cases"""
        for mode in ProcessingMode:
            result = _get_processing_mode_use_cases(mode)
            assert isinstance(result, list)

    def test_all_processing_mode_recommendations(self):
        """Test all processing mode recommendations"""
        for mode in ProcessingMode:
            result = _get_processing_mode_recommendations(mode)
            assert isinstance(result, list)

    async def test_parse_empty_csv_nodes(self):
        """Test parsing empty CSV for nodes"""
        csv_content = "id,type,name\n"
        result = await _parse_csv_nodes(csv_content)
        assert len(result) == 0

    async def test_parse_empty_csv_relationships(self):
        """Test parsing empty CSV for relationships"""
        csv_content = "source,target,type\n"
        result = await _parse_csv_relationships(csv_content)
        assert len(result) == 0
