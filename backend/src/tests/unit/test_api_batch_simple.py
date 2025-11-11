"""Simplified tests for batch.py API endpoints
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.batch import router
from src.services.batch_processing import BatchOperationType, ProcessingMode


class TestBatchJobEndpoints:
    """Test batch job management endpoints"""
    
    @pytest.fixture
    def mock_db(self):
        """Mock database session"""
        return AsyncMock(spec=AsyncSession)
    
    @pytest.fixture
    def mock_batch_service(self):
        """Mock batch processing service"""
        with patch('src.api.batch.batch_processing_service') as mock:
            yield mock
    
    @pytest.mark.asyncio
    async def test_submit_batch_job_success(self, mock_db, mock_batch_service):
        """Test successful batch job submission"""
        # Setup mock response
        mock_batch_service.submit_batch_job = AsyncMock(return_value={
            "success": True,
            "job_id": "test-job-123",
            "estimated_total_items": 1000,
            "status": "pending"
        })
        
        job_data = {
            "operation_type": "import_nodes",
            "parameters": {"source": "test.json"},
            "processing_mode": "sequential",
            "chunk_size": 100,
            "parallel_workers": 4
        }
        
        # Call the endpoint
        from src.api.batch import submit_batch_job
        result = await submit_batch_job(job_data, mock_db)
        
        # Verify service was called correctly
        mock_batch_service.submit_batch_job.assert_called_once_with(
            BatchOperationType.IMPORT_NODES,
            {"source": "test.json"},
            ProcessingMode.SEQUENTIAL,
            100,
            4,
            mock_db
        )
        
        # Verify response
        assert result["success"] is True
        assert result["job_id"] == "test-job-123"
        assert result["estimated_total_items"] == 1000
    
    @pytest.mark.asyncio
    async def test_submit_batch_job_invalid_operation_type(self, mock_db, mock_batch_service):
        """Test batch job submission with invalid operation type"""
        job_data = {
            "operation_type": "invalid_operation",
            "parameters": {}
        }
        
        from src.api.batch import submit_batch_job
        from fastapi import HTTPException
        
        with pytest.raises(HTTPException) as exc_info:
            await submit_batch_job(job_data, mock_db)
        
        assert exc_info.value.status_code == 400
        assert "Invalid operation_type" in str(exc_info.value.detail)
    
    @pytest.mark.asyncio
    async def test_get_job_status_success(self, mock_batch_service):
        """Test successful job status retrieval"""
        mock_batch_service.get_job_status = AsyncMock(return_value={
            "success": True,
            "job_id": "test-job-123",
            "status": "running",
            "progress": 45.5,
            "processed_items": 455,
            "total_items": 1000
        })
        
        from src.api.batch import get_job_status
        result = await get_job_status("test-job-123")
        
        mock_batch_service.get_job_status.assert_called_once_with("test-job-123")
        assert result["success"] is True
        assert result["job_id"] == "test-job-123"
        assert result["status"] == "running"
        assert result["progress"] == 45.5
