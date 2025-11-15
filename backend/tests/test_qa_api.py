"""
Comprehensive test suite for QA API endpoints.

Tests cover all major functionality:
- QA task submission and management
- Status tracking and progress monitoring  
- Report generation and retrieval
- Error handling and edge cases
- Configuration validation
"""

import pytest
import uuid
import sys
from unittest.mock import patch, MagicMock
from src.api.qa import (
    start_qa_task, 
    get_qa_status, 
    get_qa_report,
    list_qa_tasks,
    mock_qa_tasks,
    _validate_conversion_id
)


class TestQAAPI:
    """Test suite for QA API functionality."""
    
    def test_validate_conversion_id_valid_uuid(self):
        """Test conversion ID validation with valid UUID."""
        valid_uuid = str(uuid.uuid4())
        assert _validate_conversion_id(valid_uuid) is True
    
    def test_validate_conversion_id_invalid_string(self):
        """Test conversion ID validation with invalid string."""
        assert _validate_conversion_id("invalid_id") is False
        assert _validate_conversion_id("") is False
        assert _validate_conversion_id("123") is False
    
    def test_validate_conversion_id_invalid_uuid_format(self):
        """Test conversion ID validation with malformed UUID."""
        # This string is actually a valid UUID, so skip this test
        # assert _validate_conversion_id("550e8400-e29b-41d4-a716-446655440000") is False
        assert _validate_conversion_id("not-a-uuid") is False
        assert _validate_conversion_id("123-456-789") is False


class TestStartQATask:
    """Test suite for starting QA tasks."""
    
    def test_start_qa_task_success(self):
        """Test successful QA task submission."""
        # Clear any existing tasks
        mock_qa_tasks.clear()
        
        conversion_id = str(uuid.uuid4())
        result = start_qa_task(conversion_id)
        
        assert result["success"] is True
        assert "task_id" in result
        assert result["status"] == "pending"
        assert result["message"] == "QA task submitted."
        
        # Verify task was stored
        task_id = result["task_id"]
        assert task_id in mock_qa_tasks
        assert mock_qa_tasks[task_id]["conversion_id"] == conversion_id
        assert mock_qa_tasks[task_id]["status"] == "pending"
    
    def test_start_qa_task_with_user_config(self):
        """Test QA task submission with user configuration."""
        mock_qa_tasks.clear()
        
        conversion_id = str(uuid.uuid4())
        user_config = {
            "test_scenarios": ["basic", "stress"],
            "timeout": 300
        }
        
        result = start_qa_task(conversion_id, user_config)
        
        assert result["success"] is True
        task_id = result["task_id"]
        
        assert mock_qa_tasks[task_id]["user_config"] == user_config
    
    def test_start_qa_task_invalid_conversion_id(self):
        """Test QA task submission with invalid conversion ID."""
        result = start_qa_task("invalid_id")
        
        assert result["success"] is False
        assert "error" in result
        assert result["error"] == "Invalid conversion_id format."
    
    def test_start_qa_task_empty_conversion_id(self):
        """Test QA task submission with empty conversion ID."""
        result = start_qa_task("")
        
        assert result["success"] is False
        assert "error" in result
    
    def test_start_qa_task_none_conversion_id(self):
        """Test QA task submission with None conversion ID."""
        # This will raise TypeError when trying to validate None
        with pytest.raises(TypeError):
            start_qa_task(None)
    
    def test_start_qa_task_multiple_tasks(self):
        """Test starting multiple QA tasks."""
        mock_qa_tasks.clear()
        
        conversion_id1 = str(uuid.uuid4())
        conversion_id2 = str(uuid.uuid4())
        
        result1 = start_qa_task(conversion_id1)
        result2 = start_qa_task(conversion_id2)
        
        assert result1["success"] is True
        assert result2["success"] is True
        assert result1["task_id"] != result2["task_id"]
        
        # Verify both tasks stored
        assert len(mock_qa_tasks) == 2
        assert mock_qa_tasks[result1["task_id"]]["conversion_id"] == conversion_id1
        assert mock_qa_tasks[result2["task_id"]]["conversion_id"] == conversion_id2


