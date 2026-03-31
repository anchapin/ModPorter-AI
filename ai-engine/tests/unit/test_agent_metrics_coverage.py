import pytest
import time
import threading
from unittest.mock import MagicMock, patch
from datetime import datetime
from agent_metrics.performance_monitor import (
    PerformanceMonitor,
    OperationMetric,
    AggregatedMetrics
)
from agent_metrics.llm_usage_tracker import (
    LLMUsageTracker,
    LLMCall,
    ModelUsageStats
)
from agent_metrics.memory_monitor import (
    MemoryMonitor,
    MemorySnapshot,
    MemoryAlert,
    MemoryTracker
)
from agent_metrics.alerts import (
    AlertManager,
    Alert,
    AlertSeverity
)
from agent_metrics.dashboard import MetricsDashboard

# Test PerformanceMonitor
class TestPerformanceMonitor:
    def test_operation_metric_complete(self):
        metric = OperationMetric(name="test", start_time=time.time())
        time.sleep(0.01)
        metric.complete(success=True)
        assert metric.end_time is not None
        assert metric.duration > 0
        assert metric.success is True

    def test_aggregated_metrics(self):
        agg = AggregatedMetrics(operation_name="test")
        metric1 = OperationMetric(name="test", start_time=100, end_time=110, duration=10, success=True)
        # Manually set end_time since complete() uses time.time()
        metric1.end_time = 110
        
        metric2 = OperationMetric(name="test", start_time=120, end_time=140, duration=20, success=False)
        metric2.end_time = 140
        
        agg.add_metric(metric1)
        assert agg.total_calls == 1
        assert agg.successful_calls == 1
        assert agg.total_duration == 10
        
        agg.add_metric(metric2)
        assert agg.total_calls == 2
        assert agg.failed_calls == 1
        assert agg.total_duration == 30
        assert agg.min_duration == 10
        assert agg.max_duration == 20
        assert agg.avg_duration == 15
        
        d = agg.to_dict()
        assert d["operation_name"] == "test"
        assert d["total_calls"] == 2

    def test_monitor_start_complete(self):
        monitor = PerformanceMonitor(slow_operation_threshold=0.1)
        op_id = monitor.start_operation("test_op", metadata={"key": "value"})
        assert op_id is not None
        
        time.sleep(0.02)
        metric = monitor.complete_operation(op_id, success=True, metadata={"extra": "data"})
        
        assert metric is not None
        assert metric.name == "test_op"
        assert metric.success is True
        assert metric.metadata["key"] == "value"
        assert metric.metadata["extra"] == "data"
        assert metric.duration >= 0.02
        
        metrics = monitor.get_metrics("test_op")
        assert metrics["total_calls"] == 1
        assert metrics["successful_calls"] == 1
        
        all_metrics = monitor.get_metrics()
        assert "test_op" in all_metrics

    def test_monitor_slow_operation_alert(self):
        alert_called = False
        def alert_cb(alert_type, data):
            nonlocal alert_called
            alert_called = True
            assert alert_type == "slow_operation"
            assert data["operation"] == "slow_op"

        monitor = PerformanceMonitor(slow_operation_threshold=0.01)
        monitor.add_alert_callback(alert_cb)
        
        op_id = monitor.start_operation("slow_op")
        time.sleep(0.02)
        monitor.complete_operation(op_id)
        
        assert alert_called is True

    def test_monitor_context_manager(self):
        monitor = PerformanceMonitor()
        with monitor.track_operation("context_op"):
            time.sleep(0.01)
        
        metrics = monitor.get_metrics("context_op")
        assert metrics["total_calls"] == 1

    def test_monitor_decorator(self):
        monitor = PerformanceMonitor()
        
        @monitor.timed("decorated_op")
        def test_func(x):
            return x * 2
            
        result = test_func(5)
        assert result == 10
        
        metrics = monitor.get_metrics("decorated_op")
        assert metrics["total_calls"] == 1
        
        @monitor.timed() # uses func name
        def another_func():
            pass
        another_func()
        assert "another_func" in monitor.get_metrics()

    def test_monitor_summary(self):
        monitor = PerformanceMonitor()
        op1 = monitor.start_operation("op1")
        monitor.complete_operation(op1, success=True)
        op2 = monitor.start_operation("op2")
        monitor.complete_operation(op2, success=False)
        
        summary = monitor.get_summary()
        assert summary["total_operations"] == 2
        assert summary["successful_operations"] == 1
        assert summary["failed_operations"] == 1
        assert summary["operation_types"] == 2
        assert len(summary["slowest_operations"]) > 0

    def test_monitor_reset(self):
        monitor = PerformanceMonitor()
        op_id = monitor.start_operation("test")
        monitor.complete_operation(op_id)
        assert len(monitor.get_metrics()) == 1
        
        monitor.reset()
        assert len(monitor.get_metrics()) == 0
        assert len(monitor.get_recent_operations()) == 0

    def test_monitor_export_prometheus(self):
        monitor = PerformanceMonitor()
        op_id = monitor.start_operation("test-op")
        monitor.complete_operation(op_id)
        
        prometheus_data = monitor.export_prometheus()
        assert "test_op_total" in prometheus_data

