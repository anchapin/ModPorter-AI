"""
Comprehensive tests for batch.py API module
Tests all batch processing endpoints including job management, import/export, and utility functions.
"""

import pytest
import json
from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient

from src.api.batch import router
from src.services.batch_processing import BatchOperationType, ProcessingMode

# Test client setup
client = TestClient(router)


class TestBatchJobManagement:
    """Test batch job management endpoints"""

    @pytest.mark.asyncio
    async def test_submit_batch_job_success(self):
        """Test successful batch job submission"""
        mock_service = AsyncMock()
        mock_service.submit_batch_job.return_value = {
            "success": True,
            "job_id": "job_123",
            "estimated_total_items": 1000,
            "status": "pending",
        }

        with patch("src.api.batch.batch_processing_service", mock_service):
            job_data = {
                "operation_type": "IMPORT_NODES",
                "parameters": {"test": "data"},
                "processing_mode": "sequential",
                "chunk_size": 100,
                "parallel_workers": 4,
            }

            response = client.post("/batch/jobs", json=job_data)

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "job_id" in data

    @pytest.mark.asyncio
    async def test_submit_batch_job_missing_operation_type(self):
        """Test batch job submission without operation type"""
        job_data = {"parameters": {"test": "data"}}

        response = client.post("/batch/jobs", json=job_data)

        assert response.status_code == 400
        assert "operation_type is required" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_submit_batch_job_invalid_operation_type(self):
        """Test batch job submission with invalid operation type"""
        job_data = {"operation_type": "INVALID_TYPE", "parameters": {"test": "data"}}

        response = client.post("/batch/jobs", json=job_data)

        assert response.status_code == 400
        assert "Invalid operation_type" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_submit_batch_job_invalid_processing_mode(self):
        """Test batch job submission with invalid processing mode"""
        job_data = {
            "operation_type": "IMPORT_NODES",
            "parameters": {"test": "data"},
            "processing_mode": "INVALID_MODE",
        }

        response = client.post("/batch/jobs", json=job_data)

        assert response.status_code == 400
        assert "Invalid processing_mode" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_submit_batch_job_service_failure(self):
        """Test batch job submission when service returns failure"""
        mock_service = AsyncMock()
        mock_service.submit_batch_job.return_value = {
            "success": False,
            "error": "Service unavailable",
        }

        with patch("src.api.batch.batch_processing_service", mock_service):
            job_data = {
                "operation_type": "IMPORT_NODES",
                "parameters": {"test": "data"},
            }

            response = client.post("/batch/jobs", json=job_data)

            assert response.status_code == 400
            assert "Service unavailable" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_get_job_status_success(self):
        """Test successful job status retrieval"""
        mock_service = AsyncMock()
        mock_service.get_job_status.return_value = {
            "success": True,
            "job_id": "job_123",
            "status": "running",
            "progress": 45.5,
            "items_processed": 455,
            "total_items": 1000,
        }

        with patch("src.api.batch.batch_processing_service", mock_service):
            response = client.get("/batch/jobs/job_123")

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["status"] == "running"

    @pytest.mark.asyncio
    async def test_get_job_status_not_found(self):
        """Test job status retrieval for non-existent job"""
        mock_service = AsyncMock()
        mock_service.get_job_status.return_value = {
            "success": False,
            "error": "Job not found",
        }

        with patch("src.api.batch.batch_processing_service", mock_service):
            response = client.get("/batch/jobs/nonexistent")

            assert response.status_code == 404
            assert "Job not found" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_cancel_job_success(self):
        """Test successful job cancellation"""
        mock_service = AsyncMock()
        mock_service.cancel_job.return_value = {
            "success": True,
            "job_id": "job_123",
            "status": "cancelled",
        }

        with patch("src.api.batch.batch_processing_service", mock_service):
            cancel_data = {"reason": "User request"}

            response = client.post("/batch/jobs/job_123/cancel", json=cancel_data)

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["status"] == "cancelled"

    @pytest.mark.asyncio
    async def test_cancel_job_with_default_reason(self):
        """Test job cancellation with default reason"""
        mock_service = AsyncMock()
        mock_service.cancel_job.return_value = {
            "success": True,
            "job_id": "job_123",
            "status": "cancelled",
        }

        with patch("src.api.batch.batch_processing_service", mock_service):
            response = client.post("/batch/jobs/job_123/cancel")

            assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_pause_job_success(self):
        """Test successful job pause"""
        mock_service = AsyncMock()
        mock_service.pause_job.return_value = {
            "success": True,
            "job_id": "job_123",
            "status": "paused",
        }

        with patch("src.api.batch.batch_processing_service", mock_service):
            pause_data = {"reason": "Maintenance"}

            response = client.post("/batch/jobs/job_123/pause", json=pause_data)

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["status"] == "paused"

    @pytest.mark.asyncio
    async def test_resume_job_success(self):
        """Test successful job resume"""
        mock_service = AsyncMock()
        mock_service.resume_job.return_value = {
            "success": True,
            "job_id": "job_123",
            "status": "running",
        }

        with patch("src.api.batch.batch_processing_service", mock_service):
            response = client.post("/batch/jobs/job_123/resume")

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["status"] == "running"

    @pytest.mark.asyncio
    async def test_get_active_jobs_success(self):
        """Test successful retrieval of active jobs"""
        mock_service = AsyncMock()
        mock_service.get_active_jobs.return_value = {
            "success": True,
            "active_jobs": [
                {
                    "job_id": "job_1",
                    "status": "running",
                    "operation_type": "IMPORT_NODES",
                },
                {
                    "job_id": "job_2",
                    "status": "pending",
                    "operation_type": "EXPORT_GRAPH",
                },
            ],
            "total_active": 2,
            "queue_size": 1,
            "max_concurrent_jobs": 5,
        }

        with patch("src.api.batch.batch_processing_service", mock_service):
            response = client.get("/batch/jobs")

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert len(data["active_jobs"]) == 2

    @pytest.mark.asyncio
    async def test_get_job_history_success(self):
        """Test successful retrieval of job history"""
        mock_service = AsyncMock()
        mock_service.get_job_history.return_value = {
            "success": True,
            "job_history": [
                {
                    "job_id": "job_completed_1",
                    "status": "completed",
                    "operation_type": "IMPORT_NODES",
                },
                {
                    "job_id": "job_failed_1",
                    "status": "failed",
                    "operation_type": "EXPORT_GRAPH",
                },
            ],
        }

        with patch("src.api.batch.batch_processing_service", mock_service):
            response = client.get("/batch/jobs/history?limit=50")

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert len(data["job_history"]) == 2

    @pytest.mark.asyncio
    async def test_get_job_history_with_operation_filter(self):
        """Test job history with operation type filter"""
        mock_service = AsyncMock()
        mock_service.get_job_history.return_value = {
            "success": True,
            "job_history": [
                {
                    "job_id": "job_1",
                    "status": "completed",
                    "operation_type": "IMPORT_NODES",
                }
            ],
        }

        with patch("src.api.batch.batch_processing_service", mock_service):
            response = client.get("/batch/jobs/history?operation_type=IMPORT_NODES")

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True

    @pytest.mark.asyncio
    async def test_get_job_history_invalid_operation_type(self):
        """Test job history with invalid operation type filter"""
        response = client.get("/batch/jobs/history?operation_type=INVALID_TYPE")

        assert response.status_code == 400
        assert "Invalid operation_type" in response.json()["detail"]


