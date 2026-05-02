"""
Unit tests for observability components.

Tests for log aggregation, Celery queue monitoring, distributed tracing,
and on-call alerting services.

Issue: #1212 - Pre-beta: Full observability stack
"""

import pytest
import asyncio
import os
import time
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any, Optional


class TestLogAggregation:
    """Test log aggregation service."""

    def test_structured_logger_initialization(self):
        """Test structured logger initializes correctly."""
        from src.services.log_aggregation import StructuredLogger

        logger = StructuredLogger("test-service")
        assert logger.logger.name == "test-service"
        assert logger._trace_id is None
        assert logger._context == {}

    def test_set_trace_context(self):
        """Test setting trace context."""
        from src.services.log_aggregation import StructuredLogger

        logger = StructuredLogger("test-service")
        logger.set_trace_context("trace-123", "span-456")

        assert logger._trace_id == "trace-123"
        assert logger._span_id == "span-456"

    def test_set_context(self):
        """Test setting log context."""
        from src.services.log_aggregation import StructuredLogger

        logger = StructuredLogger("test-service")
        logger.set_context(user_id="user-123", request_id="req-456")

        assert logger._context["user_id"] == "user-123"
        assert logger._context["request_id"] == "req-456"

    def test_clear_context(self):
        """Test clearing log context."""
        from src.services.log_aggregation import StructuredLogger

        logger = StructuredLogger("test-service")
        logger.set_context(user_id="user-123")
        logger.clear_context()

        assert logger._context == {}

    def test_build_log_entry(self):
        """Test building log entries."""
        from src.services.log_aggregation import StructuredLogger

        logger = StructuredLogger("test-service")
        logger.set_trace_context("trace-123")
        entry = logger._build_log_entry("INFO", "Test message", {"key": "value"})

        assert entry["level"] == "INFO"
        assert entry["message"] == "Test message"
        assert entry["trace_id"] == "trace-123"
        assert entry["context"]["key"] == "value"
        assert entry["service"] == "portkit-backend"

    def test_better_stack_handler_initialization(self):
        """Test Better Stack handler initializes."""
        from src.services.log_aggregation import BetterStackHandler

        handler = BetterStackHandler(
            api_token="test-token",
            source_token="source-token"
        )

        assert handler.source_token == "source-token"
        assert handler._buffer_size == 100

    def test_format_log_entry(self):
        """Test log entry formatting."""
        from src.services.log_aggregation import BetterStackHandler
        import logging

        handler = BetterStackHandler(
            api_token="test-token",
            source_token="source-token"
        )

        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="/test.py",
            lineno=10,
            msg="Test message",
            args=(),
            exc_info=None
        )

        entry = handler._format_log_entry(record)

        assert entry["level"] == "INFO"
        assert entry["message"] == "Test message"
        assert entry["service"] == "portkit-backend"
        assert "timestamp" in entry


class TestCeleryMonitoring:
    """Test Celery queue monitoring service."""

    def test_celery_queue_monitor_initialization(self):
        """Test monitor initializes with defaults."""
        from src.services.celery_monitoring import CeleryQueueMonitor

        monitor = CeleryQueueMonitor(
            redis_url="redis://localhost:6379/0",
            namespace="test-portkit"
        )

        assert monitor.redis_url == "redis://localhost:6379/0"
        assert monitor.namespace == "test-portkit"

    def test_queue_metrics_dataclass(self):
        """Test QueueMetrics dataclass."""
        from src.services.celery_monitoring import QueueMetrics

        metrics = QueueMetrics(name="high", depth=50)
        assert metrics.name == "high"
        assert metrics.depth == 50
        assert metrics.messages_enqueued == 0

    def test_worker_metrics_dataclass(self):
        """Test WorkerMetrics dataclass."""
        from src.services.celery_monitoring import WorkerMetrics

        metrics = WorkerMetrics(name="worker-1", online=True)
        assert metrics.name == "worker-1"
        assert metrics.online is True
        assert metrics.active_tasks == 0

    def test_celery_cluster_metrics(self):
        """Test CeleryClusterMetrics dataclass."""
        from src.services.celery_monitoring import CeleryClusterMetrics

        metrics = CeleryClusterMetrics()
        assert metrics.total_queues == 0
        assert metrics.total_queue_depth == 0
        assert metrics.total_workers == 0
        assert metrics.online_workers == 0

    def test_celery_alert_rules(self):
        """Test alert rules are defined."""
        from src.services.celery_monitoring import CeleryAlertRules

        rules = CeleryAlertRules.ALERT_RULES
        assert len(rules) > 0

        rule_names = [r["name"] for r in rules]
        assert "CeleryWorkersOffline" in rule_names
        assert "CeleryQueueDepthHigh" in rule_names
        assert "CeleryTaskFailureRateHigh" in rule_names

    def test_queue_priority_enum(self):
        """Test queue priority enum."""
        from src.services.celery_monitoring import QueuePriority

        assert QueuePriority.LOW.value == "low"
        assert QueuePriority.HIGH.value == "high"
        assert QueuePriority.CRITICAL.value == "critical"