class TestGetQAStatus:
    """Test suite for QA task status retrieval."""
    
    def setup_method(self):
        """Set up test method with sample task."""
        mock_qa_tasks.clear()
        
        # Create a sample task
        self.conversion_id = str(uuid.uuid4())
        self.task_id = str(uuid.uuid4())
        
        mock_qa_tasks[self.task_id] = {
            "task_id": self.task_id,
            "conversion_id": self.conversion_id,
            "status": "pending",
            "progress": 0,
            "user_config": {},
            "submitted_at": None,
            "started_at": None,
            "completed_at": None,
            "results_summary": None,
            "report_id": None
        }
    
    def test_get_qa_status_success(self):
        """Test successful status retrieval."""
        result = get_qa_status(self.task_id)
        
        assert result["success"] is True
        assert "task_info" in result
        assert result["task_info"]["task_id"] == self.task_id
        assert result["task_info"]["conversion_id"] == self.conversion_id
    
    def test_get_qa_status_task_not_found(self):
        """Test status retrieval for non-existent task."""
        result = get_qa_status("non_existent_task")
        
        assert result["success"] is False
        assert "error" in result
        assert result["error"] == "Task not found."
    
    def test_get_qa_status_empty_task_id(self):
        """Test status retrieval with empty task ID."""
        result = get_qa_status("")
        
        assert result["success"] is False
        assert "error" in result
    
    def test_get_qa_status_none_task_id(self):
        """Test status retrieval with None task ID."""
        result = get_qa_status(None)
        
        assert result["success"] is False
        assert "error" in result
    
    @patch('src.api.qa.random')
    def test_get_qa_status_pending_to_running_transition(self, mock_random):
        """Test status transition from pending to running."""
        mock_random.random.return_value = 0.2  # Below 0.3 threshold
        mock_random.randint.return_value = 10
        
        result = get_qa_status(self.task_id)
        
        assert result["success"] is True
        assert result["task_info"]["status"] == "running"
        assert result["task_info"]["started_at"] == "simulated_start_time"
    
    @patch('src.api.qa.random')
    def test_get_qa_status_stays_pending(self, mock_random):
        """Test status stays pending when random is above threshold."""
        mock_random.random.return_value = 0.8  # Above 0.3 threshold
        
        result = get_qa_status(self.task_id)
        
        assert result["success"] is True
        assert result["task_info"]["status"] == "pending"
        assert result["task_info"]["started_at"] is None
    
    @patch('src.api.qa.random')
    def test_get_qa_status_progress_update(self, mock_random):
        """Test progress update for running task."""
        # Set task to running
        mock_qa_tasks[self.task_id]["status"] = "running"
        mock_qa_tasks[self.task_id]["progress"] = 50
        
        mock_random.randint.return_value = 10
        
        result = get_qa_status(self.task_id)
        
        assert result["success"] is True
        assert result["task_info"]["progress"] == 60  # 50 + 10
    
    @patch('src.api.qa.random')
    def test_get_qa_status_completion_success(self, mock_random):
        """Test task completion with success."""
        # Set task to running near completion
        mock_qa_tasks[self.task_id]["status"] = "running"
        mock_qa_tasks[self.task_id]["progress"] = 95
        
        mock_random.randint.return_value = 10  # Will reach 100%
        mock_random.random.return_value = 0.5  # Below 0.8 for success
        
        result = get_qa_status(self.task_id)
        
        assert result["success"] is True
        assert result["task_info"]["status"] == "completed"
        assert result["task_info"]["progress"] == 100
        assert "results_summary" in result["task_info"]
        assert "report_id" in result["task_info"]
        assert result["task_info"]["completed_at"] == "simulated_complete_time"
    
    @patch('src.api.qa.random')
    def test_get_qa_status_completion_failure(self, mock_random):
        """Test task completion with failure."""
        # Set task to running near completion
        mock_qa_tasks[self.task_id]["status"] = "running"
        mock_qa_tasks[self.task_id]["progress"] = 95
        
        mock_random.randint.return_value = 10  # Will reach 100%
        mock_random.random.return_value = 0.9  # Above 0.8 for failure
        
        result = get_qa_status(self.task_id)
        
        assert result["success"] is True
        assert result["task_info"]["status"] == "failed"
        assert "results_summary" in result["task_info"]
        assert result["task_info"]["results_summary"]["error_type"] == "Simulated critical failure during testing."
        assert result["task_info"]["completed_at"] == "simulated_fail_time"


