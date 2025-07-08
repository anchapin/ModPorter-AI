import pytest
import asyncio
from unittest.mock import patch, MagicMock
import json
from datetime import datetime

from src.api.performance import router, mock_benchmark_runs, mock_benchmark_reports, mock_scenarios
from src.models.performance_models import (
    BenchmarkRunRequest,
    BenchmarkRunResponse,
    BenchmarkStatusResponse,
    BenchmarkReportResponse,
    ScenarioDefinition,
    CustomScenarioRequest
)

class TestPerformanceAPI:
    """Test cases for the performance benchmarking API endpoints."""
    
    def setup_method(self):
        """Clear mock data before each test."""
        mock_benchmark_runs.clear()
        mock_benchmark_reports.clear()
        # Reset scenarios to default state
        mock_scenarios.clear()
        mock_scenarios.update({
            "baseline_idle_001": {
                "scenario_id": "baseline_idle_001",
                "scenario_name": "Idle Performance",
                "description": "Test scenario",
                "type": "baseline",
                "duration_seconds": 300,
                "parameters": {"load_level": "none"},
                "thresholds": {"cpu": 5, "memory": 50}
            }
        })
    
    def test_run_benchmark_success(self, client):
        """Test successful benchmark run creation."""
        request_data = {
            "scenario_id": "baseline_idle_001",
            "device_type": "desktop",
            "conversion_id": "test_conversion_123"
        }
        
        response = client.post("/performance/run", json=request_data)
        
        assert response.status_code == 202
        data = response.json()
        assert data["status"] == "accepted"
        assert "run_id" in data
        assert "Check status at /status/" in data["message"]
        
        # Verify the run was created in mock storage
        run_id = data["run_id"]
        assert run_id in mock_benchmark_runs
        assert mock_benchmark_runs[run_id]["scenario_id"] == "baseline_idle_001"
        assert mock_benchmark_runs[run_id]["device_type"] == "desktop"
    
    def test_run_benchmark_invalid_scenario(self, client):
        """Test benchmark run with invalid scenario ID."""
        request_data = {
            "scenario_id": "nonexistent_scenario",
            "device_type": "desktop"
        }
        
        response = client.post("/performance/run", json=request_data)
        
        assert response.status_code == 404
        assert "not found" in response.json()["detail"]
    
    def test_get_benchmark_status_success(self, client):
        """Test successful benchmark status retrieval."""
        # Create a mock run
        run_id = "test_run_123"
        mock_benchmark_runs[run_id] = {
            "status": "running",
            "scenario_id": "baseline_idle_001",
            "progress": 50.0,
            "current_stage": "collecting_baseline"
        }
        
        response = client.get(f"/performance/status/{run_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["run_id"] == run_id
        assert data["status"] == "running"
        assert data["progress"] == 50.0
        assert data["current_stage"] == "collecting_baseline"
    
    def test_get_benchmark_status_not_found(self, client):
        """Test benchmark status for non-existent run."""
        response = client.get("/performance/status/nonexistent_run")
        
        assert response.status_code == 404
        assert "not found" in response.json()["detail"]
    
    def test_get_benchmark_report_success(self, client):
        """Test successful benchmark report retrieval."""
        # Create a mock completed run
        run_id = "test_run_123"
        mock_benchmark_runs[run_id] = {
            "status": "completed",
            "scenario_id": "baseline_idle_001"
        }
        
        # Create mock report data
        mock_benchmark_reports[run_id] = {
            "benchmark": {
                "id": run_id,
                "scenario_id": "baseline_idle_001",
                "scenario_name": "Idle Performance",
                "overall_score": 85.5,
                "cpu_score": 80.0,
                "memory_score": 90.0,
                "network_score": 85.0,
                "status": "completed",
                "device_type": "desktop",
                "created_at": "2023-01-01T10:00:00Z"
            },
            "metrics": [
                {
                    "id": "metric_1",
                    "benchmark_id": run_id,
                    "metric_name": "cpu_usage_percent",
                    "metric_category": "cpu",
                    "java_value": 60.0,
                    "bedrock_value": 50.0,
                    "unit": "percent",
                    "improvement_percentage": -16.67
                }
            ],
            "analysis": {
                "identified_issues": ["No issues"],
                "optimization_suggestions": ["All good"]
            },
            "comparison_results": {"cpu": {"improvement": -16.67}},
            "report_text": "Test report"
        }
        
        response = client.get(f"/performance/report/{run_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["run_id"] == run_id
        assert data["benchmark"]["overall_score"] == 85.5
        assert len(data["metrics"]) == 1
        assert data["report_text"] == "Test report"
    
    def test_get_benchmark_report_not_completed(self, client):
        """Test benchmark report for non-completed run."""
        run_id = "test_run_123"
        mock_benchmark_runs[run_id] = {
            "status": "running",
            "scenario_id": "baseline_idle_001"
        }
        
        response = client.get(f"/performance/report/{run_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["run_id"] == run_id
        assert data["benchmark"] is None
        assert "not available yet" in data["report_text"]
    
    def test_list_scenarios_success(self, client):
        """Test successful scenario listing."""
        response = client.get("/performance/scenarios")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["scenario_id"] == "baseline_idle_001"
        assert data[0]["scenario_name"] == "Idle Performance"
        assert data[0]["type"] == "baseline"
    
    def test_create_custom_scenario_success(self, client):
        """Test successful custom scenario creation."""
        request_data = {
            "scenario_name": "Custom Test Scenario",
            "description": "A custom test scenario",
            "type": "custom",
            "duration_seconds": 600,
            "parameters": {"custom_param": "value"},
            "thresholds": {"cpu": 70, "memory": 80}
        }
        
        response = client.post("/performance/scenarios", json=request_data)
        
        assert response.status_code == 201
        data = response.json()
        assert data["scenario_name"] == "Custom Test Scenario"
        assert data["type"] == "custom"
        assert data["duration_seconds"] == 600
        assert "custom_" in data["scenario_id"]
        
        # Verify it was added to mock_scenarios
        assert data["scenario_id"] in mock_scenarios
    
    def test_get_benchmark_history_success(self, client):
        """Test successful benchmark history retrieval."""
        # Create mock completed runs
        run_id1 = "test_run_1"
        run_id2 = "test_run_2"
        
        mock_benchmark_runs[run_id1] = {
            "status": "completed",
            "scenario_id": "baseline_idle_001",
            "device_type": "desktop",
            "created_at": "2023-01-01T10:00:00"
        }
        
        mock_benchmark_runs[run_id2] = {
            "status": "completed",
            "scenario_id": "baseline_idle_001",
            "device_type": "mobile",
            "created_at": "2023-01-01T11:00:00"
        }
        
        mock_benchmark_reports[run_id1] = {
            "benchmark": {"overall_score": 85.0, "cpu_score": 80.0, "memory_score": 90.0, "network_score": 85.0}
        }
        
        mock_benchmark_reports[run_id2] = {
            "benchmark": {"overall_score": 78.0, "cpu_score": 75.0, "memory_score": 82.0, "network_score": 78.0}
        }
        
        response = client.get("/performance/history")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        
        # Should be sorted by creation time (newest first)
        assert data[0]["run_id"] == run_id2
        assert data[1]["run_id"] == run_id1
        
        # Check data structure
        assert data[0]["overall_score"] == 78.0
        assert data[0]["device_type"] == "mobile"
    
    def test_get_benchmark_history_with_pagination(self, client):
        """Test benchmark history with pagination."""
        # Create multiple mock runs
        for i in range(5):
            run_id = f"test_run_{i}"
            mock_benchmark_runs[run_id] = {
                "status": "completed",
                "scenario_id": "baseline_idle_001",
                "created_at": f"2023-01-0{i+1}T10:00:00"
            }
            mock_benchmark_reports[run_id] = {
                "benchmark": {"overall_score": 80.0 + i, "cpu_score": 80.0, "memory_score": 90.0, "network_score": 85.0}
            }
        
        # Test with limit and offset
        response = client.get("/performance/history?limit=2&offset=1")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        
        # Should skip the first item and return the next 2
        assert data[0]["run_id"] == "test_run_3"
        assert data[1]["run_id"] == "test_run_2"
    
    def test_get_benchmark_history_empty(self, client):
        """Test benchmark history when no completed runs exist."""
        # Add a non-completed run
        mock_benchmark_runs["test_run_1"] = {
            "status": "running",
            "scenario_id": "baseline_idle_001"
        }
        
        response = client.get("/performance/history")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 0  # No completed runs
    
    @patch('src.api.performance.simulate_benchmark_execution')
    def test_run_benchmark_background_task(self, mock_simulate, client):
        """Test that benchmark run properly triggers background task."""
        request_data = {
            "scenario_id": "baseline_idle_001",
            "device_type": "desktop"
        }
        
        response = client.post("/performance/run", json=request_data)
        
        assert response.status_code == 202
        # Note: In actual tests, background tasks don't execute immediately
        # This test verifies the endpoint accepts the request correctly
        
    def test_run_benchmark_missing_fields(self, client):
        """Test benchmark run with missing required fields."""
        request_data = {}  # Missing scenario_id
        
        response = client.post("/performance/run", json=request_data)
        
        assert response.status_code == 422  # Validation error
        assert "Field required" in response.json()["detail"][0]["msg"]
    
    def test_create_custom_scenario_validation(self, client):
        """Test custom scenario creation with validation errors."""
        request_data = {
            "scenario_name": "",  # Empty name should fail validation
            "description": "",    # Empty description should also fail validation
            "type": "custom"
        }
        
        response = client.post("/performance/scenarios", json=request_data)
        
        assert response.status_code == 422  # Validation error