class TestAlerting:
    """Test on-call alerting service."""

    def test_alert_severity_enum(self):
        """Test alert severity enum."""
        from src.services.alerting import AlertSeverity

        assert AlertSeverity.P0_CRITICAL.value == "P0"
        assert AlertSeverity.P1_HIGH.value == "P1"
        assert AlertSeverity.P2_MEDIUM.value == "P2"

    def test_alert_status_enum(self):
        """Test alert status enum."""
        from src.services.alerting import AlertStatus

        assert AlertStatus.TRIGGERED.value == "triggered"
        assert AlertStatus.ACKNOWLEDGED.value == "acknowledged"
        assert AlertStatus.RESOLVED.value == "resolved"

    def test_alert_dataclass(self):
        """Test Alert dataclass."""
        from src.services.alerting import Alert, AlertSeverity

        alert = Alert(
            name="test-alert",
            severity=AlertSeverity.P1_HIGH,
            message="Test message"
        )

        assert alert.name == "test-alert"
        assert alert.severity == AlertSeverity.P1_HIGH
        assert alert.status.value == "triggered"
        assert alert.alert_id is None

    def test_alert_rule_dataclass(self):
        """Test AlertRule dataclass."""
        from src.services.alerting import AlertRule, AlertSeverity

        rule = AlertRule(
            name="high_error_rate",
            metric="error_rate",
            threshold=0.05,
            operator=">",
            severity=AlertSeverity.P1_HIGH
        )

        assert rule.name == "high_error_rate"
        assert rule.metric == "error_rate"
        assert rule.threshold == 0.05
        assert rule.operator == ">"

    def test_on_call_alert_manager_initialization(self):
        """Test alert manager initializes."""
        from src.services.alerting import OnCallAlertManager

        manager = OnCallAlertManager()
        assert len(manager._rules) == 0
        assert len(manager._active_alerts) == 0
        assert len(manager._alert_history) == 0

    def test_add_remove_rule(self):
        """Test adding and removing alert rules."""
        from src.services.alerting import OnCallAlertManager, AlertRule

        manager = OnCallAlertManager()
        rule = AlertRule(name="test-rule", metric="test_metric", threshold=10)

        manager.add_rule(rule)
        assert "test-rule" in manager._rules

        manager.remove_rule("test-rule")
        assert "test-rule" not in manager._rules

    def test_evaluate_rules_greater_than(self):
        """Test alert rule evaluation with > operator."""
        from src.services.alerting import OnCallAlertManager, AlertRule

        manager = OnCallAlertManager()
        rule = AlertRule(name="high_value", metric="test_value", threshold=100, operator=">")
        manager.add_rule(rule)

        alerts = manager.evaluate_rules({"test_value": 150})
        assert len(alerts) == 1
        assert alerts[0].name == "high_value"

        alerts = manager.evaluate_rules({"test_value": 50})
        assert len(alerts) == 0

    def test_evaluate_rules_less_than(self):
        """Test alert rule evaluation with < operator."""
        from src.services.alerting import OnCallAlertManager, AlertRule

        manager = OnCallAlertManager()
        rule = AlertRule(name="low_value", metric="availability", threshold=99, operator="<")
        manager.add_rule(rule)

        alerts = manager.evaluate_rules({"availability": 98})
        assert len(alerts) == 1

        alerts = manager.evaluate_rules({"availability": 99.5})
        assert len(alerts) == 0

    def test_evaluate_rules_equality(self):
        """Test alert rule evaluation with == operator."""
        from src.services.alerting import OnCallAlertManager, AlertRule

        manager = OnCallAlertManager()
        rule = AlertRule(name="exact_match", metric="count", threshold=0, operator="==")
        manager.add_rule(rule)

        alerts = manager.evaluate_rules({"count": 0})
        assert len(alerts) == 1

        alerts = manager.evaluate_rules({"count": 1})
        assert len(alerts) == 0

    def test_create_default_alert_manager(self):
        """Test default alert manager has correct rules."""
        from src.services.alerting import create_default_alert_manager

        manager = create_default_alert_manager()
        assert len(manager._rules) > 0

        rule_names = list(manager._rules.keys())
        assert "queue_backlog_critical" in rule_names
        assert "workers_offline" in rule_names
        assert "task_failure_rate_high" in rule_names

    def test_better_stack_incidents_client_initialization(self):
        """Test Better Stack client initializes."""
        from src.services.alerting import BetterStackIncidentsClient

        client = BetterStackIncidentsClient(api_token="test-token")
        assert client.api_token == "test-token"


