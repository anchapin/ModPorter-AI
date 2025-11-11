"""
Simplified comprehensive tests for batch.py API endpoints
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
    def mock_service(self):
        """Mock batch processing service"""
        with patch('src.api.batch.batch_processing_service') as mock:
            yield mock
    
    @pytest.mark.asyncio
    async def test_submit_batch_job_success(self, mock_db, mock_service):
        """Test successful batch job submission"""
        # Setup mock response
        mock_service.submit_batch_job.return_value = {
            "success": True,
            "job_id": "test-job-123",
            "estimated_total_items": 1000,
            "status": "pending"
        }
        
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
        mock_service.submit_batch_job.assert_called_once_with(
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
    async def test_submit_batch_job_invalid_operation_type(self, mock_db, mock_service):
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
    async def test_submit_batch_job_missing_operation_type(self, mock_db, mock_service):
        """Test batch job submission with missing operation type"""
        job_data = {
            "parameters": {}
        }
        
        from src.api.batch import submit_batch_job
        from fastapi import HTTPException
        
        with pytest.raises(HTTPException) as exc_info:
            await submit_batch_job(job_data, mock_db)
        
        assert exc_info.value.status_code == 400
        assert "operation_type is required" in str(exc_info.value.detail)
    
    @pytest.mark.asyncio
    async def test_get_job_status_success(self, mock_service):
        """Test successful job status retrieval"""
        mock_service.get_job_status.return_value = {
            "success": True,
            "job_id": "test-job-123",
            "status": "running",
            "progress": 45.5,
            "processed_items": 455,
            "total_items": 1000
        }
        
        from src.api.batch import get_job_status
        result = await get_job_status("test-job-123")
        
        mock_service.get_job_status.assert_called_once_with("test-job-123")
        assert result["success"] is True
        assert result["job_id"] == "test-job-123"
        assert result["status"] == "running"
        assert result["progress"] == 45.5
    
    @pytest.mark.asyncio
    async def test_get_job_status_not_found(self, mock_service):
        """Test job status retrieval for non-existent job"""
        mock_service.get_job_status.return_value = {
            "success": False,
            "error": "Job not found"
        }
        
        from src.api.batch import get_job_status
        from fastapi import HTTPException
        
        with pytest.raises(HTTPException) as exc_info:
            await get_job_status("non-existent-job")
        
        assert exc_info.value.status_code == 404
        assert "Job not found" in str(exc_info.value.detail)
    
    @pytest.mark.asyncio
    async def test_cancel_job_success(self, mock_service):
        """Test successful job cancellation"""
        mock_service.cancel_job.return_value = {
            "success": True,
            "job_id": "test-job-123",
            "status": "cancelled",
            "message": "Job cancelled successfully"
        }
        
        cancel_data = {"reason": "Test cancellation"}
        
        from src.api.batch import cancel_job
        result = await cancel_job("test-job-123", cancel_data)
        
        mock_service.cancel_job.assert_called_once_with("test-job-123", "Test cancellation")
        assert result["success"] is True
        assert result["status"] == "cancelled"
    
    @pytest.mark.asyncio
    async def test_pause_job_success(self, mock_service):
        """Test successful job pausing"""
        mock_service.pause_job.return_value = {
            "success": True,
            "job_id": "test-job-123",
            "status": "paused",
            "message": "Job paused successfully"
        }
        
        from src.api.batch import pause_job
        result = await pause_job("test-job-123")
        
        mock_service.pause_job.assert_called_once_with("test-job-123", "User requested pause")
        assert result["success"] is True
        assert result["status"] == "paused"
    
    @pytest.mark.asyncio
    async def test_resume_job_success(self, mock_service):
        """Test successful job resuming"""
        mock_service.resume_job.return_value = {
            "success": True,
            "job_id": "test-job-123",
            "status": "running",
            "message": "Job resumed successfully"
        }
        
        from src.api.batch import resume_job
        result = await resume_job("test-job-123")
        
        mock_service.resume_job.assert_called_once_with("test-job-123")
        assert result["success"] is True
        assert result["status"] == "running"
    
    @pytest.mark.asyncio
    async def test_get_active_jobs_success(self, mock_service):
        """Test successful active jobs retrieval"""
        mock_service.get_active_jobs.return_value = {
            "success": True,
            "active_jobs": [
                {"job_id": "job1", "status": "running", "operation_type": "import_nodes"},
                {"job_id": "job2", "status": "pending", "operation_type": "export_graph"}
            ],
            "total_active": 2,
            "queue_size": 1
        }
        
        from src.api.batch import get_active_jobs
        result = await get_active_jobs()
        
        mock_service.get_active_jobs.assert_called_once()
        assert result["success"] is True
        assert len(result["active_jobs"]) == 2
        assert result["total_active"] == 2


class TestBatchUtilityEndpoints:
    """Test batch utility endpoints"""
    
    @pytest.mark.asyncio
    async def test_get_operation_types(self):
        """Test operation types endpoint"""
        from src.api.batch import get_operation_types
        result = await get_operation_types()
        
        assert result["success"] is True
        assert "operation_types" in result
        assert result["total_types"] > 0
        
        # Check that all operation types are present
        operation_values = [op["value"] for op in result["operation_types"]]
        assert "import_nodes" in operation_values
        assert "export_graph" in operation_values
        assert "validate_graph" in operation_values
        
        # Check structure of operation type data
        for op_type in result["operation_types"]:
            assert "value" in op_type
            assert "name" in op_type
            assert "description" in op_type
            assert "requires_file" in op_type
            assert isinstance(op_type["requires_file"], bool)
    
    @pytest.mark.asyncio
    async def test_get_processing_modes(self):
        """Test processing modes endpoint"""
        from src.api.batch import get_processing_modes
        result = await get_processing_modes()
        
        assert result["success"] is True
        assert "processing_modes" in result
        assert result["total_modes"] > 0
        
        # Check that all processing modes are present
        mode_values = [mode["value"] for mode in result["processing_modes"]]
        assert "sequential" in mode_values
        assert "parallel" in mode_values
        
        # Check structure of processing mode data
        for mode in result["processing_modes"]:
            assert "value" in mode
            assert "name" in mode
            assert "description" in mode
            assert "use_cases" in mode
            assert "recommended_for" in mode
            assert isinstance(mode["use_cases"], list)
    
    @pytest.mark.asyncio
    async def test_get_status_summary(self):
        """Test status summary endpoint"""
        with patch('src.api.batch.batch_processing_service') as mock_service:
            # Mock active jobs response
            mock_service.get_active_jobs.return_value = {
                "success": True,
                "active_jobs": [
                    {"job_id": "job1", "status": "running", "operation_type": "import_nodes"},
                    {"job_id": "job2", "status": "pending", "operation_type": "export_graph"}
                ],
                "total_active": 2,
                "queue_size": 1,
                "max_concurrent_jobs": 4
            }
            
            # Mock history response
            mock_service.get_job_history.return_value = {
                "success": True,
                "job_history": [
                    {"job_id": "job3", "status": "completed", "operation_type": "validate_graph"},
                    {"job_id": "job4", "status": "failed", "operation_type": "import_nodes"}
                ],
                "total_history": 2
            }
            
            from src.api.batch import get_status_summary
            result = await get_status_summary()
            
            assert result["success"] is True
            assert "summary" in result
            
            summary = result["summary"]
            assert "status_counts" in summary
            assert "operation_type_counts" in summary
            assert "total_active" in summary
            assert "queue_size" in summary
    
    @pytest.mark.asyncio
    async def test_get_performance_stats(self):
        """Test performance stats endpoint"""
        from src.api.batch import get_performance_stats
        result = await get_performance_stats()
        
        assert result["success"] is True
        assert "performance_stats" in result
        
        stats = result["performance_stats"]
        assert "total_jobs_processed" in stats
        assert "total_items_processed" in stats
        assert "average_processing_time_seconds" in stats
        assert "success_rate" in stats
        assert "failure_rate" in stats
        assert "operation_type_performance" in stats


class TestBatchHelperFunctions:
    """Test batch helper functions"""
    
    @pytest.mark.asyncio
    async def test_parse_csv_nodes(self):
        """Test CSV nodes parsing"""
        csv_content = """name,node_type,platform,description,minecraft_version,expert_validated,community_rating,properties