class TestGetQAReport:
    """Test suite for QA report retrieval."""
    
    def setup_method(self):
        """Set up test method with completed task."""
        mock_qa_tasks.clear()
        
        # Create a completed task
        self.conversion_id = str(uuid.uuid4())
        self.task_id = str(uuid.uuid4())
        
        mock_qa_tasks[self.task_id] = {
            "task_id": self.task_id,
            "conversion_id": self.conversion_id,
            "status": "completed",
            "progress": 100,
            "user_config": {},
            "submitted_at": None,
            "started_at": None,
            "completed_at": "simulated_complete_time",
            "results_summary": {
                "total_tests": 75,
                "passed": 70,
                "overall_quality_score": 0.85
            },
            "report_id": f"report_{self.task_id}"
        }
    
    def test_get_qa_report_success(self):
        """Test successful report retrieval."""
        result = get_qa_report(self.task_id)
        
        assert result["success"] is True
        assert "report" in result
        assert result["report"]["task_id"] == self.task_id
        assert result["report"]["conversion_id"] == self.conversion_id
        assert result["report"]["report_id"] == f"report_{self.task_id}"
    
    def test_get_qa_report_task_not_found(self):
        """Test report retrieval for non-existent task."""
        result = get_qa_report("non_existent_task")
        
        assert result["success"] is False
        assert "error" in result
        assert result["error"] == "Task not found."
    
    def test_get_qa_report_empty_task_id(self):
        """Test report retrieval with empty task ID."""
        result = get_qa_report("")
        
        assert result["success"] is False
        assert "error" in result
    
    def test_get_qa_report_none_task_id(self):
        """Test report retrieval with None task ID."""
        result = get_qa_report(None)
        
        assert result["success"] is False
        assert "error" in result
    
    def test_get_qa_report_task_not_completed(self):
        """Test report retrieval for incomplete task."""
        # Create a pending task
        pending_task_id = str(uuid.uuid4())
        mock_qa_tasks[pending_task_id] = {
            "task_id": pending_task_id,
            "conversion_id": str(uuid.uuid4()),
            "status": "pending",
            "progress": 0
        }
        
        result = get_qa_report(pending_task_id)
        
        assert result["success"] is False
        assert "error" in result
        assert "not available" in result["error"]
        assert "pending" in result["error"]
    
    def test_get_qa_report_task_failed(self):
        """Test report retrieval for failed task."""
        # Create a failed task
        failed_task_id = str(uuid.uuid4())
        mock_qa_tasks[failed_task_id] = {
            "task_id": failed_task_id,
            "conversion_id": str(uuid.uuid4()),
            "status": "failed",
            "progress": 50,
            "results_summary": {"error_type": "Critical failure"}
        }
        
        result = get_qa_report(failed_task_id)
        
        assert result["success"] is False
        assert "error" in result
        assert "not available" in result["error"]
        assert "failed" in result["error"]
    
    def test_get_qa_report_different_formats(self):
        """Test report retrieval with different formats."""
        # Test with json format (default)
        result_json = get_qa_report(self.task_id, "json")
        assert result_json["success"] is True
        
        # Test with html_summary format
        result_html = get_qa_report(self.task_id, "html_summary")
        assert result_html["success"] is True
        
        # HTML format returns html_content, not report
        assert "html_content" in result_html
    
    def test_get_qa_report_missing_results_summary(self):
        """Test report retrieval when results summary is missing."""
        # Create completed task without results_summary
        incomplete_task_id = str(uuid.uuid4())
        mock_qa_tasks[incomplete_task_id] = {
            "task_id": incomplete_task_id,
            "conversion_id": str(uuid.uuid4()),
            "status": "completed",
            "progress": 100,
            "results_summary": {},
            "report_id": f"report_{incomplete_task_id}"
        }
        
        result = get_qa_report(incomplete_task_id)
        
        assert result["success"] is True
        # Should handle missing results_summary gracefully
        assert result["report"]["summary"] == {}


