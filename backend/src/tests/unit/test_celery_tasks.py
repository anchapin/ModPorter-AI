"""
Unit tests for Celery tasks service.

Issue: #1098 - Consolidate task queues: remove task_queue.py duplicate, migrate to Celery
"""

import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone

from services.celery_tasks import (
    TaskData,
    TaskStatus,
    TaskPriority,
    RetryPolicy,
    DEFAULT_RETRY_POLICY,
    CONVERSION_RETRY_POLICY,
    QUEUE_NAMES,
    DEAD_LETTER_QUEUE,
    handle_conversion_task,
    handle_asset_conversion_task,
    handle_java_analysis_task,
    handle_texture_extraction_task,
    handle_model_conversion_task,
)


class TestTaskData:
    """Tests for TaskData dataclass."""

    def test_task_data_creation(self):
        """Test TaskData creation with defaults."""
        task = TaskData(
            id="test-123",
            name="test_task",
            payload={"key": "value"},
        )

        assert task.id == "test-123"
        assert task.name == "test_task"
        assert task.payload == {"key": "value"}
        assert task.status == TaskStatus.QUEUED
        assert task.priority == TaskPriority.NORMAL
        assert task.retry_count == 0
        assert task.max_retries == 3

    def test_task_data_to_dict(self):
        """Test TaskData serialization to dict."""
        task = TaskData(
            id="test-456",
            name="conversion",
            payload={"job_id": "123"},
            priority=TaskPriority.HIGH,
        )

        task_dict = task.to_dict()

        assert task_dict["id"] == "test-456"
        assert task_dict["name"] == "conversion"
        assert task_dict["priority"] == 2
        assert task_dict["status"] == "queued"

    def test_task_data_from_dict(self):
        """Test TaskData deserialization from dict."""
        data = {
            "id": "task-789",
            "name": "asset_conversion",
            "payload": {"asset_id": "abc"},
            "status": "completed",
            "priority": 1,
            "created_at": "2024-01-01T00:00:00+00:00",
            "started_at": None,
            "completed_at": None,
            "result": {"status": "done"},
            "error": None,
            "retry_count": 0,
            "max_retries": 3,
            "next_retry_at": None,
            "timeout_seconds": 300,
        }

        task = TaskData.from_dict(data)

        assert task.id == "task-789"
        assert task.name == "asset_conversion"
        assert task.status == TaskStatus.COMPLETED
        assert task.result == {"status": "done"}


class TestRetryPolicy:
    """Tests for RetryPolicy."""

    def test_default_policy_values(self):
        """Test default retry policy values."""
        policy = RetryPolicy()

        assert policy.max_retries == 3
        assert policy.initial_delay_seconds == 1.0
        assert policy.max_delay_seconds == 300.0
        assert policy.backoff_multiplier == 2.0

    def test_calculate_delay_exponential_backoff(self):
        """Test exponential backoff delay calculation."""
        policy = RetryPolicy(
            initial_delay_seconds=1.0, max_delay_seconds=100.0, backoff_multiplier=2.0
        )

        assert policy.calculate_delay(0) == 1.0
        assert policy.calculate_delay(1) == 2.0
        assert policy.calculate_delay(2) == 4.0
        assert policy.calculate_delay(3) == 8.0

    def test_calculate_delay_respects_max(self):
        """Test that delay respects maximum."""
        policy = RetryPolicy(
            initial_delay_seconds=1.0, max_delay_seconds=10.0, backoff_multiplier=2.0
        )

        assert policy.calculate_delay(10) == 10.0
        assert policy.calculate_delay(100) == 10.0

    def test_predefined_policies(self):
        """Test predefined retry policies."""
        assert DEFAULT_RETRY_POLICY.max_retries == 3
        assert DEFAULT_RETRY_POLICY.initial_delay_seconds == 1.0

        assert CONVERSION_RETRY_POLICY.max_retries == 5
        assert CONVERSION_RETRY_POLICY.initial_delay_seconds == 2.0
        assert CONVERSION_RETRY_POLICY.max_delay_seconds == 600.0


