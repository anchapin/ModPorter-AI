"""
Comprehensive Test Suite for Batch Processing API

This test provides complete coverage for all batch API endpoints including:
- Job submission, status tracking, cancellation, pause/resume
- Batch import/export operations
- Performance monitoring and statistics
- Error handling and edge cases
"""

import pytest
import json
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

# Import the batch API functions
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))
from src.api.batch import (
    submit_batch_job, get_job_status, cancel_job, pause_job, resume_job,
    get_active_jobs, get_job_history, import_nodes, import_relationships,
    export_graph, batch_delete_nodes, batch_validate_graph, get_operation_types,
    get_processing_modes, get_status_summary, get_performance_stats
)
from src.services.batch_processing import BatchOperationType, ProcessingMode


class TestBatchJobManagement:
    """Test suite for batch job management endpoints"""
    
    @pytest.fixture
    def mock_db(self):
        """Mock database session"""
        return AsyncMock(spec=AsyncSession)
    
    @pytest.fixture
    def sample_job_data(self):
        """Sample job data for testing"""
        return {
            "operation_type": "import_nodes",
            "parameters": {"source": "test.csv"},
            "processing_mode": "sequential",
            "chunk_size": 50,
            "parallel_workers": 2
        }
    
    @pytest.mark.asyncio
    async def test_submit_batch_job_success(self, mock_db, sample_job_data):
        """Test successful batch job submission"""
        # Mock the batch processing service
        with patch('src.api.batch.batch_processing_service') as mock_service:
            mock_service.submit_job.return_value = "job_123"
            
            result = await submit_batch_job(sample_job_data, mock_db)
            
            assert result == {"job_id": "job_123", "status": "submitted"}
            mock_service.submit_job.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_submit_batch_job_missing_operation_type(self, mock_db):
        """Test job submission with missing operation type"""
        job_data = {"parameters": {"source": "test.csv"}}
        
        with pytest.raises(Exception):  # Should raise HTTPException
            await submit_batch_job(job_data, mock_db)
    
    @pytest.mark.asyncio
    async def test_submit_batch_job_invalid_operation_type(self, mock_db, sample_job_data):
        """Test job submission with invalid operation type"""
        sample_job_data["operation_type"] = "invalid_operation"
        
        with pytest.raises(Exception):  # Should raise HTTPException
            await submit_batch_job(sample_job_data, mock_db)
    
    @pytest.mark.asyncio
    async def test_get_job_status_success(self, mock_db):
        """Test successful job status retrieval"""
        job_id = "job_123"
        
        with patch('src.api.batch.batch_processing_service') as mock_service:
            mock_service.get_job_status.return_value = {
                "job_id": job_id,
                "status": "running",
                "progress": 45,
                "total_items": 100,
                "processed_items": 45
            }
            
            result = await get_job_status(job_id, mock_db)
            
            assert result["job_id"] == job_id
            assert result["status"] == "running"
            assert result["progress"] == 45
            mock_service.get_job_status.assert_called_once_with(job_id, db=mock_db)
    
    @pytest.mark.asyncio
    async def test_cancel_job_success(self, mock_db):
        """Test successful job cancellation"""
        job_id = "job_123"
        
        with patch('src.api.batch.batch_processing_service') as mock_service:
            mock_service.cancel_job.return_value = True
            
            result = await cancel_job(job_id, mock_db)
            
            assert result["job_id"] == job_id
            assert result["status"] == "cancelled"
            mock_service.cancel_job.assert_called_once_with(job_id, db=mock_db)
    
    @pytest.mark.asyncio
    async def test_pause_job_success(self, mock_db):
        """Test successful job pause"""
        job_id = "job_123"
        
        with patch('src.api.batch.batch_processing_service') as mock_service:
            mock_service.pause_job.return_value = True
            
            result = await pause_job(job_id, mock_db)
            
            assert result["job_id"] == job_id
            assert result["status"] == "paused"
            mock_service.pause_job.assert_called_once_with(job_id, db=mock_db)
    
    @pytest.mark.asyncio
    async def test_resume_job_success(self, mock_db):
        """Test successful job resume"""
        job_id = "job_123"
        
        with patch('src.api.batch.batch_processing_service') as mock_service:
            mock_service.resume_job.return_value = True
            
            result = await resume_job(job_id, mock_db)
            
            assert result["job_id"] == job_id
            assert result["status"] == "resumed"
            mock_service.resume_job.assert_called_once_with(job_id, db=mock_db)
    
    @pytest.mark.asyncio
    async def test_get_active_jobs_success(self, mock_db):
        """Test successful active jobs retrieval"""
        with patch('src.api.batch.batch_processing_service') as mock_service:
            mock_service.get_active_jobs.return_value = [
                {"job_id": "job_1", "status": "running"},
                {"job_id": "job_2", "status": "paused"}
            ]
            
            result = await get_active_jobs(mock_db)
            
            assert len(result["active_jobs"]) == 2
            assert result["active_jobs"][0]["job_id"] == "job_1"
            mock_service.get_active_jobs.assert_called_once_with(db=mock_db)
    
    @pytest.mark.asyncio
    async def test_get_job_history_success(self, mock_db):
        """Test successful job history retrieval"""
        with patch('src.api.batch.batch_processing_service') as mock_service:
            mock_service.get_job_history.return_value = [
                {"job_id": "job_1", "status": "completed", "completed_at": "2023-01-01"},
                {"job_id": "job_2", "status": "failed", "failed_at": "2023-01-02"}
            ]
            
            result = await get_job_history(mock_db, limit=10, offset=0)
            
            assert len(result["jobs"]) == 2
            assert result["total"] == 2
            mock_service.get_job_history.assert_called_once_with(db=mock_db, limit=10, offset=0)