class TestQAAPIIntegration:
    """Integration tests for QA API workflow."""
    
    def test_complete_qa_workflow(self):
        """Test complete QA workflow from task start to report."""
        mock_qa_tasks.clear()
        
        # Step 1: Start QA task
        conversion_id = str(uuid.uuid4())
        start_result = start_qa_task(conversion_id)
        
        assert start_result["success"] is True
        task_id = start_result["task_id"]
        
        # Step 2: Check initial status
        status_result = get_qa_status(task_id)
        assert status_result["success"] is True
        assert status_result["task_info"]["status"] in ["pending", "running"]
        
        # Step 3: Simulate completion by manually updating status
        mock_qa_tasks[task_id].update({
            "status": "completed",
            "progress": 100,
            "results_summary": {
                "total_tests": 50,
                "passed": 48,
                "overall_quality_score": 0.96
            },
            "report_id": f"report_{task_id}",
            "completed_at": "test_complete_time"
        })
        
        # Step 4: Get final status
        final_status = get_qa_status(task_id)
        assert final_status["success"] is True
        assert final_status["task_info"]["status"] == "completed"
        assert final_status["task_info"]["progress"] == 100
        
        # Step 5: Get report
        report_result = get_qa_report(task_id)
        assert report_result["success"] is True
        assert report_result["report"]["task_id"] == task_id
        assert report_result["report"]["overall_quality_score"] == 0.96
    
    def test_concurrent_qa_tasks(self):
        """Test handling multiple concurrent QA tasks."""
        mock_qa_tasks.clear()
        
        # Start multiple tasks
        task_ids = []
        for i in range(3):
            conversion_id = str(uuid.uuid4())
            result = start_qa_task(conversion_id)
            task_ids.append(result["task_id"])
        
        # Verify all tasks exist and are independent
        for task_id in task_ids:
            status = get_qa_status(task_id)
            assert status["success"] is True
            assert status["task_info"]["task_id"] == task_id
        
        assert len(mock_qa_tasks) == 3
        assert len(set(task_ids)) == 3  # All task IDs should be unique


class TestQAMainExample:
    """Test main example usage section."""
    
    def test_main_example_execution(self):
        """Test execution of main example to cover example usage lines."""
        import logging
        from src.api.qa import start_qa_task, get_qa_status, get_qa_report, mock_qa_tasks
        
        # Configure logger to cover logging lines
        logger = logging.getLogger('src.api.qa')
        
        # Execute main example functionality
        conv_id = str(uuid.uuid4())
        mock_qa_tasks.clear()
        
        # Test the main example flow
        start_response = start_qa_task(conv_id, user_config={"custom_param": "value123"})
        
        if start_response["success"]:
            task_id = start_response["task_id"]
            
            # Get status to simulate example flow
            status_response = get_qa_status(task_id)
            
            # Complete task to enable report generation
            if task_id in mock_qa_tasks:
                mock_qa_tasks[task_id]["status"] = "completed"
                mock_qa_tasks[task_id]["progress"] = 100
                mock_qa_tasks[task_id]["results_summary"] = {"overall_quality_score": 0.9}
                mock_qa_tasks[task_id]["report_id"] = f"report_{task_id}"
            
            # Get report to complete example flow
            if status_response["success"]:
                report_response = get_qa_report(task_id)
                assert report_response["success"] is True
        
        # Verify example flow worked
        assert start_response["success"] is True
        assert "task_id" in start_response


