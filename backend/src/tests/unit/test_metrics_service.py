"""
Unit tests for metrics service.

Tests MetricsTracker class and metric recording functions.
"""

import pytest
from unittest.mock import MagicMock, patch
from services.metrics import (
    MetricsTracker,
    record_http_request,
    record_conversion_job,
    record_agent_execution,
    record_llm_usage,
    record_asset_processed,
    record_db_operation,
    record_cache_operation,
    update_queue_size,
    update_active_conversions,
    record_error,
    record_retry_attempt,
    record_successful_retry,
    record_rate_limit_hit,
    record_rate_limit_request,
    update_rate_limit_usage,
    update_active_rate_limit_clients,
    get_metrics,
    MetricsMiddleware,
)


class TestMetricsTracker:
    @pytest.fixture
    def tracker(self):
        # Reset singleton for tests
        MetricsTracker._instance = None
        return MetricsTracker()

    def test_tracker_init(self, tracker):
        """Test MetricsTracker initializes correctly."""
        assert tracker is not None
        assert hasattr(tracker, "_initialized")
        assert hasattr(tracker, "_lock")

    def test_tracker_is_singleton(self):
        """Test MetricsTracker is a singleton."""
        MetricsTracker._instance = None
        t1 = MetricsTracker()
        t2 = MetricsTracker()
        assert t1 is t2

    def test_tracker_has_conversion_tracking(self, tracker):
        """Test tracker has conversion tracking attributes."""
        assert hasattr(tracker, "_conversion_times")
        assert hasattr(tracker, "_success_count")
        assert hasattr(tracker, "_failure_count")

    def test_record_conversion_success(self, tracker):
        """Test recording a successful conversion."""
        tracker.record_conversion(1.5, True, "1.20.0", "modpack")
        assert tracker._success_count == 1

    def test_record_conversion_failure(self, tracker):
        """Test recording a failed conversion."""
        tracker.record_conversion(2.0, False, "1.20.0", "texture")
        assert tracker._failure_count == 1

    def test_get_stats(self, tracker):
        """Test getting statistics."""
        tracker.record_conversion(1.0, True, "1.20.0", "modpack")
        stats = tracker.get_stats()
        assert stats["success_count"] == 1
        assert stats["total"] == 1
        assert stats["success_rate"] == 100.0


class TestRecordFunctions:
    def test_record_http_request_import(self):
        """Test record_http_request is callable."""
        assert callable(record_http_request)

    def test_record_conversion_job_import(self):
        """Test record_conversion_job is callable."""
        assert callable(record_conversion_job)

    def test_record_agent_execution_import(self):
        """Test record_agent_execution is callable."""
        assert callable(record_agent_execution)

    def test_record_llm_usage_import(self):
        """Test record_llm_usage is callable."""
        assert callable(record_llm_usage)

    def test_record_error_import(self):
        """Test record_error is callable."""
        assert callable(record_error)

    def test_record_retry_attempt_import(self):
        """Test record_retry_attempt is callable."""
        assert callable(record_retry_attempt)

    def test_record_successful_retry_import(self):
        """Test record_successful_retry is callable."""
        assert callable(record_successful_retry)

    def test_record_rate_limit_hit_import(self):
        """Test record_rate_limit_hit is callable."""
        assert callable(record_rate_limit_hit)

    def test_record_rate_limit_request_import(self):
        """Test record_rate_limit_request is callable."""
        assert callable(record_rate_limit_request)

    def test_update_rate_limit_usage_import(self):
        """Test update_rate_limit_usage is callable."""
        assert callable(update_rate_limit_usage)

    def test_update_active_rate_limit_clients_import(self):
        """Test update_active_rate_limit_clients is callable."""
        assert callable(update_active_rate_limit_clients)


class TestMetricsMiddleware:
    def test_middleware_init(self):
        """Test MetricsMiddleware initialization."""
        mock_app = MagicMock()
        middleware = MetricsMiddleware(app=mock_app)
        assert middleware.app is mock_app


class TestGetMetrics:
    def test_get_metrics_exists(self):
        """Test get_metrics function exists."""
        assert callable(get_metrics)