class TestBatchImportOperations:
    """Test suite for batch import operations"""
    
    @pytest.fixture
    def mock_db(self):
        return AsyncMock(spec=AsyncSession)
    
    @pytest.mark.asyncio
    async def test_import_nodes_success(self, mock_db):
        """Test successful nodes import"""
        import_data = {
            "nodes": [
                {"id": "node_1", "type": "test", "properties": {"name": "Test Node"}},
                {"id": "node_2", "type": "test", "properties": {"name": "Test Node 2"}}
            ]
        }
        
        with patch('src.api.batch.batch_processing_service') as mock_service:
            mock_service.import_nodes.return_value = {
                "imported_count": 2,
                "skipped_count": 0,
                "errors": []
            }
            
            result = await import_nodes(import_data, mock_db)
            
            assert result["imported_count"] == 2
            assert result["skipped_count"] == 0
            mock_service.import_nodes.assert_called_once_with(
                nodes=import_data["nodes"], db=mock_db
            )
    
    @pytest.mark.asyncio
    async def test_import_relationships_success(self, mock_db):
        """Test successful relationships import"""
        import_data = {
            "relationships": [
                {"source": "node_1", "target": "node_2", "type": "test_rel"},
                {"source": "node_2", "target": "node_3", "type": "test_rel"}
            ]
        }
        
        with patch('src.api.batch.batch_processing_service') as mock_service:
            mock_service.import_relationships.return_value = {
                "imported_count": 2,
                "skipped_count": 0,
                "errors": []
            }
            
            result = await import_relationships(import_data, mock_db)
            
            assert result["imported_count"] == 2
            assert result["skipped_count"] == 0
            mock_service.import_relationships.assert_called_once_with(
                relationships=import_data["relationships"], db=mock_db
            )
    
    @pytest.mark.asyncio
    async def test_import_nodes_with_errors(self, mock_db):
        """Test nodes import with validation errors"""
        import_data = {
            "nodes": [
                {"id": "node_1", "type": "test"},  # Missing required properties
                {"id": "node_2", "type": "test", "properties": {"name": "Valid Node"}}
            ]
        }
        
        with patch('src.api.batch.batch_processing_service') as mock_service:
            mock_service.import_nodes.return_value = {
                "imported_count": 1,
                "skipped_count": 1,
                "errors": ["node_1: missing required properties"]
            }
            
            result = await import_nodes(import_data, mock_db)
            
            assert result["imported_count"] == 1
            assert result["skipped_count"] == 1
            assert len(result["errors"]) == 1