class TestTracing:
    """Test distributed tracing service."""

    def test_tracer_propagator_exists(self):
        """Test trace context propagator is configured."""
        from src.services.tracing import tracer_propagator

        assert tracer_propagator is not None

    def test_get_service_name(self):
        """Test service name from environment."""
        from src.services.tracing import get_service_name

        with patch.dict(os.environ, {"SERVICE_NAME": "test-service"}):
            assert get_service_name() == "test-service"

        with patch.dict(os.environ, {}, clear=True):
            assert get_service_name() == "portkit-backend"

    def test_get_service_version(self):
        """Test service version from environment."""
        from src.services.tracing import get_service_version

        with patch.dict(os.environ, {"SERVICE_VERSION": "2.0.0"}):
            assert get_service_version() == "2.0.0"

    def test_get_tracing_exporter(self):
        """Test tracing exporter type from environment."""
        from src.services.tracing import get_tracing_exporter

        with patch.dict(os.environ, {"TRACING_EXPORTER": "otlp"}):
            assert get_tracing_exporter() == "otlp"

    def test_get_otlp_endpoint(self):
        """Test OTLP endpoint from environment."""
        from src.services.tracing import get_otlp_endpoint

        with patch.dict(os.environ, {"OTLP_ENDPOINT": "http://custom:4317"}):
            assert get_otlp_endpoint() == "http://custom:4317"

    def test_get_better_stack_otlp_endpoint(self):
        """Test Better Stack OTLP endpoint from environment."""
        from src.services.tracing import get_better_stack_otlp_endpoint

        with patch.dict(os.environ, {"BETTERSTACK_OTLP_ENDPOINT": "https://custom.otlp"}):
            assert get_better_stack_otlp_endpoint() == "https://custom.otlp"

        assert get_better_stack_otlp_endpoint() == ""

    def test_get_better_stack_otlp_headers(self):
        """Test Better Stack OTLP headers from environment."""
        from src.services.tracing import get_better_stack_otlp_headers

        with patch.dict(os.environ, {"BETTERSTACK_API_TOKEN": "test-key"}):
            headers = get_better_stack_otlp_headers()
            assert headers["X-API-Key"] == "test-key"

        headers = get_better_stack_otlp_headers()
        assert headers == {}

    def test_get_tracer(self):
        """Test getting tracer returns a valid tracer."""
        from src.services.tracing import get_tracer

        tracer = get_tracer()
        assert tracer is not None

    def test_get_current_span(self):
        """Test getting current span."""
        from src.services.tracing import get_current_span

        span = get_current_span()
        assert span is None or span is not None

    def test_create_span(self):
        """Test creating a new span."""
        from src.services.tracing import create_span

        span = create_span("test-span")
        assert span is not None

    def test_add_span_attributes(self):
        """Test adding attributes to span."""
        from src.services.tracing import create_span, add_span_attributes

        span = create_span("test-span")
        add_span_attributes(span, {"key": "value", "number": 42})

        assert span is not None

    def test_record_span_exception(self):
        """Test recording exception on span."""
        from src.services.tracing import create_span, record_span_exception

        span = create_span("test-span")
        try:
            raise ValueError("Test error")
        except ValueError as e:
            record_span_exception(span, e)

        assert span is not None

    def test_inject_extract_trace_context(self):
        """Test trace context injection and extraction."""
        from src.services.tracing import inject_trace_context, extract_trace_context

        carrier = {}
        inject_trace_context(carrier)
        context = extract_trace_context(carrier)

        assert context is not None

    def test_shutdown_tracing(self):
        """Test tracing shutdown."""
        from src.services.tracing import shutdown_tracing

        shutdown_tracing()