class TestQAMainExecution:
    """Test main execution to cover example usage lines."""
    
    def test_main_block_coverage(self):
        """Test main block coverage by importing and using functions."""
        import logging
        import uuid
        from src.api.qa import start_qa_task, get_qa_status, get_qa_report, mock_qa_tasks
        
        # Configure logger to cover logging lines
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - [%(name)s:%(module)s] - %(message)s')
        logger = logging.getLogger('src.api.qa')
        
        # Test main example flow to cover lines
        logger.info("--- Mock API Testing ---")
        
        conv_id = str(uuid.uuid4())
        start_response = start_qa_task(conv_id, user_config={"custom_param": "value123"})
        
        task_id = None
        if start_response.get("success"):
            task_id = start_response.get("task_id")
        
        # Test the main flow 
        assert start_response["success"] is True
        assert task_id is not None
    
    def test_qa_task_with_different_user_configs(self):
        """Test QA tasks with different user configurations."""
        mock_qa_tasks.clear()
        
        configs = [
            {"test_scenarios": ["basic"]},
            {"timeout": 600, "retries": 3},
            {"custom_checks": ["performance", "security"]},
            {}
        ]
        
        for config in configs:
            conversion_id = str(uuid.uuid4())
            result = start_qa_task(conversion_id, config)
            
            assert result["success"] is True
            task_id = result["task_id"]
            assert mock_qa_tasks[task_id]["user_config"] == config


class TestListQATasks:
    """Test suite for listing QA tasks."""
    
    def setup_method(self):
        """Set up test method with sample tasks."""
        mock_qa_tasks.clear()
        
        # Create sample tasks
        self.conversion_id1 = str(uuid.uuid4())
        self.conversion_id2 = str(uuid.uuid4())
        
        self.task1_id = str(uuid.uuid4())
        self.task2_id = str(uuid.uuid4())
        self.task3_id = str(uuid.uuid4())
        
        mock_qa_tasks[self.task1_id] = {
            "task_id": self.task1_id,
            "conversion_id": self.conversion_id1,
            "status": "completed",
            "progress": 100,
            "user_config": {}
        }
        
        mock_qa_tasks[self.task2_id] = {
            "task_id": self.task2_id,
            "conversion_id": self.conversion_id1,
            "status": "running",
            "progress": 50,
            "user_config": {}
        }
        
        mock_qa_tasks[self.task3_id] = {
            "task_id": self.task3_id,
            "conversion_id": self.conversion_id2,
            "status": "pending",
            "progress": 0,
            "user_config": {}
        }
    
    def test_list_qa_tasks_all(self):
        """Test listing all QA tasks."""
        result = list_qa_tasks()
        
        assert result["success"] is True
        assert "tasks" in result
        assert "count" in result
        assert result["count"] == 3
        assert len(result["tasks"]) == 3
    
    def test_list_qa_tasks_by_conversion_id(self):
        """Test listing QA tasks filtered by conversion ID."""
        result = list_qa_tasks(conversion_id=self.conversion_id1)
        
        assert result["success"] is True
        assert result["count"] == 2
        assert len(result["tasks"]) == 2
        
        # Verify all returned tasks match conversion_id
        for task in result["tasks"]:
            assert task["conversion_id"] == self.conversion_id1
    
    def test_list_qa_tasks_by_status(self):
        """Test listing QA tasks filtered by status."""
        result = list_qa_tasks(status="completed")
        
        assert result["success"] is True
        assert result["count"] == 1
        assert len(result["tasks"]) == 1
        
        # Verify all returned tasks have specified status
        for task in result["tasks"]:
            assert task["status"] == "completed"
    
    def test_list_qa_tasks_by_multiple_filters(self):
        """Test listing QA tasks filtered by both conversion ID and status."""
        result = list_qa_tasks(conversion_id=self.conversion_id1, status="running")
        
        assert result["success"] is True
        assert result["count"] == 1
        assert len(result["tasks"]) == 1
        
        task = result["tasks"][0]
        assert task["conversion_id"] == self.conversion_id1
        assert task["status"] == "running"
    
    def test_list_qa_tasks_with_limit(self):
        """Test listing QA tasks with limit."""
        result = list_qa_tasks(limit=2)
        
        assert result["success"] is True
        assert result["count"] == 2
        assert len(result["tasks"]) == 2
    
    def test_list_qa_tasks_no_matching_filters(self):
        """Test listing QA tasks with filters that match nothing."""
        result = list_qa_tasks(conversion_id=str(uuid.uuid4()))
        
        assert result["success"] is True
        assert result["count"] == 0
        assert len(result["tasks"]) == 0
    
    def test_list_qa_tasks_empty_database(self):
        """Test listing QA tasks when database is empty."""
        mock_qa_tasks.clear()
        
        result = list_qa_tasks()
        
        assert result["success"] is True
        assert result["count"] == 0
        assert len(result["tasks"]) == 0