class TestBatchExportOperations:
    """Test suite for batch export operations"""
    
    @pytest.fixture
    def mock_db(self):
        return AsyncMock(spec=AsyncSession)
    
    @pytest.mark.asyncio
    async def test_export_graph_success(self, mock_db):
        """Test successful graph export"""
        export_params = {
            "format": "json",
            "include_relationships": True,
            "node_types": ["test"],
            "limit": 1000
        }
        
        with patch('src.api.batch.batch_processing_service') as mock_service:
            mock_service.export_graph.return_value = {
                "nodes": [{"id": "node_1", "type": "test"}],
                "relationships": [{"source": "node_1", "target": "node_2"}],
                "export_time": "2023-01-01T00:00:00Z"
            }
            
            result = await export_graph(export_params, mock_db)
            
            assert "nodes" in result
            assert "relationships" in result
            assert "export_time" in result
            mock_service.export_graph.assert_called_once_with(**export_params, db=mock_db)
    
    @pytest.mark.asyncio
    async def test_export_graph_different_formats(self, mock_db):
        """Test graph export in different formats"""
        formats = ["json", "csv", "xml", "graphml"]
        
        with patch('src.api.batch.batch_processing_service') as mock_service:
            for fmt in formats:
                mock_service.export_graph.return_value = {
                    "format": fmt,
                    "data": f"mock_data_in_{fmt}"
                }
                
                result = await export_graph({"format": fmt}, mock_db)
                assert result["format"] == fmt


class TestBatchDeleteOperations:
    """Test suite for batch delete operations"""
    
    @pytest.fixture
    def mock_db(self):
        return AsyncMock(spec=AsyncSession)
    
    @pytest.mark.asyncio
    async def test_batch_delete_nodes_success(self, mock_db):
        """Test successful batch node deletion"""
        delete_params = {
            "node_ids": ["node_1", "node_2", "node_3"],
            "delete_relationships": True,
            "batch_size": 100
        }
        
        with patch('src.api.batch.batch_processing_service') as mock_service:
            mock_service.delete_nodes.return_value = {
                "deleted_count": 3,
                "skipped_count": 0,
                "errors": []
            }
            
            result = await batch_delete_nodes(delete_params, mock_db)
            
            assert result["deleted_count"] == 3
            assert result["skipped_count"] == 0
            mock_service.delete_nodes.assert_called_once_with(**delete_params, db=mock_db)
    
    @pytest.mark.asyncio
    async def test_batch_delete_nodes_with_errors(self, mock_db):
        """Test batch node deletion with errors"""
        delete_params = {
            "node_ids": ["node_1", "nonexistent_node"],
            "delete_relationships": True
        }
        
        with patch('src.api.batch.batch_processing_service') as mock_service:
            mock_service.delete_nodes.return_value = {
                "deleted_count": 1,
                "skipped_count": 1,
                "errors": ["nonexistent_node: node not found"]
            }
            
            result = await batch_delete_nodes(delete_params, mock_db)
            
            assert result["deleted_count"] == 1
            assert result["skipped_count"] == 1
            assert len(result["errors"]) == 1


class TestBatchValidationOperations:
    """Test suite for batch validation operations"""
    
    @pytest.fixture
    def mock_db(self):
        return AsyncMock(spec=AsyncSession)
    
    @pytest.mark.asyncio
    async def test_batch_validate_graph_success(self, mock_db):
        """Test successful graph validation"""
        validation_params = {
            "validate_nodes": True,
            "validate_relationships": True,
            "check_duplicates": True,
            "sample_size": 1000
        }
        
        with patch('src.api.batch.batch_processing_service') as mock_service:
            mock_service.validate_graph.return_value = {
                "validation_passed": True,
                "total_nodes_checked": 500,
                "total_relationships_checked": 800,
                "issues_found": [],
                "warnings": []
            }
            
            result = await batch_validate_graph(validation_params, mock_db)
            
            assert result["validation_passed"] is True
            assert result["total_nodes_checked"] == 500
            assert result["total_relationships_checked"] == 800
            mock_service.validate_graph.assert_called_once_with(**validation_params, db=mock_db)
    
    @pytest.mark.asyncio
    async def test_batch_validate_graph_with_issues(self, mock_db):
        """Test graph validation with issues found"""
        validation_params = {"validate_nodes": True}
        
        with patch('src.api.batch.batch_processing_service') as mock_service:
            mock_service.validate_graph.return_value = {
                "validation_passed": False,
                "total_nodes_checked": 100,
                "issues_found": [
                    {"node_id": "node_1", "issue": "missing_required_field"},
                    {"node_id": "node_2", "issue": "invalid_data_type"}
                ],
                "warnings": [
                    {"node_id": "node_3", "warning": "deprecated_property"}
                ]
            }
            
            result = await batch_validate_graph(validation_params, mock_db)
            
            assert result["validation_passed"] is False
            assert len(result["issues_found"]) == 2
            assert len(result["warnings"]) == 1