Test Mod,fmod,fabric,A test mod,1.20.1,true,4.5,"{""author"":""test""}"
Another Mod,mod,forge,Another mod,1.19.4,false,3.2,\"{}\""""
        
        from src.api.batch import _parse_csv_nodes
        nodes = await _parse_csv_nodes(csv_content)
        
        assert len(nodes) == 2
        
        # Check first node
        node1 = nodes[0]
        assert node1["name"] == "Test Mod"
        assert node1["node_type"] == "fmod"
        assert node1["platform"] == "fabric"
        assert node1["expert_validated"] is True
        assert node1["community_rating"] == 4.5
    
    @pytest.mark.asyncio
    async def test_parse_csv_relationships(self):
        """Test CSV relationships parsing"""
        csv_content = """source_node_id,target_node_id,relationship_type,confidence_score,properties
node1,node2,relates_to,0.8,"{""weight"":0.5}"
node2,node3,depends_on,0.9,\"{}\""""
        
        from src.api.batch import _parse_csv_relationships
        relationships = await _parse_csv_relationships(csv_content)
        
        assert len(relationships) == 2
        
        # Check first relationship
        rel1 = relationships[0]
        assert rel1["source_node_id"] == "node1"
        assert rel1["target_node_id"] == "node2"
        assert rel1["relationship_type"] == "relates_to"
        assert rel1["confidence_score"] == 0.8
    
    def test_get_operation_description(self):
        """Test operation description helper"""
        from src.api.batch import _get_operation_description
        
        description = _get_operation_description(BatchOperationType.IMPORT_NODES)
        assert "import" in description.lower()
        assert "nodes" in description.lower()
        
        description = _get_operation_description(BatchOperationType.VALIDATE_GRAPH)
        assert "validate" in description.lower()
        assert "graph" in description.lower()
    
    def test_operation_requires_file(self):
        """Test operation file requirement helper"""
        from src.api.batch import _operation_requires_file
        
        assert _operation_requires_file(BatchOperationType.IMPORT_NODES) is True
        assert _operation_requires_file(BatchOperationType.IMPORT_RELATIONSHIPS) is True
        assert _operation_requires_file(BatchOperationType.EXPORT_GRAPH) is False
        assert _operation_requires_file(BatchOperationType.VALIDATE_GRAPH) is False
    
    def test_get_processing_mode_description(self):
        """Test processing mode description helper"""
        from src.api.batch import _get_processing_mode_description
        
        desc = _get_processing_mode_description(ProcessingMode.SEQUENTIAL)
        assert "sequence" in desc.lower()
        
        desc = _get_processing_mode_description(ProcessingMode.PARALLEL)
        assert "simultaneously" in desc.lower()