# Test LLMUsageTracker
class TestLLMUsageTracker:
    def test_llm_call_cost_calculation(self):
        call = LLMCall(
            call_id="test",
            model="gpt-4",
            provider="openai",
            input_tokens=1000,
            output_tokens=500,
            total_tokens=1500,
            duration=1.0,
            timestamp=time.time()
        )
        cost = call.calculate_cost()
        expected = (1000/1000 * 0.03) + (500/1000 * 0.06)
        assert cost == pytest.approx(expected)

    def test_model_usage_stats(self):
        stats = ModelUsageStats(model="gpt-4")
        call = LLMCall("id", "gpt-4", "p", 100, 50, 150, 1.0, time.time(), success=True, cost=0.01)
        stats.add_call(call)
        assert stats.total_calls == 1
        assert stats.total_cost == 0.01
        
        d = stats.to_dict()
        assert d["model"] == "gpt-4"
        assert d["total_calls"] == 1

    def test_tracker_track_call(self):
        tracker = LLMUsageTracker(cost_alert_threshold=100.0)
        call = tracker.track_call(
            model="gpt-4o",
            provider="openai",
            input_tokens=100,
            output_tokens=50,
            duration=0.5
        )
        
        assert call.model == "gpt-4o"
        assert call.total_tokens == 150
        assert tracker._call_counter == 1
        
        stats = tracker.get_usage_by_model("gpt-4o")
        assert stats["total_calls"] == 1
        assert stats["total_tokens"] == 150
        
        all_stats = tracker.get_usage_by_model()
        assert "gpt-4o" in all_stats

    def test_tracker_cost_alert(self):
        alert_called = False
        def alert_cb(alert_type, data):
            nonlocal alert_called
            alert_called = True
            assert alert_type == "cost_threshold"

        tracker = LLMUsageTracker(cost_alert_threshold=0.000001)
        tracker.add_alert_callback(alert_cb)
        
        tracker.track_call("gpt-4", "openai", 10000, 10000, 1.0)
        assert alert_called is True

    def test_tracker_summary_and_breakdown(self):
        tracker = LLMUsageTracker()
        tracker.track_call("gpt-4", "openai", 100, 50, 0.5)
        tracker.track_call("claude-3-opus", "anthropic", 200, 100, 0.8)
        
        total = tracker.get_total_usage()
        assert total["total_calls"] == 2
        assert total["models_used"] == 2
        
        breakdown = tracker.get_cost_breakdown()
        assert "gpt-4" in breakdown
        assert "claude-3-opus" in breakdown
        assert breakdown["gpt-4"]["percentage"] > 0

    def test_tracker_estimate_cost(self):
        tracker = LLMUsageTracker()
        cost = tracker.estimate_cost("gpt-4", 1000, 1000)
        assert cost == 0.03 + 0.06

    def test_tracker_reset(self):
        tracker = LLMUsageTracker()
        tracker.track_call("gpt-4", "openai", 100, 50, 0.5)
        tracker.reset()
        assert tracker.get_total_usage()["total_calls"] == 0

    def test_tracker_export_prometheus(self):
        tracker = LLMUsageTracker()
        tracker.track_call("gpt-4", "openai", 100, 50, 0.5)
        prometheus_data = tracker.export_prometheus()
        assert "llm_calls_total" in prometheus_data

