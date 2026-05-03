"""
Tests for Automation Metrics Service and API

Unit tests for the automation metrics service (GAP-2.5-06).
Tests cover:
- Recording conversion events
- Calculating automation metrics
- Dashboard data generation
- Historical data tracking
- API endpoints
"""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock
import uuid

from services.automation_metrics import (
    AutomationMetricsService,
    ConversionEvent,
    AutomationMetricsSnapshot,
    get_automation_metrics_service,
    record_conversion_event,
    get_current_metrics,
    get_dashboard_data,
    TARGET_AUTOMATION_RATE,
    TARGET_ONE_CLICK_RATE,
    TARGET_AUTO_RECOVERY_RATE,
)


class TestConversionEvent:
    """Tests for ConversionEvent dataclass."""

    def test_conversion_event_creation(self):
        """Test creating a conversion event."""
        event = ConversionEvent(
            conversion_id="test-123",
            was_automated=True,
            was_one_click=True,
        )

        assert event.conversion_id == "test-123"
        assert event.was_automated is True
        assert event.was_one_click is True
        assert event.had_error is False
        assert event.auto_recovered is False
        assert event.timestamp is not None

    def test_conversion_event_with_timestamps(self):
        """Test conversion duration calculation from timestamps."""
        upload = datetime(2026, 3, 31, 12, 0, 0, tzinfo=timezone.utc)
        download = datetime(2026, 3, 31, 12, 5, 0, tzinfo=timezone.utc)

        event = ConversionEvent(
            conversion_id="test-456",
            upload_time=upload,
            download_time=download,
        )

        assert (
            299.9 < event.conversion_duration_seconds < 300.1
        )  # ~5 minutes (allowing for timing precision)

    def test_conversion_event_duration_override(self):
        """Test conversion_time_seconds override."""
        event = ConversionEvent(
            conversion_id="test-789",
            conversion_time_seconds=120.5,
        )

        assert event.conversion_duration_seconds == 120.5