class TestBatchErrorHandling:
    """Test batch API error handling"""
    
    @pytest.mark.asyncio
    async def test_submit_batch_job_service_error(self):
        """Test handling of service errors during job submission"""
        mock_db = AsyncMock(spec=AsyncSession)
        
        with patch('src.api.batch.batch_processing_service') as mock_service:
            mock_service.submit_batch_job.side_effect = Exception("Service error")
            
            from src.api.batch import submit_batch_job
            from fastapi import HTTPException
            
            job_data = {
                "operation_type": "import_nodes",
                "parameters": {}
            }
            
            with pytest.raises(HTTPException) as exc_info:
                await submit_batch_job(job_data, mock_db)
            
            assert exc_info.value.status_code == 500
            assert "Job submission failed" in str(exc_info.value.detail)
    
    @pytest.mark.asyncio
    async def test_get_job_status_service_error(self):
        """Test handling of service errors during job status retrieval"""
        with patch('src.api.batch.batch_processing_service') as mock_service:
            mock_service.get_job_status.side_effect = Exception("Service error")
            
            from src.api.batch import get_job_status
            from fastapi import HTTPException
            
            with pytest.raises(HTTPException) as exc_info:
                await get_job_status("test-job")
            
            assert exc_info.value.status_code == 500
            assert "Failed to get job status" in str(exc_info.value.detail)