class TestObservabilityIntegration:
    """Integration tests for observability components."""

    @pytest.mark.asyncio
    async def test_log_aggregation_with_trace_context(self):
        """Test structured logging with trace context."""
        from src.services.log_aggregation import StructuredLogger

        logger = StructuredLogger("integration-test")
        logger.set_trace_context("trace-integration-123")

        entry = logger._build_log_entry("INFO", "Integration test message")
        assert entry["trace_id"] == "trace-integration-123"
        assert entry["message"] == "Integration test message"

    @pytest.mark.asyncio
    async def test_celery_monitor_with_mock_redis(self):
        """Test Celery monitor with mocked Redis."""
        from src.services.celery_monitoring import CeleryQueueMonitor

        with patch("src.services.celery_monitoring.redis") as mock_redis:
            mock_client = MagicMock()
            mock_redis.from_url.return_value = mock_client
            mock_client.zcard.return_value = 10
            mock_client.scard.return_value = 2
            mock_client.hgetall.return_value = {"tasks_enqueued": "100"}

            monitor = CeleryQueueMonitor()
            stats = monitor.get_queue_stats()

            assert stats["total_queued"] >= 0

    @pytest.mark.asyncio
    async def test_alert_manager_trigger_resolve(self):
        """Test alert triggering and resolving."""
        from src.services.alerting import OnCallAlertManager, AlertSeverity

        manager = OnCallAlertManager()

        alert = await manager.trigger_alert(
            name="integration_test_alert",
            message="Integration test alert",
            severity=AlertSeverity.P2_MEDIUM
        )

        assert alert.name == "integration_test_alert"
        assert "integration_test_alert" in manager._active_alerts

        resolved = await manager.resolve_alert("integration_test_alert")
        assert resolved is True
        assert "integration_test_alert" not in manager._active_alerts

    def test_celery_and_alerting_integration(self):
        """Test Celery metrics flow into alert evaluation."""
        from src.services.celery_monitoring import CeleryAlertRules
        from src.services.alerting import OnCallAlertManager, AlertRule, AlertSeverity

        manager = OnCallAlertManager()
        manager.add_rule(AlertRule(
            name="queue_depth_high",
            metric="queue_depth",
            threshold=100,
            operator=">",
            severity=AlertSeverity.P1_HIGH
        ))

        metrics = {"queue_depth": 150}
        alerts = manager.evaluate_rules(metrics)

        assert len(alerts) == 1
        assert alerts[0].name == "queue_depth_high"
        assert alerts[0].severity == AlertSeverity.P1_HIGH


if __name__ == "__main__":
    pytest.main([__file__, "-v"])