# Test MemoryMonitor
class TestMemoryMonitor:
    def test_memory_snapshot(self):
        monitor = MemoryMonitor()
        snapshot = monitor.take_snapshot(label="test")
        assert isinstance(snapshot, MemorySnapshot)
        assert snapshot.label == "test"
        assert snapshot.rss_mb >= 0

    def test_memory_threshold_alerts(self):
        alert_called = False
        def alert_cb(alert_type, data):
            nonlocal alert_called
            alert_called = True
            assert "memory" in alert_type

        monitor = MemoryMonitor(warning_threshold_mb=0.001, critical_threshold_mb=0.002)
        monitor.add_alert_callback(alert_cb)
        
        # Take snapshot which should trigger alert if current memory > 0.001MB
        monitor.take_snapshot()
        assert alert_called is True

    def test_memory_growth_and_peak(self):
        monitor = MemoryMonitor()
        monitor.take_snapshot(label="start")
        monitor.take_snapshot(label="end")
        
        growth = monitor.get_memory_growth()
        assert "growth_mb" in growth
        
        peak = monitor.get_peak_usage()
        assert peak["peak_mb"] >= 0

    def test_memory_tracker_context(self):
        monitor = MemoryMonitor()
        with MemoryTracker("test_block", monitor=monitor):
            pass

        history = monitor.get_memory_history()

        assert any("test_block_start" in s["label"] for s in history)
        assert any("test_block_end" in s["label"] for s in history)

    def test_memory_history_and_alerts(self):
        monitor = MemoryMonitor()
        monitor.take_snapshot("s1")
        history = monitor.get_memory_history(limit=1)
        assert len(history) == 1
        
        alerts = monitor.get_alerts()
        assert isinstance(alerts, list)

    def test_memory_reset_and_clear(self):
        monitor = MemoryMonitor()
        monitor.take_snapshot("s1")
        monitor.clear_history()
        assert len(monitor.get_memory_history()) == 0
        
        monitor.reset_baseline()
        assert monitor._baseline is not None