class TestAutomationMetricsService:
    """Tests for AutomationMetricsService."""

    @pytest.fixture
    def service(self):
        """Create a fresh service instance for testing."""
        # Reset singleton for testing
        AutomationMetricsService._instance = None
        AutomationMetricsService._lock = threading.Lock()
        svc = AutomationMetricsService()
        yield svc
        # Cleanup
        svc.reset_metrics()

    def test_singleton_pattern(self):
        """Test that service follows singleton pattern."""
        svc1 = AutomationMetricsService()
        svc2 = AutomationMetricsService()

        assert svc1 is svc2

    def test_record_conversion_event(self, service):
        """Test recording a basic conversion event."""
        event = service.record_conversion_event(
            conversion_id="conv-001",
            was_automated=True,
            was_one_click=True,
        )

        assert event.conversion_id == "conv-001"
        assert event.was_automated is True
        assert event.was_one_click is True

    def test_record_event_with_all_fields(self, service):
        """Test recording an event with all fields populated."""
        upload = datetime.now(timezone.utc) - timedelta(minutes=5)
        download = datetime.now(timezone.utc)

        event = service.record_conversion_event(
            conversion_id="conv-002",
            was_automated=True,
            was_one_click=True,
            upload_time=upload,
            download_time=download,
            mode_classification_correct=True,
            had_error=True,
            auto_recovered=True,
            user_satisfaction_score=4.5,
        )

        assert event.was_automated is True
        assert event.was_one_click is True
        assert event.mode_classification_correct is True
        assert event.had_error is True
        assert event.auto_recovered is True
        assert event.user_satisfaction_score == 4.5
        assert 299.9 < event.conversion_duration_seconds < 300.1  # ~5 minutes

    def test_get_current_metrics_empty(self, service):
        """Test metrics calculation with no events."""
        service.reset_metrics()
        metrics = service.get_current_metrics(period_hours=24)

        assert metrics.total_conversions == 0
        assert metrics.automation_rate == 0.0
        assert metrics.one_click_rate == 0.0
        assert metrics.auto_recovery_rate == 0.0

    def test_get_current_metrics_automation_rate(self, service):
        """Test automation rate calculation."""
        # Record 10 events, 8 automated
        for i in range(10):
            service.record_conversion_event(
                conversion_id=f"conv-{i}",
                was_automated=(i < 8),  # First 8 are automated
                was_one_click=True,
            )

        metrics = service.get_current_metrics(period_hours=24)

        assert metrics.total_conversions == 10
        assert metrics.automated_conversions == 8
        assert metrics.automation_rate == 80.0

    def test_get_current_metrics_one_click_rate(self, service):
        """Test one-click rate calculation."""
        # Record 10 events, 6 one-click
        for i in range(10):
            service.record_conversion_event(
                conversion_id=f"conv-{i}",
                was_automated=True,
                was_one_click=(i < 6),  # First 6 are one-click
            )

        metrics = service.get_current_metrics(period_hours=24)

        assert metrics.total_conversions == 10
        assert metrics.one_click_conversions == 6
        assert metrics.one_click_rate == 60.0

    def test_get_current_metrics_auto_recovery_rate(self, service):
        """Test auto-recovery rate calculation."""
        # Record 5 errors, 4 auto-recovered
        for i in range(5):
            service.record_conversion_event(
                conversion_id=f"conv-{i}",
                was_automated=True,
                was_one_click=True,
                had_error=True,
                auto_recovered=(i < 4),  # First 4 recovered
            )

        metrics = service.get_current_metrics(period_hours=24)

        assert metrics.errors_total == 5
        assert metrics.auto_recovered_count == 4
        assert metrics.auto_recovery_rate == 80.0

    def test_get_current_metrics_conversion_time(self, service):
        """Test average conversion time calculation."""
        base_time = datetime.now(timezone.utc)

        # Record 3 events with different conversion times
        for i, seconds in enumerate([100.0, 200.0, 300.0]):
            upload = base_time - timedelta(seconds=seconds)
            download = base_time - timedelta(seconds=seconds - 100)
            service.record_conversion_event(
                conversion_id=f"conv-{i}",
                was_automated=True,
                was_one_click=True,
                upload_time=upload,
                download_time=download,
            )

        metrics = service.get_current_metrics(period_hours=24)

        # Each conversion took 100 seconds
        assert metrics.avg_conversion_time_seconds == 100.0

    def test_get_current_metrics_mode_classification_accuracy(self, service):
        """Test mode classification accuracy calculation."""
        # Record 10 events, 7 correct
        for i in range(10):
            service.record_conversion_event(
                conversion_id=f"conv-{i}",
                was_automated=True,
                was_one_click=True,
                mode_classification_correct=(i < 7),  # First 7 correct
            )

        metrics = service.get_current_metrics(period_hours=24)

        assert metrics.mode_classifications_total == 10
        assert metrics.mode_classifications_correct == 7
        assert metrics.mode_classification_accuracy == 70.0

    def test_get_current_metrics_user_satisfaction(self, service):
        """Test average user satisfaction calculation."""
        # Record 4 events with satisfaction scores
        scores = [4.0, 4.5, 5.0, 3.5]
        for i, score in enumerate(scores):
            service.record_conversion_event(
                conversion_id=f"conv-{i}",
                was_automated=True,
                was_one_click=True,
                user_satisfaction_score=score,
            )

        metrics = service.get_current_metrics(period_hours=24)

        assert metrics.satisfaction_scores_total == 4
        assert metrics.avg_user_satisfaction == 4.25  # (4.0 + 4.5 + 5.0 + 3.5) / 4

    def test_get_current_metrics_target_status(self, service):
        """Test target met status indicators."""
        # Record events to meet targets
        # Target: 95% automation, 80% one-click, 80% auto-recovery
        for i in range(100):
            service.record_conversion_event(
                conversion_id=f"conv-{i}",
                was_automated=(i < 96),  # 96% - meets 95% target
                was_one_click=(i < 85),  # 85% - meets 80% target
                had_error=(i >= 90),  # 10 errors
                auto_recovered=(i >= 90) and (i < 98),  # 8 of 10 recovered - 80%
            )

        metrics = service.get_current_metrics(period_hours=24)

        assert metrics.automation_rate >= TARGET_AUTOMATION_RATE
        assert metrics.one_click_rate >= TARGET_ONE_CLICK_RATE
        # 8/10 = 80% auto-recovery - exactly at target
        assert metrics.auto_recovery_rate >= TARGET_AUTO_RECOVERY_RATE

    def test_get_current_metrics_period_filter(self, service):
        """Test that period filter correctly excludes old events."""
        # Record an old event directly in storage
        old_time = datetime.now(timezone.utc) - timedelta(hours=48)
        service._events.append(
            ConversionEvent(
                conversion_id="old-conv",
                timestamp=old_time,
                was_automated=True,
                was_one_click=True,
            )
        )

        # Record a recent event
        service.record_conversion_event(
            conversion_id="recent-conv",
            was_automated=True,
            was_one_click=True,
        )

        # Should only see recent event in 24h metrics
        metrics = service.get_current_metrics(period_hours=24)
        assert metrics.total_conversions == 1
        assert "recent-conv" in [e.conversion_id for e in service._events[-1:]]

    def test_get_dashboard_data_structure(self, service):
        """Test dashboard data structure and content."""
        # Record some events
        for i in range(5):
            service.record_conversion_event(
                conversion_id=f"conv-{i}",
                was_automated=True,
                was_one_click=True,
                user_satisfaction_score=4.0,
            )

        dashboard = service.get_dashboard_data(period_hours=24)

        assert "metrics" in dashboard
        assert "summary" in dashboard
        assert "status" in dashboard
        assert "period" in dashboard

        # Check metrics structure
        assert "automation_rate" in dashboard["metrics"]
        assert "one_click_rate" in dashboard["metrics"]
        assert "auto_recovery_rate" in dashboard["metrics"]
        assert "avg_conversion_time_seconds" in dashboard["metrics"]
        assert "mode_classification_accuracy" in dashboard["metrics"]
        assert "user_satisfaction" in dashboard["metrics"]

        # Check status values
        assert dashboard["status"]["overall"] in [
            "excellent",
            "good",
            "needs_improvement",
            "critical",
        ]
        assert dashboard["status"]["total_targets"] == 3

    def test_get_dashboard_data_overall_status(self, service):
        """Test overall status calculation in dashboard."""
        # Record events to meet all targets
        for i in range(100):
            service.record_conversion_event(
                conversion_id=f"conv-{i}",
                was_automated=(i < 96),  # 96% - meets 95%
                was_one_click=(i < 85),  # 85% - meets 80%
                had_error=(i >= 90),
                auto_recovered=(i >= 90),
            )

        dashboard = service.get_dashboard_data(period_hours=24)

        # All targets met should be "excellent"
        assert dashboard["status"]["overall"] == "excellent"

    def test_reset_metrics(self, service):
        """Test resetting metrics clears all data."""
        # Record some events
        for i in range(5):
            service.record_conversion_event(
                conversion_id=f"conv-{i}",
                was_automated=True,
            )

        assert len(service._events) == 5

        service.reset_metrics()

        assert len(service._events) == 0
        assert len(service._history) == 0

    def test_get_all_events_pagination(self, service):
        """Test pagination of get_all_events."""
        # Record 15 events
        for i in range(15):
            service.record_conversion_event(
                conversion_id=f"conv-{i:03d}",
                was_automated=True,
                was_one_click=True,
            )

        # Get first page
        events, total = service.get_all_events(limit=5, offset=0)
        assert len(events) == 5
        assert total == 15

        # Get second page
        events, total = service.get_all_events(limit=5, offset=5)
        assert len(events) == 5
        assert total == 15

        # Get last page
        events, total = service.get_all_events(limit=5, offset=10)
        assert len(events) == 5
        assert total == 15

    def test_get_all_events_date_filter(self, service):
        """Test date filtering in get_all_events."""
        # Record events with specific timestamps
        now = datetime.now(timezone.utc)

        # Add old event
        old_event = ConversionEvent(
            conversion_id="old-conv",
            timestamp=now - timedelta(days=2),
            was_automated=True,
        )
        service._events.append(old_event)

        # Add recent event
        service.record_conversion_event(
            conversion_id="recent-conv",
            was_automated=True,
        )

        # Filter by start date
        start = now - timedelta(days=1)
        events, total = service.get_all_events(start_date=start)
        assert total == 1
        assert events[0]["conversion_id"] == "recent-conv"


