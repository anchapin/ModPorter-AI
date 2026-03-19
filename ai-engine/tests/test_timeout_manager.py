"""
Unit tests for timeout_manager module
"""

import pytest
import asyncio
import time
from utils.timeout_manager import (
    TimeoutConfig,
    TimeoutExceeded,
    TaskTimeout,
    DeadlineTracker,
    get_timeout_config,
    create_deadline_tracker,
    run_with_timeout,
)


class TestTimeoutConfig:
    """Test TimeoutConfig class."""

    def test_default_config(self):
        """Test default configuration values."""
        config = TimeoutConfig._default()
        
        # Verify default LLM timeouts
        assert config.get_llm_timeout('openai', 'translate') == 120
        assert config.get_llm_timeout('anthropic', 'analyze') == 60
        
        # Verify default agent timeouts
        assert config.get_agent_timeout('java_analyzer') == 120
        assert config.get_agent_timeout('logic_translator') == 180
        
        # Verify default pipeline timeouts
        assert config.get_pipeline_timeout('total_job') == 1800
        assert config.get_pipeline_timeout('analysis') == 180

    def test_load_from_yaml(self, tmp_path):
        """Test loading configuration from YAML."""
        yaml_content = """
llm_timeout:
  openai:
    translate: 150
    analyze: 75
    
agent_timeout:
  java_analyzer: 200
  warning_threshold: 0.7
  
pipeline_timeout:
  analysis: 200
  conversion: 400
  total_job: 2000
"""
        config_file = tmp_path / "timeouts.yaml"
        config_file.write_text(yaml_content)
        
        config = TimeoutConfig.from_yaml(config_file)
        
        assert config.get_llm_timeout('openai', 'translate') == 150
        assert config.get_llm_timeout('openai', 'analyze') == 75
        assert config.get_agent_timeout('java_analyzer') == 200
        assert config.get_pipeline_timeout('total_job') == 2000

    def test_missing_keys_return_defaults(self):
        """Test that missing keys return default values."""
        config = TimeoutConfig._default()
        
        # Unknown provider returns default
        assert config.get_llm_timeout('unknown', 'translate') == 300
        # Unknown agent returns default
        assert config.get_agent_timeout('unknown_agent') == 300
        # Unknown pipeline stage returns default
        assert config.get_pipeline_timeout('unknown_stage') == 300


class TestDeadlineTracker:
    """Test DeadlineTracker class."""

    def test_start_and_elapsed(self):
        """Test basic start and elapsed time tracking."""
        config = TimeoutConfig._default()
        tracker = DeadlineTracker(config)
        
        tracker.start()
        time.sleep(0.01)  # Small delay
        
        elapsed = tracker.get_elapsed()
        assert elapsed > 0
        assert elapsed < 1  # Should be less than 1 second

    def test_stage_tracking(self):
        """Test stage start and completion tracking."""
        config = TimeoutConfig._default()
        tracker = DeadlineTracker(config)
        
        tracker.start()
        tracker.start_stage("analysis")
        
        assert "analysis" in tracker.stage_start_times
        
        tracker.complete_stage("analysis", 1.0)
        assert "analysis" in tracker.completed_stages

    def test_progress_with_eta(self):
        """Test progress calculation with ETA."""
        config = TimeoutConfig._default()
        tracker = DeadlineTracker(config)
        
        tracker.start()
        tracker.start_stage("analysis")
        tracker.set_progress("analysis", 0.5)
        
        progress_info = tracker.get_progress_with_eta()
        
        assert 'elapsed_seconds' in progress_info
        assert 'overall_progress' in progress_info
        assert 'stages_completed' in progress_info

    def test_is_stage_timeout(self):
        """Test stage timeout detection."""
        config = TimeoutConfig._default()
        tracker = DeadlineTracker(config)
        
        tracker.start()
        tracker.start_stage("analysis")
        
        # Should not be timeout immediately
        assert not tracker.is_stage_timeout("analysis")


class TestTimeoutExceeded:
    """Test TimeoutExceeded exception."""

    def test_exception_attributes(self):
        """Test that exception has proper attributes."""
        exc = TimeoutExceeded(
            message="Test timeout",
            operation="test_operation",
            timeout_seconds=60.0,
            elapsed_seconds=65.0,
            context={"key": "value"}
        )
        
        assert exc.operation == "test_operation"
        assert exc.timeout_seconds == 60.0
        assert exc.elapsed_seconds == 65.0
        assert exc.context["key"] == "value"
        assert exc.timestamp is not None


class TestTaskTimeout:
    """Test TaskTimeout exception."""

    def test_exception_attributes(self):
        """Test that exception has proper attributes."""
        from datetime import datetime, timedelta
        
        deadline = datetime.utcnow() + timedelta(seconds=30)
        exc = TaskTimeout(
            message="Task timeout",
            task_name="test_task",
            deadline=deadline,
            progress=0.75,
            partial_result={"data": "partial"}
        )
        
        assert exc.task_name == "test_task"
        assert exc.progress == 0.75
        assert exc.partial_result["data"] == "partial"


@pytest.mark.asyncio
async def test_run_with_timeout_success():
    """Test run_with_timeout with successful operation."""
    async def quick_task():
        await asyncio.sleep(0.01)
        return "success"
    
    result = await run_with_timeout(quick_task(), 5, "quick_task")
    assert result == "success"


@pytest.mark.asyncio
async def test_run_with_timeout_failure():
    """Test run_with_timeout with timeout."""
    async def slow_task():
        await asyncio.sleep(10)  # Will definitely timeout
        return "success"
    
    with pytest.raises(TimeoutExceeded):
        await run_with_timeout(slow_task(), 0.01, "slow_task")


def test_create_deadline_tracker():
    """Test create_deadline_tracker helper function."""
    tracker = create_deadline_tracker()
    
    assert tracker is not None
    assert isinstance(tracker, DeadlineTracker)


def test_get_timeout_config():
    """Test get_timeout_config helper function."""
    config = get_timeout_config()
    
    assert config is not None
    assert isinstance(config, TimeoutConfig)
    assert config.get_pipeline_timeout('total_job') == 1800