# Test AlertManager
class TestAlertManager:
    def test_alert_creation(self):
        manager = AlertManager()
        alert = manager.create_alert(
            alert_type="test",
            severity=AlertSeverity.WARNING,
            message="Test message",
            data={"foo": "bar"}
        )
        
        assert alert.alert_type == "test"
        assert alert.severity == AlertSeverity.WARNING
        assert alert.message == "Test message"
        
        history = manager.get_alerts()
        assert len(history) == 1
        assert history[0]["alert_type"] == "test"
        
        summary = manager.get_alert_summary()
        assert summary["total_alerts"] == 1
        assert summary["by_severity"]["warning"] == 1

    def test_specific_alerts(self):
        manager = AlertManager()
        manager.alert_slow_operation("op", 10.0)
        manager.alert_memory_usage(800.0, "warning")
        manager.alert_cost_threshold(15.0)
        manager.alert_error_rate(0.5)
        manager.alert_llm_failure("gpt-4", "timeout")
        
        summary = manager.get_alert_summary()
        assert summary["total_alerts"] == 5

    def test_alert_acknowledgment(self):
        manager = AlertManager()
        manager.create_alert("test", AlertSeverity.INFO, "msg")
        
        # Newest first in get_alerts
        alerts = manager.get_alerts()
        assert len(alerts) == 1
        assert alerts[0]["acknowledged"] is False
        
        # Acknowledge the alert at index 0 (which is the only one)
        # Wait, get_alerts returns dicts, but acknowledge_alert uses index in self._alerts
        # self._alerts is appended, so first alert is at index 0
        success = manager.acknowledge_alert(0, acknowledged_by="user")
        assert success is True
        
        alerts = manager.get_alerts()
        assert alerts[0]["acknowledged"] is True
        assert alerts[0]["acknowledged_by"] == "user"

    def test_alert_callbacks(self):
        manager = AlertManager()
        called = False
        def cb(alert):
            nonlocal called
            called = True
            assert alert.alert_type == "test"
            
        manager.add_callback("test", cb)
        manager.create_alert("test", AlertSeverity.INFO, "msg")
        assert called is True
        
        # Wildcard callback
        wildcard_called = False
        def wildcard_cb(alert):
            nonlocal wildcard_called
            wildcard_called = True
            
        manager.add_callback("*", wildcard_cb)
        manager.create_alert("another", AlertSeverity.INFO, "msg")
        assert wildcard_called is True

    def test_alert_rate_limiting(self):
        manager = AlertManager(max_alerts=100)
        # Force a small rate limit for testing
        manager._rate_limit_max = 2
        
        a1 = manager.create_alert("rate_limited", AlertSeverity.INFO, "msg1")
        a2 = manager.create_alert("rate_limited", AlertSeverity.INFO, "msg2")
        a3 = manager.create_alert("rate_limited", AlertSeverity.INFO, "msg3")
        
        assert a1 is not None
        assert a2 is not None
        assert a3 is None # Rate limited

    def test_alert_filtering_advanced(self):
        manager = AlertManager()
        manager.create_alert("t1", AlertSeverity.CRITICAL, "m1")
        manager.create_alert("t1", AlertSeverity.WARNING, "m2")
        manager.create_alert("t2", AlertSeverity.CRITICAL, "m3")
        
        # Acknowledge one
        manager.acknowledge_alert(0)
        
        alerts = manager.get_alerts(unacknowledged_only=True)
        assert len(alerts) == 2
        
        alerts = manager.get_alerts(severity=AlertSeverity.CRITICAL, alert_type="t1")
        assert len(alerts) == 1
        assert alerts[0]["message"] == "m1"

    def test_alert_threshold_management(self):
        manager = AlertManager()
        manager.set_threshold("slow_operation", 10.0)
        assert manager.get_thresholds()["slow_operation"] == 10.0
        
        # Test alert_slow_operation with different severity based on threshold
        # threshold is 10.0. 15.0 is < 2*threshold (WARNING), 25.0 is >= 2*threshold (ERROR)
        a_warn = manager.alert_slow_operation("op1", 15.0)
        assert a_warn.severity == AlertSeverity.WARNING
        
        a_err = manager.alert_slow_operation("op1", 25.0)
        assert a_err.severity == AlertSeverity.ERROR

    def test_alert_callback_removal(self):
        manager = AlertManager()
        called = 0
        def cb(alert):
            nonlocal called
            called += 1
            
        manager.add_callback("test", cb)
        manager.create_alert("test", AlertSeverity.INFO, "m1")
        assert called == 1
        
        manager.remove_callback("test", cb)
        manager.create_alert("test", AlertSeverity.INFO, "m2")
        assert called == 1 # Still 1

    def test_alert_clear(self):
        manager = AlertManager()
        manager.create_alert("test", AlertSeverity.INFO, "m1")
        manager.clear_alerts()
        assert len(manager.get_alerts()) == 0