class TestAutomationMetricsServiceClass:
    """Tests for service class methods (thread safety, etc.)."""

    def test_concurrent_event_recording(self):
        """Test thread-safe event recording."""
        import threading

        # Reset singleton
        AutomationMetricsService._instance = None

        service = AutomationMetricsService()
        initial_count = len(service._events)

        def record_events():
            for i in range(100):
                service.record_conversion_event(
                    conversion_id=f"conv-{threading.current_thread().name}-{i}",
                    was_automated=True,
                )

        # Create 4 threads
        threads = [threading.Thread(target=record_events, name=f"thread-{i}") for i in range(4)]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Should have 400 new events
        assert len(service._events) == initial_count + 400


class TestModuleLevelFunctions:
    """Tests for module-level convenience functions."""

    def test_record_conversion_event_function(self):
        """Test convenience function for recording events."""
        # Reset singleton
        AutomationMetricsService._instance = None

        event = record_conversion_event(
            conversion_id="test-conv",
            was_automated=True,
        )

        assert event.conversion_id == "test-conv"
        assert event.was_automated is True

    def test_get_current_metrics_function(self):
        """Test convenience function for getting metrics."""
        # Reset singleton
        AutomationMetricsService._instance = None

        service = get_automation_metrics_service()
        service.reset_metrics()

        # Record an event
        record_conversion_event(
            conversion_id="test-conv",
            was_automated=True,
        )

        metrics = get_current_metrics(period_hours=24)

        assert metrics.total_conversions == 1
        assert metrics.automation_rate == 100.0

    def test_get_dashboard_data_function(self):
        """Test convenience function for getting dashboard data."""
        # Reset singleton
        AutomationMetricsService._instance = None

        record_conversion_event(
            conversion_id="test-conv",
            was_automated=True,
        )

        dashboard = get_dashboard_data(period_hours=24)

        assert "metrics" in dashboard
        assert "status" in dashboard