class TestBatchUtilityEndpoints:
    """Test suite for batch utility endpoints"""
    
    @pytest.fixture
    def mock_db(self):
        return AsyncMock(spec=AsyncSession)
    
    @pytest.mark.asyncio
    async def test_get_operation_types(self):
        """Test operation types endpoint"""
        result = await get_operation_types()
        
        assert "operation_types" in result
        assert len(result["operation_types"]) > 0
        assert all(isinstance(op["name"], str) for op in result["operation_types"])
        assert all(isinstance(op["description"], str) for op in result["operation_types"])
    
    @pytest.mark.asyncio
    async def test_get_processing_modes(self):
        """Test processing modes endpoint"""
        result = await get_processing_modes()
        
        assert "processing_modes" in result
        assert len(result["processing_modes"]) > 0
        assert all(isinstance(mode["name"], str) for mode in result["processing_modes"])
        assert all(isinstance(mode["description"], str) for mode in result["processing_modes"])
    
    @pytest.mark.asyncio
    async def test_get_status_summary(self, mock_db):
        """Test status summary endpoint"""
        with patch('src.api.batch.batch_processing_service') as mock_service:
            mock_service.get_status_summary.return_value = {
                "total_jobs": 100,
                "active_jobs": 5,
                "completed_jobs": 90,
                "failed_jobs": 3,
                "paused_jobs": 2,
                "average_processing_time": 45.5
            }
            
            result = await get_status_summary(mock_db)
            
            assert result["total_jobs"] == 100
            assert result["active_jobs"] == 5
            assert result["completed_jobs"] == 90
            assert result["failed_jobs"] == 3
            assert result["paused_jobs"] == 2
            assert result["average_processing_time"] == 45.5
    
    @pytest.mark.asyncio
    async def test_get_performance_stats(self, mock_db):
        """Test performance statistics endpoint"""
        with patch('src.api.batch.batch_processing_service') as mock_service:
            mock_service.get_performance_stats.return_value = {
                "jobs_processed_today": 25,
                "average_job_duration": 120.5,
                "success_rate": 95.0,
                "peak_concurrent_jobs": 8,
                "system_load": 45.2,
                "memory_usage": 1024
            }
            
            result = await get_performance_stats(mock_db)
            
            assert result["jobs_processed_today"] == 25
            assert result["average_job_duration"] == 120.5
            assert result["success_rate"] == 95.0
            assert result["peak_concurrent_jobs"] == 8


