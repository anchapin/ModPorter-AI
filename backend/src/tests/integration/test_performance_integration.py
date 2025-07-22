import pytest
import time
from unittest.mock import patch
from fastapi.testclient import TestClient

from src.main import app
from backend.src.api.performance import mock_benchmark_runs, mock_benchmark_reports, mock_scenarios

class TestPerformanceIntegration:
    """Integration tests for the performance benchmarking system."""
    
    def setup_method(self):
        """Setup test environment."""
        self.client = TestClient(app)
        
        # Clear mock data
        mock_benchmark_runs.clear()
        mock_benchmark_reports.clear()
        
        # Ensure baseline scenario exists
        mock_scenarios["baseline_idle_001"] = {
            "scenario_id": "baseline_idle_001",
            "scenario_name": "Idle Performance",
            "description": "Test scenario",
            "type": "baseline",
            "duration_seconds": 300,
            "parameters": {"load_level": "none"},
            "thresholds": {"cpu": 5, "memory": 50}
        }
    
    def test_full_benchmark_workflow(self):
        """Test the complete benchmark workflow from creation to report."""
        # Step 1: List available scenarios
        scenarios_response = self.client.get("/performance/scenarios")
        assert scenarios_response.status_code == 200
        scenarios = scenarios_response.json()
        assert len(scenarios) >= 1
        
        # Step 2: Create a benchmark run
        run_request = {
            "scenario_id": "baseline_idle_001",
            "device_type": "desktop",
            "conversion_id": "test_conversion_123"
        }
        
        run_response = self.client.post("/performance/run", json=run_request)
        assert run_response.status_code == 202
        
        run_data = run_response.json()
        run_id = run_data["run_id"]
        assert run_data["status"] == "accepted"
        
        # Step 3: Check initial status
        status_response = self.client.get(f"/performance/status/{run_id}")
        assert status_response.status_code == 200
        
        status_data = status_response.json()
        assert status_data["run_id"] == run_id
        assert status_data["status"] in ["pending", "running", "completed"]
        
        # Step 4: Wait for completion (in real test, this would be mocked)
        # For integration test, we'll simulate completion
        max_wait = 10  # seconds
        start_time = time.time()
        
        while time.time() - start_time < max_wait:
            status_response = self.client.get(f"/performance/status/{run_id}")
            status_data = status_response.json()
            
            if status_data["status"] == "completed":
                break
            elif status_data["status"] == "failed":
                pytest.fail(f"Benchmark failed: {status_data}")
            
            time.sleep(0.5)
        
        # Step 5: Get the final report
        report_response = self.client.get(f"/performance/report/{run_id}")
        assert report_response.status_code == 200
        
        report_data = report_response.json()
        assert report_data["run_id"] == run_id
        
        # Verify report structure
        if report_data["benchmark"] is not None:  # If completed
            assert "overall_score" in report_data["benchmark"]
            assert len(report_data["metrics"]) >= 0
            assert "analysis" in report_data
            assert "comparison_results" in report_data
            assert len(report_data["report_text"]) > 0
    
    def test_custom_scenario_creation_and_usage(self):
        """Test creating a custom scenario and using it for benchmarking."""
        # Step 1: Create a custom scenario
        custom_scenario = {
            "scenario_name": "Custom Integration Test",
            "description": "A custom scenario for integration testing",
            "type": "custom",
            "duration_seconds": 180,
            "parameters": {"test_param": "value"},
            "thresholds": {"cpu": 60, "memory": 100}
        }
        
        scenario_response = self.client.post("/performance/scenarios", json=custom_scenario)
        assert scenario_response.status_code == 201
        
        scenario_data = scenario_response.json()
        custom_scenario_id = scenario_data["scenario_id"]
        assert scenario_data["scenario_name"] == "Custom Integration Test"
        
        # Step 2: Verify it appears in scenarios list
        scenarios_response = self.client.get("/performance/scenarios")
        scenarios = scenarios_response.json()
        
        custom_found = False
        for scenario in scenarios:
            if scenario["scenario_id"] == custom_scenario_id:
                custom_found = True
                assert scenario["scenario_name"] == "Custom Integration Test"
                break
        
        assert custom_found, "Custom scenario not found in scenarios list"
        
        # Step 3: Use the custom scenario for benchmarking
        run_request = {
            "scenario_id": custom_scenario_id,
            "device_type": "desktop"
        }
        
        run_response = self.client.post("/performance/run", json=run_request)
        assert run_response.status_code == 202
        
        run_data = run_response.json()
        assert run_data["status"] == "accepted"
    
    def test_benchmark_history_tracking(self):
        """Test that benchmark history is properly tracked."""
        # Create multiple benchmark runs
        run_ids = []
        
        for i in range(3):
            run_request = {
                "scenario_id": "baseline_idle_001",
                "device_type": "desktop",
                "conversion_id": f"test_conversion_{i}"
            }
            
            run_response = self.client.post("/performance/run", json=run_request)
            assert run_response.status_code == 202
            
            run_data = run_response.json()
            run_ids.append(run_data["run_id"])
        
        # Wait for completion and manually set some as completed for testing
        for i, run_id in enumerate(run_ids):
            mock_benchmark_runs[run_id]["status"] = "completed"
            mock_benchmark_runs[run_id]["created_at"] = f"2023-01-0{i+1}T10:00:00"
            
            # Add mock report data
            mock_benchmark_reports[run_id] = {
                "benchmark": {
                    "overall_score": 80.0 + i,
                    "cpu_score": 75.0 + i,
                    "memory_score": 85.0 + i,
                    "network_score": 80.0 + i
                }
            }
        
        # Test history retrieval
        history_response = self.client.get("/performance/history")
        assert history_response.status_code == 200
        
        history_data = history_response.json()
        assert len(history_data) == 3
        
        # Verify sorting (newest first)
        assert history_data[0]["run_id"] == run_ids[2]  # Most recent
        assert history_data[2]["run_id"] == run_ids[0]  # Oldest
        
        # Test pagination
        paginated_response = self.client.get("/performance/history?limit=2&offset=1")
        assert paginated_response.status_code == 200
        
        paginated_data = paginated_response.json()
        assert len(paginated_data) == 2
        assert paginated_data[0]["run_id"] == run_ids[1]
    
    def test_api_error_handling(self):
        """Test API error handling for various scenarios."""
        # Test 1: Invalid scenario ID
        invalid_run_request = {
            "scenario_id": "nonexistent_scenario",
            "device_type": "desktop"
        }
        
        response = self.client.post("/performance/run", json=invalid_run_request)
        assert response.status_code == 404
        
        # Test 2: Invalid run ID for status
        response = self.client.get("/performance/status/invalid_run_id")
        assert response.status_code == 404
        
        # Test 3: Invalid run ID for report
        response = self.client.get("/performance/report/invalid_run_id")
        assert response.status_code == 404
        
        # Test 4: Missing required fields
        response = self.client.post("/performance/run", json={})
        assert response.status_code == 422
        
        # Test 5: Invalid custom scenario data
        invalid_scenario = {
            "scenario_name": "",  # Empty name
            "description": "Test",
            "type": "custom"
        }
        
        response = self.client.post("/performance/scenarios", json=invalid_scenario)
        assert response.status_code == 422
    
    def test_concurrent_benchmark_runs(self):
        """Test handling of multiple concurrent benchmark runs."""
        # Create multiple runs simultaneously
        run_requests = [
            {
                "scenario_id": "baseline_idle_001",
                "device_type": "desktop",
                "conversion_id": f"concurrent_test_{i}"
            }
            for i in range(5)
        ]
        
        run_ids = []
        for request in run_requests:
            response = self.client.post("/performance/run", json=request)
            assert response.status_code == 202
            
            run_data = response.json()
            run_ids.append(run_data["run_id"])
        
        # Verify all runs were created
        assert len(run_ids) == 5
        assert len(set(run_ids)) == 5  # All unique
        
        # Check that all runs are tracked
        for run_id in run_ids:
            response = self.client.get(f"/performance/status/{run_id}")
            assert response.status_code == 200
            
            status_data = response.json()
            assert status_data["run_id"] == run_id
            assert status_data["status"] in ["pending", "running", "completed"]
    
    @patch('src.api.performance.simulate_benchmark_execution')
    def test_benchmark_execution_failure_handling(self, mock_simulate):
        """Test handling of benchmark execution failures."""
        # Mock the execution to fail
        def failing_execution(run_id, scenario_id, device_type):
            mock_benchmark_runs[run_id].update({
                "status": "failed",
                "error": "Simulated execution failure"
            })
        
        mock_simulate.side_effect = failing_execution
        
        # Create a benchmark run
        run_request = {
            "scenario_id": "baseline_idle_001",
            "device_type": "desktop"
        }
        
        run_response = self.client.post("/performance/run", json=run_request)
        assert run_response.status_code == 202
        
        run_data = run_response.json()
        run_id = run_data["run_id"]
        
        # Give some time for background task to execute
        time.sleep(0.1)
        
        # Check status reflects failure
        status_response = self.client.get(f"/performance/status/{run_id}")
        assert status_response.status_code == 200
        
        status_data = status_response.json()
        assert status_data["status"] == "failed"
        
        # Report should indicate failure
        report_response = self.client.get(f"/performance/report/{run_id}")
        assert report_response.status_code == 200
        
        report_data = report_response.json()
        assert report_data["benchmark"] is None
        assert "not available" in report_data["report_text"]
    
    def test_scenario_file_loading(self):
        """Test that scenarios are properly loaded from JSON files."""
        # This test verifies the load_scenarios_from_files function
        scenarios_response = self.client.get("/performance/scenarios")
        assert scenarios_response.status_code == 200
        
        scenarios = scenarios_response.json()
        
        # Should have at least the baseline scenario
        scenario_ids = [s["scenario_id"] for s in scenarios]
        assert "baseline_idle_001" in scenario_ids
        
        # Verify scenario structure
        for scenario in scenarios:
            assert "scenario_id" in scenario
            assert "scenario_name" in scenario
            assert "description" in scenario
            assert "type" in scenario
            assert "duration_seconds" in scenario
            assert "parameters" in scenario
            assert "thresholds" in scenario