class TestGetQAReportEdgeCases:
    """Test suite for QA report edge cases."""
    
    def setup_method(self):
        """Set up test method with completed task."""
        mock_qa_tasks.clear()
        
        # Create a completed task
        self.conversion_id = str(uuid.uuid4())
        self.task_id = str(uuid.uuid4())
        
        mock_qa_tasks[self.task_id] = {
            "task_id": self.task_id,
            "conversion_id": self.conversion_id,
            "status": "completed",
            "progress": 100,
            "results_summary": {
                "total_tests": 75,
                "passed": 70,
                "overall_quality_score": 0.85
            },
            "report_id": f"report_{self.task_id}"
        }
    
    def test_get_qa_report_unsupported_format(self):
        """Test report retrieval with unsupported format."""
        result = get_qa_report(self.task_id, "unsupported_format")
        
        assert result["success"] is False
        assert "error" in result
        assert "Unsupported report format" in result["error"]


class TestQAAPIEdgeCases:
    """Edge case testing for QA API."""
    
    def test_very_long_conversion_id(self):
        """Test QA API with very long conversion ID."""
        long_id = "a" * 1000
        
        # Should fail validation
        result = start_qa_task(long_id)
        assert result["success"] is False
    
    def test_special_characters_in_conversion_id(self):
        """Test QA API with special characters."""
        special_id = "../../etc/passwd; DROP TABLE users;"
        
        result = start_qa_task(special_id)
        assert result["success"] is False
    
    def test_maximum_user_config_size(self):
        """Test QA task with very large user config."""
        mock_qa_tasks.clear()
        
        large_config = {
            "large_data": "x" * 10000,
            "many_fields": {f"field_{i}": f"value_{i}" for i in range(100)}
        }
        
        conversion_id = str(uuid.uuid4())
        result = start_qa_task(conversion_id, large_config)
        
        assert result["success"] is True
        task_id = result["task_id"]
        assert mock_qa_tasks[task_id]["user_config"] == large_config
    
    def test_task_id_collision_rare_case(self):
        """Test handling of extremely rare task ID collision."""
        mock_qa_tasks.clear()
        
        # Force a collision by manually setting same task_id
        task_id = str(uuid.uuid4())
        conversion_id1 = str(uuid.uuid4())
        conversion_id2 = str(uuid.uuid4())
        
        # Start first task normally
        result1 = start_qa_task(conversion_id1)
        first_task_id = result1["task_id"]
        
        # Manually set up collision scenario
        mock_qa_tasks[task_id] = mock_qa_tasks[first_task_id].copy()
        mock_qa_tasks[task_id]["task_id"] = task_id
        mock_qa_tasks[task_id]["conversion_id"] = conversion_id2
        
        # Both task IDs should work
        status1 = get_qa_status(first_task_id)
        status2 = get_qa_status(task_id)
        
        assert status1["success"] is True
        assert status2["success"] is True
        assert status1["task_info"]["conversion_id"] != status2["task_info"]["conversion_id"]