class TestBatchErrorHandling:
    """Test suite for error handling scenarios"""
    
    @pytest.fixture
    def mock_db(self):
        return AsyncMock(spec=AsyncSession)
    
    @pytest.mark.asyncio
    async def test_job_not_found_error(self, mock_db):
        """Test handling of non-existent job"""
        with patch('src.api.batch.batch_processing_service') as mock_service:
            mock_service.get_job_status.side_effect = Exception("Job not found")
            
            with pytest.raises(Exception):
                await get_job_status("nonexistent_job", mock_db)
    
    @pytest.mark.asyncio
    async def test_service_timeout_error(self, mock_db):
        """Test handling of service timeout"""
        with patch('src.api.batch.batch_processing_service') as mock_service:
            mock_service.submit_job.side_effect = asyncio.TimeoutError("Service timeout")
            
            with pytest.raises(asyncio.TimeoutError):
                await submit_batch_job({"operation_type": "import_nodes"}, mock_db)
    
    @pytest.mark.asyncio
    async def test_database_connection_error(self, mock_db):
        """Test handling of database connection errors"""
        with patch('src.api.batch.batch_processing_service') as mock_service:
            mock_service.get_active_jobs.side_effect = Exception("Database connection failed")
            
            with pytest.raises(Exception):
                await get_active_jobs(mock_db)
    
    @pytest.mark.asyncio
    async def test_invalid_json_data(self, mock_db):
        """Test handling of invalid JSON data"""
        invalid_data = {"invalid": "data structure"}
        
        with pytest.raises(Exception):  # Should raise validation error
            await import_nodes(invalid_data, mock_db)
    
    @pytest.mark.asyncio
    async def test_insufficient_permissions_error(self, mock_db):
        """Test handling of permission errors"""
        with patch('src.api.batch.batch_processing_service') as mock_service:
            mock_service.delete_nodes.side_effect = PermissionError("Insufficient permissions")
            
            with pytest.raises(PermissionError):
                await batch_delete_nodes({"node_ids": ["node_1"]}, mock_db)


class TestBatchConcurrentOperations:
    """Test suite for concurrent batch operations"""
    
    @pytest.fixture
    def mock_db(self):
        return AsyncMock(spec=AsyncSession)
    
    @pytest.mark.asyncio
    async def test_concurrent_job_submission(self, mock_db):
        """Test submitting multiple jobs concurrently"""
        job_data = [
            {"operation_type": "import_nodes", "parameters": {"batch": i}}
            for i in range(5)
        ]
        
        with patch('src.api.batch.batch_processing_service') as mock_service:
            mock_service.submit_job.side_effect = [f"job_{i}" for i in range(5)]
            
            # Submit jobs concurrently
            tasks = [
                submit_batch_job(data, mock_db) 
                for data in job_data
            ]
            results = await asyncio.gather(*tasks)
            
            assert len(results) == 5
            assert all(result["status"] == "submitted" for result in results)
            assert mock_service.submit_job.call_count == 5
    
    @pytest.mark.asyncio
    async def test_concurrent_status_checks(self, mock_db):
        """Test checking job status concurrently"""
        job_ids = ["job_1", "job_2", "job_3"]
        
        with patch('src.api.batch.batch_processing_service') as mock_service:
            mock_service.get_job_status.side_effect = [
                {"job_id": job_id, "status": "running"} 
                for job_id in job_ids
            ]
            
            # Check status concurrently
            tasks = [
                get_job_status(job_id, mock_db) 
                for job_id in job_ids
            ]
            results = await asyncio.gather(*tasks)
            
            assert len(results) == 3
            assert all(result["status"] == "running" for result in results)
    
    @pytest.mark.asyncio
    async def test_concurrent_job_control(self, mock_db):
        """Test concurrent job control operations"""
        job_id = "job_123"
        
        with patch('src.api.batch.batch_processing_service') as mock_service:
            mock_service.pause_job.return_value = True
            mock_service.resume_job.return_value = True
            mock_service.cancel_job.return_value = True
            
            # Execute control operations concurrently
            pause_task = pause_job(job_id, mock_db)
            resume_task = resume_job(job_id, mock_db)
            cancel_task = cancel_job(job_id, mock_db)
            
            results = await asyncio.gather(*tasks)
            
            assert len(results) == 3
            assert all(result["job_id"] == job_id for result in results)


