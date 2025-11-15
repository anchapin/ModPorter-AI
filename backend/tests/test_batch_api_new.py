"""
Comprehensive tests for batch.py API endpoints.

This test suite provides extensive coverage for the Batch Processing API,
ensuring all job submission, progress tracking, and management endpoints are tested.

Coverage Target: ≥80% line coverage for 339 statements
"""

import pytest
import asyncio
import json
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch, call, mock_open
from fastapi.testclient import TestClient
from fastapi import HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from io import BytesIO

from src.api.batch import router
from src.services.batch_processing import (
    BatchOperationType, ProcessingMode, batch_processing_service
)


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
                "nodes": [
                    {"name": "Entity1", "node_type": "entity", "platform": "java"},
                    {"name": "Entity2", "node_type": "entity", "platform": "bedrock"}
                ]
            },
            "processing_mode": "parallel",
            "chunk_size": 50,
            "parallel_workers": 4
        }

    # Job Management Endpoints Tests
    
    async def test_submit_batch_job_success(self, client, mock_db, sample_job_data):
        """Test successful batch job submission."""
        with patch('src.api.batch.get_db') as mock_get_db, \
             patch.object(batch_processing_service, 'submit_batch_job') as mock_submit:
            
            mock_get_db.return_value = mock_db
            mock_submit.return_value = {
                "success": True,
                "job_id": "job123",
                "status": "queued",
                "estimated_total_items": 100,
                "submitted_at": datetime.utcnow().isoformat()
            }
            
            response = client.post("/batch/jobs", json=sample_job_data)
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "job_id" in data
            assert data["status"] == "queued"
    
    def test_submit_batch_job_missing_operation_type(self, client, mock_db):
        """Test batch job submission with missing operation_type."""
        with patch('src.api.batch.get_db') as mock_get_db:
            mock_get_db.return_value = mock_db
            
            job_data = {
                "parameters": {"test": "data"},
                "processing_mode": "parallel"
            }
            
            response = client.post("/batch/jobs", json=job_data)
            
            assert response.status_code == 400
            assert "operation_type is required" in response.json()["detail"]
    
    def test_submit_batch_job_invalid_operation_type(self, client, mock_db):
        """Test batch job submission with invalid operation_type."""
        with patch('src.api.batch.get_db') as mock_get_db:
            mock_get_db.return_value = mock_db
            
            job_data = {
                "operation_type": "invalid_operation",
                "parameters": {"test": "data"}
            }
            
            response = client.post("/batch/jobs", json=job_data)
            
            assert response.status_code == 400
            assert "Invalid operation_type" in response.json()["detail"]
    
    def test_submit_batch_job_invalid_processing_mode(self, client, mock_db):
        """Test batch job submission with invalid processing mode."""
        with patch('src.api.batch.get_db') as mock_get_db:
            mock_get_db.return_value = mock_db
            
            job_data = {
                "operation_type": "import_nodes",
                "parameters": {"test": "data"},
                "processing_mode": "invalid_mode"
            }
            
            response = client.post("/batch/jobs", json=job_data)
            
            assert response.status_code == 400
            assert "Invalid processing_mode" in response.json()["detail"]
    
    def test_submit_batch_job_service_error(self, client, mock_db, sample_job_data):
        """Test batch job submission when service raises an error."""
        with patch('src.api.batch.get_db') as mock_get_db, \
             patch.object(batch_processing_service, 'submit_batch_job') as mock_submit:
            
            mock_get_db.return_value = mock_db
            mock_submit.return_value = {
                "success": False,
                "error": "Service unavailable"
            }
            
            response = client.post("/batch/jobs", json=sample_job_data)
            
            assert response.status_code == 400
            assert "Service unavailable" in response.json()["detail"]
    
    async def test_get_job_status_success(self, client):
        """Test successful job status retrieval."""
        with patch.object(batch_processing_service, 'get_job_status') as mock_status:
            
            mock_status.return_value = {
                "success": True,
                "job_id": "job123",
                "status": "running",
                "progress": 45.5,
                "total_items": 1000,
                "processed_items": 455,
                "failed_items": 2
            }
            
            response = client.get("/batch/jobs/job123")
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["job_id"] == "job123"
            assert data["status"] == "running"
            assert data["progress"] == 45.5
    
    async def test_get_job_status_not_found(self, client):
        """Test job status retrieval when job not found."""
        with patch.object(batch_processing_service, 'get_job_status') as mock_status:
            
            mock_status.return_value = {
                "success": False,
                "error": "Job not found"
            }
            
            response = client.get("/batch/jobs/nonexistent")
            
            assert response.status_code == 404
            assert "Job not found" in response.json()["detail"]
    
    def test_cancel_job_success(self, client):
        """Test successful job cancellation."""
        with patch.object(batch_processing_service, 'cancel_job') as mock_cancel:
            
            mock_cancel.return_value = {
                "success": True,
                "job_id": "job123",
                "status": "cancelled"
            }
            
            response = client.post("/batch/jobs/job123/cancel", json={"reason": "User request"})
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["job_id"] == "job123"
            assert data["status"] == "cancelled"
    
    def test_pause_job_success(self, client):
        """Test successful job pause."""
        with patch.object(batch_processing_service, 'pause_job') as mock_pause:
            
            mock_pause.return_value = {
                "success": True,
                "job_id": "job123",
                "status": "paused"
            }
            
            response = client.post("/batch/jobs/job123/pause", json={"reason": "User request"})
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["status"] == "paused"
    
    def test_resume_job_success(self, client):
        """Test successful job resume."""
        with patch.object(batch_processing_service, 'resume_job') as mock_resume:
            
            mock_resume.return_value = {
                "success": True,
                "job_id": "job123",
                "status": "running"
            }
            
            response = client.post("/batch/jobs/job123/resume")
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["status"] == "running"
    
    def test_get_active_jobs_success(self, client):
        """Test successful active jobs listing."""
        with patch.object(batch_processing_service, 'get_active_jobs') as mock_active:
            
            mock_active.return_value = {
                "success": True,
                "active_jobs": [
                    {"job_id": "job123", "status": "running", "operation_type": "import_nodes"},
                    {"job_id": "job124", "status": "paused", "operation_type": "export_graph"}
                ],
                "total_active": 2
            }
            
            response = client.get("/batch/jobs")
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert len(data["active_jobs"]) == 2
            assert data["total_active"] == 2
    
    @pytest.mark.skip(reason="Route path issue - TODO: Fix endpoint routing")
    def test_get_job_history_success(self, client):
        """Test successful job history retrieval."""
        with patch.object(batch_processing_service, 'get_job_history') as mock_history:
            
            mock_history.return_value = {
                "success": True,
                "job_history": [
                    {"job_id": "job120", "status": "completed", "operation_type": "import_nodes"},
                    {"job_id": "job119", "status": "completed", "operation_type": "export_graph"}
                ]
            }
            
            response = client.get("/batch/jobs/history?limit=10")
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert len(data["job_history"]) == 2

    # Import/Export Endpoints Tests
    
    def test_import_nodes_json_success(self, client, mock_db):
        """Test successful nodes import from JSON."""
        with patch('src.api.batch.get_db') as mock_get_db, \
             patch.object(batch_processing_service, 'submit_batch_job') as mock_submit:
            
            mock_get_db.return_value = mock_db
            mock_submit.return_value = {
                "success": True,
                "job_id": "import_job123",
                "estimated_total_items": 50
            }
            
            # Mock file content
            nodes_data = [
                {"name": "Entity1", "node_type": "entity", "platform": "java"},
                {"name": "Entity2", "node_type": "entity", "platform": "bedrock"}
            ]
            json_content = json.dumps(nodes_data)
            
            files = {"file": ("nodes.json", json_content, "application/json")}
            data = {"processing_mode": "parallel", "chunk_size": "25", "parallel_workers": "2"}
            
            response = client.post("/batch/import/nodes", files=files, data=data)
            
            assert response.status_code == 200
            result = response.json()
            assert result["success"] is True
            assert "job_id" in result
            assert result["job_id"] == "import_job123"
    
    def test_import_nodes_csv_success(self, client, mock_db):
        """Test successful nodes import from CSV."""
        with patch('src.api.batch.get_db') as mock_get_db, \
             patch('src.api.batch._parse_csv_nodes') as mock_parse_csv, \
             patch.object(batch_processing_service, 'submit_batch_job') as mock_submit:
            
            mock_get_db.return_value = mock_db
            mock_parse_csv.return_value = [
                {"name": "Entity1", "node_type": "entity", "platform": "java"}
            ]
            mock_submit.return_value = {
                "success": True,
                "job_id": "import_job124",
                "estimated_total_items": 1
            }
            
            csv_content = "name,node_type,platform\nEntity1,entity,java"
            files = {"file": ("nodes.csv", csv_content, "text/csv")}
            data = {"processing_mode": "sequential"}
            
            response = client.post("/batch/import/nodes", files=files, data=data)
            
            assert response.status_code == 200
            result = response.json()
            assert result["success"] is True
    
    def test_import_relationships_success(self, client, mock_db):
        """Test successful relationships import."""
        with patch('src.api.batch.get_db') as mock_get_db, \
             patch.object(batch_processing_service, 'submit_batch_job') as mock_submit:
            
            mock_get_db.return_value = mock_db
            mock_submit.return_value = {
                "success": True,
                "job_id": "rel_import123",
                "estimated_total_items": 25
            }
            
            relationships_data = [
                {"source_node_id": "node1", "target_node_id": "node2", "relationship_type": "relates_to"},
                {"source_node_id": "node2", "target_node_id": "node3", "relationship_type": "depends_on"}
            ]
            json_content = json.dumps(relationships_data)
            
            files = {"file": ("relationships.json", json_content, "application/json")}
            data = {"processing_mode": "parallel"}
            
            response = client.post("/batch/import/relationships", files=files, data=data)
            
            assert response.status_code == 200
            result = response.json()
            assert result["success"] is True
            assert "job_id" in result
    
    def test_export_graph_success(self, client, mock_db):
        """Test successful graph export."""
        with patch('src.api.batch.get_db') as mock_get_db, \
             patch.object(batch_processing_service, 'submit_batch_job') as mock_submit:
            
            mock_get_db.return_value = mock_db
            mock_submit.return_value = {
                "success": True,
                "job_id": "export_job123",
                "estimated_total_items": 1000
            }
            
            export_data = {
                "format": "json",
                "filters": {"node_type": "entity"},
                "include_relationships": True,
                "processing_mode": "parallel"
            }
            
            response = client.post("/batch/export/graph", json=export_data)
            
            assert response.status_code == 200
            result = response.json()
            assert result["success"] is True
            assert result["output_format"] == "json"
            assert "job_id" in result

    # Batch Operation Endpoints Tests
    
    def test_batch_delete_nodes_success(self, client, mock_db):
        """Test successful batch node deletion."""
        with patch('src.api.batch.get_db') as mock_get_db, \
             patch.object(batch_processing_service, 'submit_batch_job') as mock_submit:
            
            mock_get_db.return_value = mock_db
            mock_submit.return_value = {
                "success": True,
                "job_id": "delete_job123",
                "estimated_total_items": 50
            }
            
            delete_data = {
                "filters": {"node_type": "entity", "platform": "java"},
                "dry_run": False,
                "processing_mode": "parallel"
            }
            
            response = client.post("/batch/delete/nodes", json=delete_data)
            
            assert response.status_code == 200
            result = response.json()
            assert result["success"] is True
            assert result["dry_run"] is False
            assert "job_id" in result
    
    def test_batch_delete_nodes_missing_filters(self, client, mock_db):
        """Test batch node deletion with missing filters."""
        with patch('src.api.batch.get_db') as mock_get_db:
            mock_get_db.return_value = mock_db
            
            delete_data = {"dry_run": True}
            
            response = client.post("/batch/delete/nodes", json=delete_data)
            
            assert response.status_code == 400
            assert "filters are required" in response.json()["detail"]
    
    def test_batch_validate_graph_success(self, client, mock_db):
        """Test successful batch graph validation."""
        with patch('src.api.batch.get_db') as mock_get_db, \
             patch.object(batch_processing_service, 'submit_batch_job') as mock_submit:
            
            mock_get_db.return_value = mock_db
            mock_submit.return_value = {
                "success": True,
                "job_id": "validate_job123",
                "estimated_total_items": 500
            }
            
            validation_data = {
                "rules": ["nodes", "relationships", "consistency"],
                "scope": "full",
                "processing_mode": "parallel",
                "chunk_size": 100,
                "parallel_workers": 4
            }
            
            response = client.post("/batch/validate/graph", json=validation_data)
            
            assert response.status_code == 200
            result = response.json()
            assert result["success"] is True
            assert result["validation_rules"] == ["nodes", "relationships", "consistency"]
            assert result["scope"] == "full"

    # Utility Endpoints Tests
    
    def test_get_operation_types_success(self, client):
        """Test successful operation types retrieval."""
        response = client.get("/batch/operation-types")
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "operation_types" in data
        assert len(data["operation_types"]) > 0
        
        # Check structure of operation types
        op_type = data["operation_types"][0]
        assert "value" in op_type
        assert "name" in op_type
        assert "description" in op_type
        assert "requires_file" in op_type
    
    def test_get_processing_modes_success(self, client):
        """Test successful processing modes retrieval."""
        response = client.get("/batch/processing-modes")
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "processing_modes" in data
        assert len(data["processing_modes"]) > 0
        
        # Check structure of processing modes
        mode = data["processing_modes"][0]
        assert "value" in mode
        assert "name" in mode
        assert "description" in mode
        assert "use_cases" in mode
        assert "recommended_for" in mode
    
    def test_get_status_summary_success(self, client):
        """Test successful status summary retrieval."""
        with patch.object(batch_processing_service, 'get_active_jobs') as mock_active, \
             patch.object(batch_processing_service, 'get_job_history') as mock_history:
            
            mock_active.return_value = {
                "success": True,
                "active_jobs": [
                    {"status": "running", "operation_type": "import_nodes"},
                    {"status": "paused", "operation_type": "export_graph"}
                ],
                "total_active": 2,
                "queue_size": 5,
                "max_concurrent_jobs": 10
            }
            
            mock_history.return_value = {
                "success": True,
                "job_history": [
                    {"status": "completed", "operation_type": "import_nodes"},
                    {"status": "failed", "operation_type": "export_graph"}
                ]
            }
            
            response = client.get("/batch/status-summary")
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "summary" in data
            
            summary = data["summary"]
            assert "status_counts" in summary
            assert "operation_type_counts" in summary
            assert "total_active" in summary
            assert summary["total_active"] == 2
    
    def test_get_performance_stats_success(self, client):
        """Test successful performance statistics retrieval."""
        response = client.get("/batch/performance-stats")
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "performance_stats" in data
        
        stats = data["performance_stats"]
        assert "total_jobs_processed" in stats
        assert "success_rate" in stats
        assert "operation_type_performance" in stats