# Test MetricsDashboard
class TestMetricsDashboard:
    def test_dashboard_get_all(self):
        dashboard = MetricsDashboard()
        data = dashboard.get_all_metrics()
        assert "performance" in data
        assert "llm_usage" in data
        assert "memory" in data
        assert "alerts" in data
        assert "health" in data
        assert "uptime_seconds" in data

    def test_dashboard_summary(self):
        dashboard = MetricsDashboard()
        summary = dashboard.get_summary()
        assert "operations" in summary
        assert "llm" in summary
        assert "memory" in summary

    def test_dashboard_health(self):
        dashboard = MetricsDashboard()
        health = dashboard._get_health_status()
        assert "status" in health
        assert "checks" in health

    def test_dashboard_health_unhealthy_memory(self):
        dashboard = MetricsDashboard()
        with patch("agent_metrics.dashboard.memory_monitor") as mock_memory, \
             patch("agent_metrics.dashboard.alert_manager") as mock_alerts:
            
            mock_memory.get_current_usage.return_value = {"rss_mb": 2000.0}
            mock_alerts.get_thresholds.return_value = {
                "memory_critical": 1000.0,
                "memory_warning": 500.0,
                "error_rate": 0.1
            }
            
            health = dashboard._get_health_status()
            assert health["status"] == "unhealthy"
            assert health["checks"]["memory"] == "critical"

    def test_dashboard_health_degraded_llm(self):
        dashboard = MetricsDashboard()
        with patch("agent_metrics.dashboard.llm_tracker") as mock_llm, \
             patch("agent_metrics.dashboard.memory_monitor") as mock_memory, \
             patch("agent_metrics.dashboard.performance_tracker") as mock_perf, \
             patch("agent_metrics.dashboard.alert_manager") as mock_alerts:
            
            mock_llm.get_total_usage.return_value = {
                "total_calls": 10,
                "successful_calls": 3 # < 50%
            }
            mock_memory.get_current_usage.return_value = {"rss_mb": 100.0}
            mock_perf.get_summary.return_value = {"total_operations": 10, "failed_operations": 0}
            mock_alerts.get_thresholds.return_value = {
                "memory_critical": 1000.0,
                "memory_warning": 500.0,
                "error_rate": 0.1
            }
            mock_alerts.get_alert_summary.return_value = {"unacknowledged": 0}
            
            health = dashboard._get_health_status()
            assert health["status"] == "degraded"
            assert health["checks"]["llm"] == "degraded"

    def test_dashboard_health_error_rate_critical(self):
        dashboard = MetricsDashboard()
        with patch("agent_metrics.dashboard.performance_tracker") as mock_perf, \
             patch("agent_metrics.dashboard.memory_monitor") as mock_memory, \
             patch("agent_metrics.dashboard.alert_manager") as mock_alerts:
            
            mock_perf.get_summary.return_value = {
                "total_operations": 100,
                "failed_operations": 20 # 20% > 10% default threshold
            }
            mock_memory.get_current_usage.return_value = {"rss_mb": 100.0}
            mock_alerts.get_thresholds.return_value = {
                "memory_critical": 1000.0,
                "memory_warning": 500.0,
                "error_rate": 0.1
            }
            
            health = dashboard._get_health_status()
            assert health["status"] == "unhealthy"
            assert health["checks"]["error_rate"] == "critical"

    def test_dashboard_health_alerts_warning(self):
        dashboard = MetricsDashboard()
        with patch("agent_metrics.dashboard.alert_manager") as mock_alerts, \
             patch("agent_metrics.dashboard.memory_monitor") as mock_memory, \
             patch("agent_metrics.dashboard.performance_tracker") as mock_perf:
            
            mock_alerts.get_alert_summary.return_value = {"unacknowledged": 10}
            mock_alerts.get_thresholds.return_value = {
                "memory_critical": 1000.0,
                "memory_warning": 500.0,
                "error_rate": 0.1
            }
            mock_memory.get_current_usage.return_value = {"rss_mb": 100.0}
            mock_perf.get_summary.return_value = {"total_operations": 10, "failed_operations": 0}
            
            health = dashboard._get_health_status()
            assert health["status"] == "degraded"
            assert health["checks"]["alerts"] == "warning"

    def test_dashboard_health_exception_handling(self):
        dashboard = MetricsDashboard()
        with patch("agent_metrics.dashboard.memory_monitor.get_current_usage", side_effect=Exception("error")):
            health = dashboard._get_health_status()
            assert health["checks"]["memory"] == "unknown"

    def test_dashboard_export(self):
        dashboard = MetricsDashboard()
        prometheus = dashboard.export_prometheus()
        assert "# Performance Metrics" in prometheus
        
        json_data = dashboard.export_json()
        assert "performance" in json_data

    def test_dashboard_reset(self):
        dashboard = MetricsDashboard()
        dashboard.reset_all()
        summary = dashboard.get_summary()
        assert summary["operations"]["total"] == 0