class TestBatchPerformanceTests:
    """Test suite for performance-related scenarios"""
    
    @pytest.fixture
    def mock_db(self):
        return AsyncMock(spec=AsyncSession)
    
    @pytest.mark.asyncio
    async def test_large_batch_import(self, mock_db):
        """Test importing a large batch of nodes"""
        large_batch = {
            "nodes": [
                {"id": f"node_{i}", "type": "test", "properties": {"index": i}}
                for i in range(1000)
            ]
        }
        
        with patch('src.api.batch.batch_processing_service') as mock_service:
            mock_service.import_nodes.return_value = {
                "imported_count": 1000,
                "skipped_count": 0,
                "errors": [],
                "processing_time": 5.2
            }
            
            result = await import_nodes(large_batch, mock_db)
            
            assert result["imported_count"] == 1000
            assert result["processing_time"] > 0
            mock_service.import_nodes.assert_called_once_with(
                nodes=large_batch["nodes"], db=mock_db
            )
    
    @pytest.mark.asyncio
    async def test_batch_operation_memory_usage(self, mock_db):
        """Test memory usage during batch operations"""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss
        
        # Simulate a memory-intensive operation
        with patch('src.api.batch.batch_processing_service') as mock_service:
            mock_service.export_graph.return_value = {
                "nodes": [{"id": f"node_{i}"} for i in range(10000)],
                "memory_usage": "high"
            }
            
            result = await export_graph({"format": "json", "limit": 10000}, mock_db)
            
            final_memory = process.memory_info().rss
            memory_increase = final_memory - initial_memory
            
            assert len(result["nodes"]) == 10000
            assert memory_increase > 0  # Memory should increase during operation
    
    @pytest.mark.asyncio
    async def test_batch_processing_throughput(self, mock_db):
        """Test batch processing throughput metrics"""
        with patch('src.api.batch.batch_processing_service') as mock_service:
            mock_service.get_performance_stats.return_value = {
                "jobs_per_hour": 120,
                "records_per_second": 500,
                "average_response_time": 0.5,
                "peak_throughput": 1000
            }
            
            result = await get_performance_stats(mock_db)
            
            assert result["jobs_per_hour"] == 120
            assert result["records_per_second"] == 500
            assert result["average_response_time"] == 0.5
            assert result["peak_throughput"] == 1000


class TestBatchIntegrationScenarios:
    """Test suite for integration scenarios"""
    
    @pytest.fixture
    def mock_db(self):
        return AsyncMock(spec=AsyncSession)
    
    @pytest.mark.asyncio
    async def test_complete_import_workflow(self, mock_db):
        """Test complete import workflow: nodes -> relationships -> validation"""
        # Step 1: Import nodes
        nodes_data = {
            "nodes": [
                {"id": "node_1", "type": "user"},
                {"id": "node_2", "type": "user"}
            ]
        }
        
        # Step 2: Import relationships
        relationships_data = {
            "relationships": [
                {"source": "node_1", "target": "node_2", "type": "knows"}
            ]
        }
        
        with patch('src.api.batch.batch_processing_service') as mock_service:
            # Mock node import
            mock_service.import_nodes.return_value = {
                "imported_count": 2, "skipped_count": 0, "errors": []
            }
            
            # Mock relationship import
            mock_service.import_relationships.return_value = {
                "imported_count": 1, "skipped_count": 0, "errors": []
            }
            
            # Mock validation
            mock_service.validate_graph.return_value = {
                "validation_passed": True, "issues_found": []
            }
            
            # Execute workflow
            nodes_result = await import_nodes(nodes_data, mock_db)
            relationships_result = await import_relationships(relationships_data, mock_db)
            validation_result = await batch_validate_graph({}, mock_db)
            
            # Verify results
            assert nodes_result["imported_count"] == 2
            assert relationships_result["imported_count"] == 1
            assert validation_result["validation_passed"] is True
    
    @pytest.mark.asyncio
    async def test_error_recovery_workflow(self, mock_db):
        """Test error recovery in batch operations"""
        with patch('src.api.batch.batch_processing_service') as mock_service:
            # Simulate initial failure
            mock_service.import_nodes.return_value = {
                "imported_count": 5,
                "skipped_count": 2,
                "errors": ["invalid_data_format", "missing_required_fields"]
            }
            
            # First import attempt with errors
            result = await import_nodes({"nodes": []}, mock_db)
            
            assert result["imported_count"] == 5
            assert result["skipped_count"] == 2
            assert len(result["errors"]) == 2
            
            # Second attempt after fixing data
            mock_service.import_nodes.return_value = {
                "imported_count": 7,
                "skipped_count": 0,
                "errors": []
            }
            
            result = await import_nodes({"nodes": []}, mock_db)
            
            assert result["imported_count"] == 7
            assert result["skipped_count"] == 0
            assert len(result["errors"]) == 0