class TestBatchImportExport:
    """Test batch import/export endpoints"""

    @pytest.mark.asyncio
    async def test_import_nodes_json_success(self):
        """Test successful JSON nodes import"""
        mock_service = AsyncMock()
        mock_service.submit_batch_job.return_value = {
            "success": True,
            "job_id": "import_job_123",
            "estimated_total_items": 150,
        }

        with patch("src.api.batch.batch_processing_service", mock_service):
            # Create mock file upload
            test_data = {"nodes": [{"name": "test_node", "type": "mod"}]}
            files = {"file": ("test.json", json.dumps(test_data), "application/json")}

            response = client.post(
                "/batch/import/nodes",
                files=files,
                data={"processing_mode": "sequential"},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "job_id" in data

    @pytest.mark.asyncio
    async def test_import_nodes_csv_success(self):
        """Test successful CSV nodes import"""
        mock_service = AsyncMock()
        mock_service.submit_batch_job.return_value = {
            "success": True,
            "job_id": "csv_import_job_123",
            "estimated_total_items": 200,
        }

        with patch("src.api.batch.batch_processing_service", mock_service):
            # Mock CSV content
            csv_content = "name,node_type,platform\nmod1,mod,bedrock\nmod2,mod,java"

            files = {"file": ("test.csv", csv_content, "text/csv")}

            response = client.post(
                "/batch/import/nodes", files=files, data={"processing_mode": "parallel"}
            )

            assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_import_nodes_unsupported_format(self):
        """Test import with unsupported file format"""
        test_data = {"nodes": [{"name": "test"}]}
        files = {"file": ("test.txt", json.dumps(test_data), "text/plain")}

        response = client.post("/batch/import/nodes", files=files)

        assert response.status_code == 400
        assert "Unsupported file format" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_import_nodes_malformed_json(self):
        """Test import with malformed JSON"""
        files = {"file": ("test.json", "{invalid json}", "application/json")}

        response = client.post("/batch/import/nodes", files=files)

        assert response.status_code == 400
        assert "Failed to parse file" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_import_relationships_json_success(self):
        """Test successful JSON relationships import"""
        mock_service = AsyncMock()
        mock_service.submit_batch_job.return_value = {
            "success": True,
            "job_id": "rel_import_job_123",
            "estimated_total_items": 300,
        }

        with patch("src.api.batch.batch_processing_service", mock_service):
            test_data = {
                "relationships": [
                    {"source": "node1", "target": "node2", "type": "relates_to"}
                ]
            }
            files = {"file": ("rels.json", json.dumps(test_data), "application/json")}

            response = client.post("/batch/import/relationships", files=files)

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True

    @pytest.mark.asyncio
    async def test_export_graph_success(self):
        """Test successful graph export"""
        mock_service = AsyncMock()
        mock_service.submit_batch_job.return_value = {
            "success": True,
            "job_id": "export_job_123",
            "estimated_total_items": 500,
        }

        with patch("src.api.batch.batch_processing_service", mock_service):
            export_data = {
                "format": "json",
                "filters": {"platform": "java"},
                "include_relationships": True,
                "processing_mode": "chunked",
            }

            response = client.post("/batch/export/graph", json=export_data)

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["output_format"] == "json"

    @pytest.mark.asyncio
    async def test_export_graph_invalid_format(self):
        """Test export with invalid format"""
        export_data = {"format": "invalid_format", "filters": {}}

        response = client.post("/batch/export/graph", json=export_data)

        assert response.status_code == 400
        assert "Unsupported format" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_export_graph_invalid_processing_mode(self):
        """Test export with invalid processing mode"""
        export_data = {"format": "json", "processing_mode": "invalid_mode"}

        response = client.post("/batch/export/graph", json=export_data)

        assert response.status_code == 400
        assert "Invalid processing_mode" in response.json()["detail"]


class TestBatchOperations:
    """Test batch operation endpoints"""

    @pytest.mark.asyncio
    async def test_batch_delete_nodes_success(self):
        """Test successful batch node deletion"""
        mock_service = AsyncMock()
        mock_service.submit_batch_job.return_value = {
            "success": True,
            "job_id": "delete_job_123",
            "estimated_total_items": 100,
        }

        with patch("src.api.batch.batch_processing_service", mock_service):
            delete_data = {
                "filters": {"platform": "bedrock"},
                "dry_run": False,
                "processing_mode": "parallel",
            }

            response = client.post("/batch/delete/nodes", json=delete_data)

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["dry_run"] is False

    @pytest.mark.asyncio
    async def test_batch_delete_nodes_dry_run(self):
        """Test batch delete in dry run mode"""
        mock_service = AsyncMock()
        mock_service.submit_batch_job.return_value = {
            "success": True,
            "job_id": "dry_run_job_123",
            "estimated_total_items": 50,
        }

        with patch("src.api.batch.batch_processing_service", mock_service):
            delete_data = {"filters": {"node_type": "mod"}, "dry_run": True}

            response = client.post("/batch/delete/nodes", json=delete_data)

            assert response.status_code == 200
            data = response.json()
            assert data["dry_run"] is True

    @pytest.mark.asyncio
    async def test_batch_delete_nodes_no_filters(self):
        """Test batch delete without filters (should fail)"""
        delete_data = {"dry_run": True}

        response = client.post("/batch/delete/nodes", json=delete_data)

        assert response.status_code == 400
        assert "filters are required" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_batch_validate_graph_success(self):
        """Test successful graph validation"""
        mock_service = AsyncMock()
        mock_service.submit_batch_job.return_value = {
            "success": True,
            "job_id": "validate_job_123",
            "estimated_total_items": 1000,
        }

        with patch("src.api.batch.batch_processing_service", mock_service):
            validation_data = {
                "rules": ["nodes", "relationships"],
                "scope": "full",
                "processing_mode": "parallel",
            }

            response = client.post("/batch/validate/graph", json=validation_data)

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "nodes" in data["validation_rules"]

    @pytest.mark.asyncio
    async def test_batch_validate_graph_invalid_rules(self):
        """Test validation with invalid rules"""
        validation_data = {"rules": ["invalid_rule", "nodes"], "scope": "full"}

        response = client.post("/batch/validate/graph", json=validation_data)

        assert response.status_code == 400
        assert "Invalid validation rule" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_batch_validate_graph_all_rules(self):
        """Test validation with all valid rules"""
        mock_service = AsyncMock()
        mock_service.submit_batch_job.return_value = {
            "success": True,
            "job_id": "validate_all_job_123",
            "estimated_total_items": 2000,
        }

        with patch("src.api.batch.batch_processing_service", mock_service):
            validation_data = {"rules": ["all"], "scope": "comprehensive"}

            response = client.post("/batch/validate/graph", json=validation_data)

            assert response.status_code == 200


class TestBatchUtilityEndpoints:
    """Test batch utility endpoints"""

    @pytest.mark.asyncio
    async def test_get_operation_types_success(self):
        """Test successful retrieval of operation types"""
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
        assert "estimated_duration" in op_type

    @pytest.mark.asyncio
    async def test_get_processing_modes_success(self):
        """Test successful retrieval of processing modes"""
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

    @pytest.mark.asyncio
    async def test_get_status_summary_success(self):
        """Test successful status summary retrieval"""
        mock_service = AsyncMock()
        mock_service.get_active_jobs.return_value = {
            "success": True,
            "active_jobs": [
                {
                    "job_id": "job_1",
                    "status": "running",
                    "operation_type": "IMPORT_NODES",
                }
            ],
            "total_active": 1,
            "queue_size": 0,
            "max_concurrent_jobs": 5,
        }
        mock_service.get_job_history.return_value = {
            "success": True,
            "job_history": [
                {
                    "job_id": "job_2",
                    "status": "completed",
                    "operation_type": "EXPORT_GRAPH",
                }
            ],
        }

        with patch("src.api.batch.batch_processing_service", mock_service):
            response = client.get("/batch/status-summary")

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "summary" in data
            assert "status_counts" in data["summary"]
            assert "operation_type_counts" in data["summary"]

    @pytest.mark.asyncio
    async def test_get_performance_stats_success(self):
        """Test successful performance stats retrieval"""
        response = client.get("/batch/performance-stats")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "performance_stats" in data
        assert "total_jobs_processed" in data["performance_stats"]
        assert "success_rate" in data["performance_stats"]
        assert "operation_type_performance" in data["performance_stats"]

    @pytest.mark.asyncio
    async def test_get_performance_stats_structure(self):
        """Test performance stats data structure"""
        response = client.get("/batch/performance-stats")

        assert response.status_code == 200
        data = response.json()
        stats = data["performance_stats"]

        # Check required fields
        assert stats["total_jobs_processed"] > 0
        assert stats["success_rate"] > 0
        assert 0 <= stats["success_rate"] <= 100

        # Check operation type performance structure
        op_performance = stats["operation_type_performance"]
        for op_type, perf_data in op_performance.items():
            assert "total_jobs" in perf_data
            assert "success_rate" in perf_data
            assert "avg_time_per_1000_items" in perf_data


class TestBatchErrorHandling:
    """Test error handling in batch API"""

    @pytest.mark.asyncio
    async def test_service_exception_handling(self):
        """Test handling of service exceptions"""
        mock_service = AsyncMock()
        mock_service.submit_batch_job.side_effect = Exception("Service error")

        with patch("src.api.batch.batch_processing_service", mock_service):
            job_data = {
                "operation_type": "IMPORT_NODES",
                "parameters": {"test": "data"},
            }

            response = client.post("/batch/jobs", json=job_data)

            assert response.status_code == 500
            assert "Job submission failed" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_get_job_status_exception(self):
        """Test exception handling in get job status"""
        mock_service = AsyncMock()
        mock_service.get_job_status.side_effect = Exception("Database error")

        with patch("src.api.batch.batch_processing_service", mock_service):
            response = client.get("/batch/jobs/job_123")

            assert response.status_code == 500
            assert "Failed to get job status" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_cancel_job_exception(self):
        """Test exception handling in job cancellation"""
        mock_service = AsyncMock()
        mock_service.cancel_job.side_effect = Exception("Cancel failed")

        with patch("src.api.batch.batch_processing_service", mock_service):
            cancel_data = {"reason": "Test"}

            response = client.post("/batch/jobs/job_123/cancel", json=cancel_data)

            assert response.status_code == 500
            assert "Job cancellation failed" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_get_operation_types_exception(self):
        """Test exception handling in get operation types"""
        with patch(
            "src.api.batch.BatchOperationType", side_effect=Exception("Enum error")
        ):
            response = client.get("/batch/operation-types")

            assert response.status_code == 500

    @pytest.mark.asyncio
    async def test_get_status_summary_service_failure(self):
        """Test status summary with service failures"""
        mock_service = AsyncMock()
        mock_service.get_active_jobs.return_value = {
            "success": False,
            "error": "Service unavailable",
        }
        mock_service.get_job_history.return_value = {
            "success": False,
            "error": "Service unavailable",
        }

        with patch("src.api.batch.batch_processing_service", mock_service):
            response = client.get("/batch/status-summary")

            assert response.status_code == 500


class TestBatchCSVParsing:
    """Test CSV parsing functionality"""

    @pytest.mark.asyncio
    async def test_parse_csv_nodes_success(self):
        """Test successful CSV nodes parsing"""
        from src.api.batch import _parse_csv_nodes

        csv_content = """name,node_type,platform,description
mod1,mod,java,Java mod
mod2,resourcepack,bedrock,Bedrock resource pack"""

        result = await _parse_csv_nodes(csv_content)

        assert len(result) == 2
        assert result[0]["name"] == "mod1"
        assert result[0]["node_type"] == "mod"
        assert result[0]["platform"] == "java"
        assert result[1]["name"] == "mod2"
        assert result[1]["node_type"] == "resourcepack"
        assert result[1]["platform"] == "bedrock"

    @pytest.mark.asyncio
    async def test_parse_csv_nodes_with_properties(self):
        """Test CSV parsing with properties column"""
        from src.api.batch import _parse_csv_nodes

        csv_content = """name,node_type,platform,properties
mod1,mod,java,"{\\"version\\": \\"1.20.1\\"}"
mod2,mod,bedrock,"{\\"version\\": \\"1.20.0\\"}" """

        result = await _parse_csv_nodes(csv_content)

        assert len(result) == 2
        assert "version" in result[0]["properties"]
        assert result[0]["properties"]["version"] == "1.20.1"

    @pytest.mark.asyncio
    async def test_parse_csv_nodes_missing_fields(self):
        """Test CSV parsing with missing optional fields"""
        from src.api.batch import _parse_csv_nodes

        csv_content = """name,node_type
mod1,mod
mod2,resourcepack"""

        result = await _parse_csv_nodes(csv_content)

        assert len(result) == 2
        assert result[0]["platform"] == "unknown"  # Default value
        assert result[0]["description"] == ""  # Default value
        assert result[1]["minecraft_version"] == "latest"  # Default value

    @pytest.mark.asyncio
    async def test_parse_csv_nodes_malformed_json(self):
        """Test CSV parsing with malformed JSON in properties"""
        from src.api.batch import _parse_csv_nodes

        csv_content = """name,node_type,properties
mod1,mod,"{invalid json}" """

        with pytest.raises(ValueError) as exc_info:
            await _parse_csv_nodes(csv_content)

        assert "Failed to parse CSV nodes" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_parse_csv_relationships_success(self):
        """Test successful CSV relationships parsing"""
        from src.api.batch import _parse_csv_relationships

        csv_content = """source_node_id,target_node_id,relationship_type,confidence_score
node1,node2,depends_on,0.9
node2,node3,relates_to,0.7"""

        result = await _parse_csv_relationships(csv_content)

        assert len(result) == 2
        assert result[0]["source_node_id"] == "node1"
        assert result[0]["target_node_id"] == "node2"
        assert result[0]["relationship_type"] == "depends_on"
        assert result[0]["confidence_score"] == 0.9
        assert result[1]["relationship_type"] == "relates_to"

    @pytest.mark.asyncio
    async def test_parse_csv_relationships_with_properties(self):
        """Test CSV parsing relationships with properties"""
        from src.api.batch import _parse_csv_relationships

        csv_content = """source_node_id,target_node_id,relationship_type,properties
node1,node2,depends_on,"{\\"weight\\": 2}"
node2,node3,relates_to,"{\\"weight\\": 1}" """

        result = await _parse_csv_relationships(csv_content)

        assert len(result) == 2
        assert "weight" in result[0]["properties"]
        assert result[0]["properties"]["weight"] == 2

    @pytest.mark.asyncio
    async def test_parse_csv_relationships_missing_fields(self):
        """Test CSV parsing relationships with missing optional fields"""
        from src.api.batch import _parse_csv_relationships

        csv_content = """source_node_id,target_node_id
node1,node2"""

        result = await _parse_csv_relationships(csv_content)

        assert len(result) == 1
        assert result[0]["relationship_type"] == "relates_to"  # Default value
        assert result[0]["confidence_score"] == 0.5  # Default value


class TestBatchHelperFunctions:
    """Test batch API helper functions"""

    def test_get_operation_description(self):
        """Test operation description helper"""
        from src.api.batch import _get_operation_description

        desc = _get_operation_description(BatchOperationType.IMPORT_NODES)
        assert "Import knowledge nodes" in desc

        desc = _get_operation_description(BatchOperationType.EXPORT_GRAPH)
        assert "Export entire knowledge graph" in desc

        # Test unknown operation type
        desc = _get_operation_description("UNKNOWN")
        assert desc == "Unknown operation"

    def test_operation_requires_file(self):
        """Test file requirement check"""
        from src.api.batch import _operation_requires_file

        # Import operations should require files
        assert _operation_requires_file(BatchOperationType.IMPORT_NODES) is True
        assert _operation_requires_file(BatchOperationType.IMPORT_RELATIONSHIPS) is True

        # Other operations should not require files
        assert _operation_requires_file(BatchOperationType.EXPORT_GRAPH) is False
        assert _operation_requires_file(BatchOperationType.DELETE_NODES) is False
        assert _operation_requires_file(BatchOperationType.VALIDATE_GRAPH) is False

    def test_get_operation_duration(self):
        """Test operation duration estimates"""
        from src.api.batch import _get_operation_duration

        duration = _get_operation_duration(BatchOperationType.IMPORT_NODES)
        assert "Medium" in duration

        duration = _get_operation_duration(BatchOperationType.DELETE_NODES)
        assert "Very Fast" in duration

        duration = _get_operation_duration(BatchOperationType.VALIDATE_GRAPH)
        assert "Slow" in duration

    def test_get_processing_mode_description(self):
        """Test processing mode descriptions"""
        from src.api.batch import _get_processing_mode_description

        desc = _get_processing_mode_description(ProcessingMode.SEQUENTIAL)
        assert "one by one" in desc

        desc = _get_processing_mode_description(ProcessingMode.PARALLEL)
        assert "simultaneously" in desc

        desc = _get_processing_mode_description("UNKNOWN")
        assert desc == "Unknown processing mode"

    def test_get_processing_mode_use_cases(self):
        """Test processing mode use cases"""
        from src.api.batch import _get_processing_mode_use_cases

        use_cases = _get_processing_mode_use_cases(ProcessingMode.SEQUENTIAL)
        assert "Simple operations" in use_cases

        use_cases = _get_processing_mode_use_cases(ProcessingMode.PARALLEL)
        assert "CPU-intensive operations" in use_cases

        use_cases = _get_processing_mode_use_cases("UNKNOWN")
        assert use_cases == ["General use"]

    def test_get_processing_mode_recommendations(self):
        """Test processing mode recommendations"""
        from src.api.batch import _get_processing_mode_recommendations

        recommendations = _get_processing_mode_recommendations(
            ProcessingMode.SEQUENTIAL
        )
        assert "small datasets" in recommendations

        recommendations = _get_processing_mode_recommendations(ProcessingMode.PARALLEL)
        assert "multi-core systems" in recommendations

        recommendations = _get_processing_mode_recommendations("UNKNOWN")
        assert recommendations == ["General purpose"]


class TestBatchIntegration:
    """Integration tests for batch API workflows"""

    @pytest.mark.asyncio
    async def test_complete_import_workflow(self):
        """Test complete import workflow from file upload to job status"""
        mock_service = AsyncMock()
        mock_service.submit_batch_job.return_value = {
            "success": True,
            "job_id": "workflow_job_123",
            "estimated_total_items": 500,
        }
        mock_service.get_job_status.return_value = {
            "success": True,
            "job_id": "workflow_job_123",
            "status": "completed",
            "progress": 100.0,
        }

        with patch("src.api.batch.batch_processing_service", mock_service):
            # Step 1: Submit import job
            test_data = {"nodes": [{"name": "test", "type": "mod"}]}
            files = {"file": ("test.json", json.dumps(test_data), "application/json")}

            import_response = client.post("/batch/import/nodes", files=files)
            assert import_response.status_code == 200

            job_id = import_response.json()["job_id"]

            # Step 2: Check job status
            status_response = client.get(f"/batch/jobs/{job_id}")
            assert status_response.status_code == 200

    @pytest.mark.asyncio
    async def test_complete_export_workflow(self):
        """Test complete export workflow"""
        mock_service = AsyncMock()
        mock_service.submit_batch_job.return_value = {
            "success": True,
            "job_id": "export_workflow_123",
            "estimated_total_items": 1000,
        }

        with patch("src.api.batch.batch_processing_service", mock_service):
            # Submit export job
            export_data = {
                "format": "json",
                "include_relationships": True,
                "processing_mode": "parallel",
            }

            response = client.post("/batch/export/graph", json=export_data)
            assert response.status_code == 200
            assert response.json()["success"] is True

    @pytest.mark.asyncio
    async def test_job_management_workflow(self):
        """Test job management operations workflow"""
        mock_service = AsyncMock()

        # Mock different service responses for different operations
        mock_service.cancel_job.return_value = {"success": True, "job_id": "job_123"}
        mock_service.pause_job.return_value = {"success": True, "job_id": "job_123"}
        mock_service.resume_job.return_value = {"success": True, "job_id": "job_123"}

        with patch("src.api.batch.batch_processing_service", mock_service):
            job_id = "job_123"

            # Test cancel
            cancel_response = client.post(
                f"/batch/jobs/{job_id}/cancel", json={"reason": "test"}
            )
            assert cancel_response.status_code == 200

            # Test pause
            pause_response = client.post(f"/batch/jobs/{job_id}/pause")
            assert pause_response.status_code == 200

            # Test resume
            resume_response = client.post(f"/batch/jobs/{job_id}/resume")
            assert resume_response.status_code == 200

    @pytest.mark.asyncio
    async def test_mixed_processing_modes(self):
        """Test different processing modes across operations"""
        mock_service = AsyncMock()
        mock_service.submit_batch_job.return_value = {
            "success": True,
            "job_id": "mode_test_123",
        }

        with patch("src.api.batch.batch_processing_service", mock_service):
            # Test sequential mode
            job_data = {
                "operation_type": "IMPORT_NODES",
                "parameters": {},
                "processing_mode": "sequential",
            }
            response = client.post("/batch/jobs", json=job_data)
            assert response.status_code == 200

            # Test parallel mode
            job_data["processing_mode"] = "parallel"
            response = client.post("/batch/jobs", json=job_data)
            assert response.status_code == 200

            # Test chunked mode
            job_data["processing_mode"] = "chunked"
            response = client.post("/batch/jobs", json=job_data)
            assert response.status_code == 200

            # Test streaming mode
            job_data["processing_mode"] = "streaming"
            response = client.post("/batch/jobs", json=job_data)
            assert response.status_code == 200


class TestBatchPerformance:
    """Test batch API performance characteristics"""

    @pytest.mark.asyncio
    async def test_large_dataset_import(self):
        """Test handling of large datasets"""
        mock_service = AsyncMock()
        mock_service.submit_batch_job.return_value = {
            "success": True,
            "job_id": "large_dataset_123",
            "estimated_total_items": 100000,
        }

        with patch("src.api.batch.batch_processing_service", mock_service):
            # Create large dataset
            large_data = {
                "nodes": [{"name": f"node_{i}", "type": "mod"} for i in range(1000)]
            }
            files = {"file": ("large.json", json.dumps(large_data), "application/json")}

            response = client.post(
                "/batch/import/nodes",
                files=files,
                data={"chunk_size": 1000, "parallel_workers": 8},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["estimated_total_items"] == 100000

    @pytest.mark.asyncio
    async def test_concurrent_job_submission(self):
        """Test concurrent job submissions"""
        mock_service = AsyncMock()
        mock_service.submit_batch_job.return_value = {
            "success": True,
            "job_id": "concurrent_job",
        }

        with patch("src.api.batch.batch_processing_service", mock_service):
            job_data = {
                "operation_type": "IMPORT_NODES",
                "parameters": {},
                "processing_mode": "parallel",
            }

            # Submit multiple jobs concurrently (simulated)
            responses = []
            for i in range(5):
                response = client.post("/batch/jobs", json=job_data)
                responses.append(response)

            # All should succeed
            for response in responses:
                assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_parameter_validation_limits(self):
        """Test parameter validation with boundary values"""
        job_data = {
            "operation_type": "IMPORT_NODES",
            "parameters": {},
            "chunk_size": 1000,  # Max allowed
            "parallel_workers": 10,  # Max allowed
        }

        response = client.post("/batch/jobs", json=job_data)
        assert response.status_code == 200

        # Test exceeded limits
        job_data["chunk_size"] = 1001  # Over limit
        response = client.post("/batch/import/nodes", json=job_data)
        assert response.status_code == 422  # FastAPI validation error
