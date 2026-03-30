"""
Comprehensive observability testing suite.
Tests metrics collection, distributed tracing, log aggregation, and alerting.
"""

import pytest
import asyncio
import time
import json
import logging
from unittest.mock import AsyncMock, patch, MagicMock
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from collections import defaultdict
import uuid

# Set up imports
try:
    from modporter.cli.main import convert_mod
    IMPORTS_AVAILABLE = True
except ImportError:
    IMPORTS_AVAILABLE = False


pytestmark = pytest.mark.skipif(not IMPORTS_AVAILABLE, reason="Required imports unavailable")


# ==================== Metrics Implementation ====================

class MetricsCollector:
    """Collect and aggregate metrics."""
    
    def __init__(self):
        self.counters = defaultdict(int)
        self.gauges = defaultdict(float)
        self.histograms = defaultdict(list)
        self.timers = defaultdict(list)
    
    def increment_counter(self, name: str, value: int = 1, tags: Dict = None):
        """Increment counter metric."""
        key = f"{name}:{json.dumps(tags or {})}"
        self.counters[key] += value
    
    def set_gauge(self, name: str, value: float, tags: Dict = None):
        """Set gauge metric."""
        key = f"{name}:{json.dumps(tags or {})}"
        self.gauges[key] = value
    
    def record_histogram(self, name: str, value: float, tags: Dict = None):
        """Record histogram metric."""
        key = f"{name}:{json.dumps(tags or {})}"
        self.histograms[key].append(value)
    
    def record_timer(self, name: str, duration: float, tags: Dict = None):
        """Record timer metric."""
        key = f"{name}:{json.dumps(tags or {})}"
        self.timers[key].append(duration)
    
    def get_counter(self, name: str) -> int:
        """Get counter value."""
        for key in self.counters:
            if key.startswith(name):
                return self.counters[key]
        return 0
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get all metrics."""
        return {
            "counters": dict(self.counters),
            "gauges": dict(self.gauges),
            "histograms": dict(self.histograms),
            "timers": dict(self.timers)
        }


# ==================== Tracing Implementation ====================

class TraceContext:
    """Distributed trace context."""
    
    def __init__(self, trace_id: str = None, span_id: str = None):
        self.trace_id = trace_id or str(uuid.uuid4())
        self.span_id = span_id or str(uuid.uuid4())
        self.parent_span_id = None
        self.baggage = {}
    
    def new_child_span(self) -> 'TraceContext':
        """Create child span."""
        child = TraceContext(trace_id=self.trace_id)
        child.parent_span_id = self.span_id
        child.baggage = self.baggage.copy()
        return child
    
    def set_baggage(self, key: str, value: str):
        """Set baggage item."""
        self.baggage[key] = value
    
    def get_baggage(self, key: str) -> Optional[str]:
        """Get baggage item."""
        return self.baggage.get(key)


class TracingCollector:
    """Collect distributed traces."""
    
    def __init__(self):
        self.spans = []
        self.current_trace = TraceContext()
    
    def start_span(self, operation_name: str) -> Dict[str, Any]:
        """Start a new span."""
        span = {
            "trace_id": self.current_trace.trace_id,
            "span_id": self.current_trace.span_id,
            "operation_name": operation_name,
            "start_time": time.time(),
            "tags": {},
            "logs": []
        }
        self.spans.append(span)
        return span
    
    def end_span(self, span: Dict[str, Any]):
        """End a span."""
        span["end_time"] = time.time()
        span["duration"] = span["end_time"] - span["start_time"]
    
    def add_tag(self, span: Dict[str, Any], key: str, value: Any):
        """Add tag to span."""
        span["tags"][key] = value
    
    def log_event(self, span: Dict[str, Any], event: str, fields: Dict = None):
        """Log event in span."""
        span["logs"].append({
            "timestamp": time.time(),
            "event": event,
            "fields": fields or {}
        })
    
    def get_traces(self) -> List[Dict[str, Any]]:
        """Get all traces."""
        return self.spans


# ==================== Logging Implementation ====================

class StructuredLogger:
    """Structured logging with context."""
    
    def __init__(self):
        self.logs = []
        self.level = logging.INFO
    
    def log(self, level: str, message: str, context: Dict = None, trace_id: str = None):
        """Log structured message."""
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": level,
            "message": message,
            "context": context or {},
            "trace_id": trace_id
        }
        self.logs.append(log_entry)
    
    def info(self, message: str, context: Dict = None, trace_id: str = None):
        """Log info level."""
        self.log("INFO", message, context, trace_id)
    
    def error(self, message: str, context: Dict = None, trace_id: str = None):
        """Log error level."""
        self.log("ERROR", message, context, trace_id)
    
    def warning(self, message: str, context: Dict = None, trace_id: str = None):
        """Log warning level."""
        self.log("WARN", message, context, trace_id)
    
    def debug(self, message: str, context: Dict = None, trace_id: str = None):
        """Log debug level."""
        self.log("DEBUG", message, context, trace_id)
    
    def get_logs(self, level: str = None, trace_id: str = None) -> List[Dict[str, Any]]:
        """Get logs with optional filtering."""
        logs = self.logs
        if level:
            logs = [l for l in logs if l["level"] == level]
        if trace_id:
            logs = [l for l in logs if l["trace_id"] == trace_id]
        return logs


# ==================== Alerting Implementation ====================

class AlertRule:
    """Alert rule definition."""
    
    def __init__(self, name: str, metric: str, threshold: float, operator: str = ">"):
        self.name = name
        self.metric = metric
        self.threshold = threshold
        self.operator = operator
        self.triggered = False
    
    def evaluate(self, value: float) -> bool:
        """Evaluate alert condition."""
        if self.operator == ">":
            triggered = value > self.threshold
        elif self.operator == "<":
            triggered = value < self.threshold
        elif self.operator == ">=":
            triggered = value >= self.threshold
        elif self.operator == "<=":
            triggered = value <= self.threshold
        else:
            triggered = False
        
        self.triggered = triggered
        return triggered


class AlertManager:
    """Manage alerts and alert rules."""
    
    def __init__(self):
        self.rules = {}
        self.alerts = []
        self.alert_history = []
    
    def add_rule(self, rule: AlertRule):
        """Add alert rule."""
        self.rules[rule.name] = rule
    
    def evaluate_rules(self, metrics: Dict[str, float]):
        """Evaluate all rules against metrics."""
        for rule in self.rules.values():
            if rule.metric in metrics:
                if rule.evaluate(metrics[rule.metric]):
                    alert = {
                        "rule": rule.name,
                        "metric": rule.metric,
                        "value": metrics[rule.metric],
                        "threshold": rule.threshold,
                        "timestamp": datetime.utcnow().isoformat(),
                        "severity": "high"
                    }
                    self.alerts.append(alert)
                    self.alert_history.append(alert)
    
    def clear_alerts(self):
        """Clear current alerts."""
        self.alerts = []
    
    def get_alerts(self) -> List[Dict[str, Any]]:
        """Get current alerts."""
        return self.alerts
    
    def get_alert_history(self) -> List[Dict[str, Any]]:
        """Get alert history."""
        return self.alert_history


# ==================== Test Fixtures ====================

@pytest.fixture
def metrics_collector():
    """Create metrics collector."""
    return MetricsCollector()


@pytest.fixture
def tracing_collector():
    """Create tracing collector."""
    return TracingCollector()


@pytest.fixture
def structured_logger():
    """Create structured logger."""
    return StructuredLogger()


@pytest.fixture
def alert_manager():
    """Create alert manager."""
    return AlertManager()


# ==================== Metrics Collection Tests ====================

class TestMetricsCollection:
    """Test metrics collection and aggregation."""
    
    def test_counter_increment(self, metrics_collector):
        """Test counter increment."""
        metrics_collector.increment_counter("requests_total", 1)
        metrics_collector.increment_counter("requests_total", 1)
        metrics_collector.increment_counter("requests_total", 1)
        
        count = metrics_collector.get_counter("requests_total")
        assert count == 3
    
    def test_counter_with_tags(self, metrics_collector):
        """Test counter with tags."""
        tags = {"endpoint": "/api/convert", "method": "POST"}
        metrics_collector.increment_counter("http_requests", 1, tags)
        metrics_collector.increment_counter("http_requests", 1, tags)
        
        metrics = metrics_collector.get_metrics()
        assert "counters" in metrics
    
    def test_gauge_metric(self, metrics_collector):
        """Test gauge metric."""
        metrics_collector.set_gauge("memory_usage_bytes", 1024000)
        metrics_collector.set_gauge("memory_usage_bytes", 1536000)
        
        metrics = metrics_collector.get_metrics()
        assert "gauges" in metrics
    
    def test_histogram_recording(self, metrics_collector):
        """Test histogram recording."""
        response_times = [0.010, 0.015, 0.012, 0.020, 0.018]
        
        for time_val in response_times:
            metrics_collector.record_histogram("response_time_seconds", time_val)
        
        metrics = metrics_collector.get_metrics()
        assert len(metrics["histograms"]) > 0
    
    def test_timer_recording(self, metrics_collector):
        """Test timer recording."""
        durations = [0.5, 0.6, 0.55, 0.65]
        
        for duration in durations:
            metrics_collector.record_timer("operation_duration", duration)
        
        metrics = metrics_collector.get_metrics()
        assert "timers" in metrics
    
    @pytest.mark.asyncio
    async def test_metric_aggregation(self, metrics_collector):
        """Test metric aggregation over time."""
        for i in range(100):
            metrics_collector.increment_counter("processed_items", 1)
            await asyncio.sleep(0.001)
        
        count = metrics_collector.get_counter("processed_items")
        assert count == 100
    
    def test_multiple_metric_types(self, metrics_collector):
        """Test tracking multiple metric types."""
        # Counters
        metrics_collector.increment_counter("events_total", 5)
        
        # Gauges
        metrics_collector.set_gauge("queue_depth", 42)
        
        # Histograms
        metrics_collector.record_histogram("latency_ms", 150)
        
        # Timers
        metrics_collector.record_timer("operation_time", 2.5)
        
        metrics = metrics_collector.get_metrics()
        assert len(metrics["counters"]) > 0
        assert len(metrics["gauges"]) > 0
        assert len(metrics["histograms"]) > 0
        assert len(metrics["timers"]) > 0


# ==================== Distributed Tracing Tests ====================

class TestDistributedTracing:
    """Test distributed tracing and span collection."""
    
    def test_trace_context_creation(self):
        """Test trace context creation."""
        trace = TraceContext()
        
        assert trace.trace_id is not None
        assert trace.span_id is not None
        assert trace.parent_span_id is None
    
    def test_child_span_creation(self):
        """Test child span creation."""
        parent = TraceContext()
        child = parent.new_child_span()
        
        assert child.trace_id == parent.trace_id
        assert child.parent_span_id == parent.span_id
        assert child.span_id != parent.span_id
    
    def test_baggage_propagation(self):
        """Test baggage propagation across spans."""
        parent = TraceContext()
        parent.set_baggage("user_id", "user123")
        parent.set_baggage("request_id", "req456")
        
        child = parent.new_child_span()
        
        assert child.get_baggage("user_id") == "user123"
        assert child.get_baggage("request_id") == "req456"
    
    def test_span_recording(self, tracing_collector):
        """Test span recording."""
        span = tracing_collector.start_span("database_query")
        
        time.sleep(0.01)
        tracing_collector.end_span(span)
        
        assert span["duration"] >= 0.01
    
    def test_span_tagging(self, tracing_collector):
        """Test span tagging."""
        span = tracing_collector.start_span("api_request")
        tracing_collector.add_tag(span, "http.method", "POST")
        tracing_collector.add_tag(span, "http.status_code", 200)
        
        assert span["tags"]["http.method"] == "POST"
        assert span["tags"]["http.status_code"] == 200
    
    def test_span_logging(self, tracing_collector):
        """Test span event logging."""
        span = tracing_collector.start_span("transaction")
        
        tracing_collector.log_event(span, "transaction_started")
        tracing_collector.log_event(span, "query_executed", {"rows": 100})
        tracing_collector.log_event(span, "transaction_committed")
        
        assert len(span["logs"]) == 3
    
    @pytest.mark.asyncio
    async def test_async_span_tracking(self, tracing_collector):
        """Test async span tracking."""
        parent_span = tracing_collector.start_span("parent_operation")
        
        async def child_operation():
            child_span = tracing_collector.start_span("child_operation")
            tracing_collector.add_tag(child_span, "operation.order", 1)
            await asyncio.sleep(0.01)
            tracing_collector.end_span(child_span)
        
        await child_operation()
        tracing_collector.end_span(parent_span)
        
        traces = tracing_collector.get_traces()
        assert len(traces) == 2
    
    def test_trace_correlation(self, tracing_collector):
        """Test trace correlation across services."""
        # Simulate cross-service request
        original_trace_id = tracing_collector.current_trace.trace_id
        
        # Service A
        span_a = tracing_collector.start_span("service_a_operation")
        tracing_collector.add_tag(span_a, "service", "service_a")
        tracing_collector.end_span(span_a)
        
        # Service B receives same trace_id
        service_b_trace = TraceContext(trace_id=original_trace_id)
        
        span_b = tracing_collector.start_span("service_b_operation")
        tracing_collector.add_tag(span_b, "service", "service_b")
        tracing_collector.end_span(span_b)
        
        traces = tracing_collector.get_traces()
        # Both spans should have same trace_id
        assert all(span["trace_id"] == original_trace_id for span in traces)


# ==================== Log Aggregation Tests ====================

class TestLogAggregation:
    """Test log collection and aggregation."""
    
    def test_structured_logging(self, structured_logger):
        """Test structured logging."""
        structured_logger.info(
            "API request received",
            {"endpoint": "/api/convert", "method": "POST"},
            trace_id="trace123"
        )
        
        logs = structured_logger.get_logs()
        assert len(logs) == 1
        assert logs[0]["message"] == "API request received"
    
    def test_log_filtering_by_level(self, structured_logger):
        """Test log filtering by level."""
        structured_logger.info("Info message")
        structured_logger.error("Error message")
        structured_logger.warning("Warning message")
        
        errors = structured_logger.get_logs(level="ERROR")
        assert len(errors) == 1
        assert errors[0]["message"] == "Error message"
    
    def test_log_filtering_by_trace(self, structured_logger):
        """Test log filtering by trace ID."""
        structured_logger.info("Request start", trace_id="trace123")
        structured_logger.info("Request processing", trace_id="trace123")
        structured_logger.info("Request complete", trace_id="trace456")
        
        trace_logs = structured_logger.get_logs(trace_id="trace123")
        assert len(trace_logs) == 2
    
    @pytest.mark.asyncio
    async def test_async_logging_context(self, structured_logger):
        """Test async logging with context."""
        trace_id = "trace789"
        
        async def operation():
            structured_logger.info("Operation started", trace_id=trace_id)
            await asyncio.sleep(0.01)
            structured_logger.info("Operation completed", trace_id=trace_id)
        
        await operation()
        
        logs = structured_logger.get_logs(trace_id=trace_id)
        assert len(logs) == 2
    
    def test_error_context_logging(self, structured_logger):
        """Test error logging with context."""
        try:
            raise ValueError("Test error")
        except ValueError as e:
            structured_logger.error(
                "Operation failed",
                {"error_type": type(e).__name__, "error_message": str(e)},
                trace_id="error123"
            )
        
        errors = structured_logger.get_logs(level="ERROR")
        assert len(errors) == 1
        assert "error_type" in errors[0]["context"]
    
    def test_multiple_log_levels(self, structured_logger):
        """Test logging all severity levels."""
        structured_logger.debug("Debug info", {"detail": "low level"})
        structured_logger.info("General info", {"detail": "operational"})
        structured_logger.warning("Potential issue", {"detail": "warning"})
        structured_logger.error("Error occurred", {"detail": "failure"})
        
        all_logs = structured_logger.get_logs()
        assert len(all_logs) == 4
        assert all_logs[0]["level"] == "DEBUG"
        assert all_logs[3]["level"] == "ERROR"


# ==================== Alerting Tests ====================

class TestAlerting:
    """Test alert rules and alerting system."""
    
    def test_alert_rule_threshold_exceeded(self, alert_manager):
        """Test alert triggers when threshold exceeded."""
        rule = AlertRule("high_error_rate", "error_rate", 0.05, ">")
        alert_manager.add_rule(rule)
        
        metrics = {"error_rate": 0.10}
        alert_manager.evaluate_rules(metrics)
        
        alerts = alert_manager.get_alerts()
        assert len(alerts) == 1
        assert alerts[0]["rule"] == "high_error_rate"
    
    def test_alert_rule_threshold_not_exceeded(self, alert_manager):
        """Test no alert when threshold not exceeded."""
        rule = AlertRule("high_error_rate", "error_rate", 0.05, ">")
        alert_manager.add_rule(rule)
        
        metrics = {"error_rate": 0.02}
        alert_manager.evaluate_rules(metrics)
        
        alerts = alert_manager.get_alerts()
        assert len(alerts) == 0
    
    def test_multiple_alert_rules(self, alert_manager):
        """Test multiple alert rules."""
        alert_manager.add_rule(AlertRule("high_latency", "p99_latency_ms", 500, ">"))
        alert_manager.add_rule(AlertRule("low_availability", "uptime_percent", 99.5, "<"))
        alert_manager.add_rule(AlertRule("queue_building", "queue_depth", 100, ">"))
        
        metrics = {
            "p99_latency_ms": 600,
            "uptime_percent": 99.0,
            "queue_depth": 50
        }
        alert_manager.evaluate_rules(metrics)
        
        alerts = alert_manager.get_alerts()
        assert len(alerts) == 2
    
    def test_alert_operators(self, alert_manager):
        """Test different alert operators."""
        # Greater than
        rule_gt = AlertRule("threshold_gt", "value", 100, ">")
        assert rule_gt.evaluate(150) is True
        assert rule_gt.evaluate(50) is False
        
        # Less than
        rule_lt = AlertRule("threshold_lt", "value", 10, "<")
        assert rule_lt.evaluate(5) is True
        assert rule_lt.evaluate(15) is False
        
        # Greater than or equal
        rule_gte = AlertRule("threshold_gte", "value", 100, ">=")
        assert rule_gte.evaluate(100) is True
        assert rule_gte.evaluate(99) is False
        
        # Less than or equal
        rule_lte = AlertRule("threshold_lte", "value", 100, "<=")
        assert rule_lte.evaluate(100) is True
        assert rule_lte.evaluate(101) is False
    
    def test_alert_history(self, alert_manager):
        """Test alert history tracking."""
        rule = AlertRule("test_alert", "metric", 50, ">")
        alert_manager.add_rule(rule)
        
        # Trigger alert multiple times
        alert_manager.evaluate_rules({"metric": 100})
        alert_manager.evaluate_rules({"metric": 150})
        alert_manager.evaluate_rules({"metric": 200})
        
        history = alert_manager.get_alert_history()
        assert len(history) == 3
    
    @pytest.mark.asyncio
    async def test_alert_clearing(self, alert_manager):
        """Test alert clearing."""
        rule = AlertRule("transient_alert", "metric", 100, ">")
        alert_manager.add_rule(rule)
        
        # Trigger alert
        alert_manager.evaluate_rules({"metric": 150})
        assert len(alert_manager.get_alerts()) == 1
        
        # Clear alerts
        alert_manager.clear_alerts()
        assert len(alert_manager.get_alerts()) == 0
        
        # History should still be available
        assert len(alert_manager.get_alert_history()) == 1


# ==================== End-to-End Observability Tests ====================

class TestObservabilityIntegration:
    """Test integration of all observability components."""
    
    @pytest.mark.asyncio
    async def test_end_to_end_observability(self, metrics_collector, tracing_collector, structured_logger, alert_manager):
        """Test complete observability pipeline."""
        trace_id = str(uuid.uuid4())
        
        # Start operation trace
        span = tracing_collector.start_span("end_to_end_operation")
        tracing_collector.add_tag(span, "trace_id", trace_id)
        
        # Log operation start
        structured_logger.info("Operation started", {"operation": "test"}, trace_id)
        
        # Simulate work with metrics
        start_time = time.time()
        for i in range(10):
            metrics_collector.increment_counter("iterations", 1)
            await asyncio.sleep(0.01)
        
        duration = time.time() - start_time
        metrics_collector.record_timer("operation_duration", duration)
        
        # Log operation completion
        structured_logger.info("Operation completed", {"iterations": 10}, trace_id)
        
        # End span
        tracing_collector.end_span(span)
        
        # Verify all components recorded data
        metrics = metrics_collector.get_metrics()
        traces = tracing_collector.get_traces()
        logs = structured_logger.get_logs(trace_id=trace_id)
        
        assert metrics["counters"]
        assert len(traces) == 1
        assert len(logs) == 2
    
    @pytest.mark.asyncio
    async def test_observability_with_errors(self, metrics_collector, structured_logger, alert_manager):
        """Test observability during error conditions."""
        error_count = 0
        
        async def failing_operation():
            nonlocal error_count
            for i in range(10):
                try:
                    if i % 3 == 0:
                        raise RuntimeError("Simulated error")
                    metrics_collector.increment_counter("successful_ops", 1)
                except RuntimeError:
                    error_count += 1
                    metrics_collector.increment_counter("failed_ops", 1)
                    structured_logger.error("Operation failed", {"iteration": i})
        
        await failing_operation()
        
        # Check metrics
        metrics = metrics_collector.get_metrics()
        assert "counters" in metrics
        
        # Check error logs
        error_logs = structured_logger.get_logs(level="ERROR")
        assert len(error_logs) > 0
    
    def test_observability_performance_degradation(self, metrics_collector, alert_manager):
        """Test alerting on performance degradation."""
        # Set up alert
        alert_manager.add_rule(AlertRule("high_latency", "p95_latency_ms", 200, ">"))
        
        # Simulate latency increase
        latencies = [50, 75, 100, 150, 250, 350]
        
        for latency in latencies:
            metrics_collector.record_histogram("response_times", latency)
            alert_manager.evaluate_rules({"p95_latency_ms": latency})
        
        # Should have alerts for high latency values
        alerts = alert_manager.get_alerts()
        assert len(alerts) > 0


class TestMetricsPercentiles:
    """Test percentile calculations for metrics."""
    
    def test_percentile_calculation(self, metrics_collector):
        """Test percentile calculation from histogram."""
        values = list(range(1, 101))  # 1 to 100
        
        for val in values:
            metrics_collector.record_histogram("response_time", val)
        
        metrics = metrics_collector.get_metrics()
        histogram_values = metrics["histograms"]["response_time:{}"]
        
        sorted_vals = sorted(histogram_values)
        # Use proper percentile calculation (clamped index)
        idx_50 = min(int(len(sorted_vals) * 0.50), len(sorted_vals) - 1)
        idx_95 = min(int(len(sorted_vals) * 0.95), len(sorted_vals) - 1)
        idx_99 = min(int(len(sorted_vals) * 0.99), len(sorted_vals) - 1)
        
        p50 = sorted_vals[idx_50]
        p95 = sorted_vals[idx_95]
        p99 = sorted_vals[idx_99]
        
        # Assert approximate values (not exact due to percentile computation)
        assert 40 <= p50 <= 60
        assert 90 <= p95 <= 100
        assert 95 <= p99 <= 100
    
    def test_metric_cardinality(self, metrics_collector):
        """Test managing metric cardinality."""
        # Add metrics with high cardinality
        for user_id in range(100):
            metrics_collector.increment_counter(
                "user_requests",
                1,
                {"user_id": str(user_id)}
            )
        
        metrics = metrics_collector.get_metrics()
        # Should have many counter entries due to tags
        assert len(metrics["counters"]) >= 100
    
    def test_metrics_aggregation_window(self, metrics_collector):
        """Test metrics aggregation over time window."""
        # Simulate 60 seconds of data in 10 windows
        for window in range(6):
            for _ in range(100):
                metrics_collector.increment_counter("events", 1)
        
        count = metrics_collector.get_counter("events")
        assert count == 600