# Need to import threading for the singleton test
import threading


class TestAPIResponseModels:
    """Tests for API response structures."""

    def test_metrics_targets_defined(self):
        """Test that target constants are properly defined."""
        assert TARGET_AUTOMATION_RATE == 95.0
        assert TARGET_ONE_CLICK_RATE == 80.0
        assert TARGET_AUTO_RECOVERY_RATE == 80.0

    def test_snapshot_has_required_fields(self):
        """Test that snapshot has all required fields."""
        snapshot = AutomationMetricsSnapshot()

        assert hasattr(snapshot, "automation_rate")
        assert hasattr(snapshot, "one_click_rate")
        assert hasattr(snapshot, "auto_recovery_rate")
        assert hasattr(snapshot, "avg_conversion_time_seconds")
        assert hasattr(snapshot, "mode_classification_accuracy")
        assert hasattr(snapshot, "avg_user_satisfaction")
        assert hasattr(snapshot, "total_conversions")
        assert hasattr(snapshot, "target_automation_rate")
        assert hasattr(snapshot, "target_one_click_rate")
        assert hasattr(snapshot, "target_auto_recovery_rate")
        assert hasattr(snapshot, "automation_target_met")
        assert hasattr(snapshot, "one_click_target_met")
        assert hasattr(snapshot, "auto_recovery_target_met")