class TestQueueNames:
    """Tests for queue name constants."""

    def test_queue_names_exist(self):
        """Test that all priority queue names exist."""
        assert TaskPriority.LOW in QUEUE_NAMES
        assert TaskPriority.NORMAL in QUEUE_NAMES
        assert TaskPriority.HIGH in QUEUE_NAMES
        assert TaskPriority.CRITICAL in QUEUE_NAMES

    def test_queue_name_values(self):
        """Test queue name values."""
        assert QUEUE_NAMES[TaskPriority.LOW] == "celery:low"
        assert QUEUE_NAMES[TaskPriority.NORMAL] == "celery:normal"
        assert QUEUE_NAMES[TaskPriority.HIGH] == "celery:high"
        assert QUEUE_NAMES[TaskPriority.CRITICAL] == "celery:critical"

    def test_dead_letter_queue_name(self):
        """Test dead letter queue name."""
        assert DEAD_LETTER_QUEUE == "celery:dead_letter"


class TestTaskHandlers:
    """Tests for task handler functions."""

    def test_handle_conversion_task(self):
        """Test conversion task handler."""
        result = handle_conversion_task({"job_id": "job-123", "file_id": "file-456"})

        assert result["job_id"] == "job-123"
        assert result["status"] == "completed"
        assert "result_url" in result

    def test_handle_asset_conversion_task(self):
        """Test asset conversion task handler."""
        result = handle_asset_conversion_task({"asset_id": "asset-789"})

        assert result["asset_id"] == "asset-789"
        assert result["status"] == "converted"

    def test_handle_java_analysis_task(self):
        """Test Java analysis task handler."""
        result = handle_java_analysis_task({"mod_id": "mod-abc"})

        assert result["mod_id"] == "mod-abc"
        assert result["status"] == "analyzed"

    def test_handle_texture_extraction_task(self):
        """Test texture extraction task handler."""
        result = handle_texture_extraction_task({"jar_path": "/path/to/mod.jar"})

        assert result["jar_path"] == "/path/to/mod.jar"
        assert result["status"] == "extracted"

    def test_handle_model_conversion_task(self):
        """Test model conversion task handler."""
        result = handle_model_conversion_task({"model_id": "model-xyz"})

        assert result["model_id"] == "model-xyz"
        assert result["status"] == "converted"


class TestTaskStatus:
    """Tests for TaskStatus enum."""

    def test_all_statuses_exist(self):
        """Test all task statuses are defined."""
        assert TaskStatus.QUEUED.value == "queued"
        assert TaskStatus.PROCESSING.value == "processing"
        assert TaskStatus.COMPLETED.value == "completed"
        assert TaskStatus.FAILED.value == "failed"
        assert TaskStatus.CANCELLED.value == "cancelled"
        assert TaskStatus.DEAD_LETTER.value == "dead_letter"
        assert TaskStatus.RETRYING.value == "retrying"


class TestTaskPriority:
    """Tests for TaskPriority enum."""

    def test_priority_order(self):
        """Test priority values are ordered correctly."""
        assert TaskPriority.LOW.value == 0
        assert TaskPriority.NORMAL.value == 1
        assert TaskPriority.HIGH.value == 2
        assert TaskPriority.CRITICAL.value == 3

    def test_priority_comparison(self):
        """Test priority comparison."""
        assert TaskPriority.LOW < TaskPriority.NORMAL
        assert TaskPriority.NORMAL < TaskPriority.HIGH
        assert TaskPriority.HIGH < TaskPriority.CRITICAL


class TestCeleryConfigImport:
    """Tests for Celery configuration import."""

    def test_celery_config_import(self):
        """Test that celery_config can be imported."""
        from services.celery_config import celery_app, REDIS_URL

        assert celery_app is not None
        assert REDIS_URL is not None
        assert "redis" in REDIS_URL

    def test_celery_app_name(self):
        """Test Celery app is configured with correct name."""
        from services.celery_config import celery_app

        assert celery_app.main == "portkit"

    def test_celery_conf_settings(self):
        """Test Celery configuration settings."""
        from services.celery_config import celery_app

        assert celery_app.conf.task_serializer == "json"
        assert celery_app.conf.result_serializer == "json"
        assert celery_app.conf.timezone == "UTC"
        assert celery_app.conf.enable_utc is True
        assert celery_app.conf.task_track_started is True