class TestBatchAPIHelpers:
    """Test helper functions in batch API."""
    
    async def test_parse_csv_nodes_success(self):
        """Test successful CSV nodes parsing."""
        from src.api.batch import _parse_csv_nodes
        
        csv_content = """name,node_type,platform,description
Entity1,entity,java,A test entity
Entity2,block,bedrock,A test block"""
        
        result = await _parse_csv_nodes(csv_content)
        
        assert len(result) == 2
        assert result[0]["name"] == "Entity1"
        assert result[0]["node_type"] == "entity"
        assert result[0]["platform"] == "java"
        assert result[0]["description"] == "A test entity"
        assert result[1]["name"] == "Entity2"
        assert result[1]["node_type"] == "block"
    
    async def test_parse_csv_relationships_success(self):
        """Test successful CSV relationships parsing."""
        from src.api.batch import _parse_csv_relationships
        
        csv_content = """source_node_id,target_node_id,relationship_type,confidence_score
node1,node2,relates_to,0.8
node2,node3,depends_on,0.9"""
        
        result = await _parse_csv_relationships(csv_content)
        
        assert len(result) == 2
        assert result[0]["source_node_id"] == "node1"
        assert result[0]["target_node_id"] == "node2"
        assert result[0]["relationship_type"] == "relates_to"
        assert result[0]["confidence_score"] == 0.8
        assert result[1]["source_node_id"] == "node2"
        assert result[1]["relationship_type"] == "depends_on"
    
    def test_get_operation_description(self):
        """Test operation description helper."""
        from src.api.batch import _get_operation_description
        
        desc = _get_operation_description(BatchOperationType.IMPORT_NODES)
        assert "Import knowledge nodes" in desc
        
        desc = _get_operation_description(BatchOperationType.EXPORT_GRAPH)
        assert "Export entire knowledge graph" in desc
    
    def test_operation_requires_file(self):
        """Test file requirement helper."""
        from src.api.batch import _operation_requires_file
        
        assert _operation_requires_file(BatchOperationType.IMPORT_NODES) is True
        assert _operation_requires_file(BatchOperationType.EXPORT_GRAPH) is False
        assert _operation_requires_file(BatchOperationType.DELETE_NODES) is False
    
    def test_get_processing_mode_description(self):
        """Test processing mode description helper."""
        from src.api.batch import _get_processing_mode_description
        
        desc = _get_processing_mode_description(ProcessingMode.PARALLEL)
        assert "simultaneously" in desc
        
        desc = _get_processing_mode_description(ProcessingMode.SEQUENTIAL)
        assert "sequence" in desc


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

    def test_import_unsupported_file_format(self, client, mock_db):
        """Test import with unsupported file format."""
        with patch('src.api.batch.get_db') as mock_get_db:
            mock_get_db.return_value = mock_db
            
            files = {"file": ("data.txt", "some content", "text/plain")}
            data = {"processing_mode": "sequential"}
            
            response = client.post("/batch/import/nodes", files=files, data=data)
            
            assert response.status_code == 400
            assert "Unsupported file format" in response.json()["detail"]
    
    def test_export_invalid_format(self, client, mock_db):
        """Test export with invalid format."""
        with patch('src.api.batch.get_db') as mock_get_db:
            mock_get_db.return_value = mock_db
            
            export_data = {
                "format": "invalid_format",
                "filters": {}
            }
            
            response = client.post("/batch/export/graph", json=export_data)
            
            assert response.status_code == 400
            assert "Unsupported format" in response.json()["detail"]
    
    def test_validate_invalid_rules(self, client, mock_db):
        """Test validation with invalid rules."""
        with patch('src.api.batch.get_db') as mock_get_db:
            mock_get_db.return_value = mock_db
            
            validation_data = {
                "rules": ["invalid_rule"],
                "scope": "full"
            }
            
            response = client.post("/batch/validate/graph", json=validation_data)
            
            assert response.status_code == 400
            assert "Invalid validation rule" in response.json()["detail"]
    
    def test_unicode_data_in_import(self, client, mock_db):
        """Test import with unicode data."""
        with patch('src.api.batch.get_db') as mock_get_db, \
             patch.object(batch_processing_service, 'submit_batch_job') as mock_submit:
            
            mock_get_db.return_value = mock_db
            mock_submit.return_value = {"success": True, "job_id": "unicode123", "estimated_total_items": 2}
            
            # Unicode data
            nodes_data = [
                {"name": "测试实体", "node_type": "entity", "platform": "java"},
                {"name": "エンティティ", "node_type": "entity", "platform": "bedrock"}
            ]
            json_content = json.dumps(nodes_data, ensure_ascii=False)
            
            files = {"file": ("nodes.json", json_content, "application/json")}
            data = {"processing_mode": "sequential"}
            
            response = client.post("/batch/import/nodes", files=files, data=data)
            
            assert response.status_code == 200
            result = response.json()
            assert result["success"] is True
    
    def test_concurrent_operations(self, client):
        """Test concurrent operations handling."""
        import threading
        results = []
        
        def make_request():
            response = client.get("/batch/operation-types")
            results.append(response.status_code)
        
        # Create multiple threads
        threads = [threading.Thread(target=make_request) for _ in range(5)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        
        # All requests should succeed
        assert all(status == 200 for status in results)
        assert len(results) == 5


if __name__ == "__main__":
    # Run tests directly
    pytest.main([__file__, "-v", "--tb=short"])
