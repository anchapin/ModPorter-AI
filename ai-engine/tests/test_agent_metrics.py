"""
Tests for agent_metrics module
"""

import pytest
import time
from unittest.mock import Mock


class TestAlertManager:
    """Test AlertManager class"""

    @pytest.fixture
    def alert_mgr(self):
        """Create AlertManager instance"""
        from agent_metrics.alerts import AlertManager
        return AlertManager()

    def test_manager_initialization(self, alert_mgr):
        """Test AlertManager initializes correctly"""
        assert alert_mgr._alerts == []
        assert alert_mgr._callbacks == {}

    def test_create_alert(self, alert_mgr):
        """Test creating an alert"""
        from agent_metrics.alerts import AlertSeverity

        alert = alert_mgr.create_alert(
            alert_type="test_type",
            severity=AlertSeverity.INFO,
            message="Test alert message"
        )

        assert alert is not None
        assert alert.alert_type == "test_type"
        assert len(alert_mgr._alerts) == 1

    def test_create_alert_with_data(self, alert_mgr):
        """Test creating an alert with additional data"""
        from agent_metrics.alerts import AlertSeverity

        alert = alert_mgr.create_alert(
            alert_type="test_type",
            severity=AlertSeverity.CRITICAL,
            message="Critical alert",
            data={"operation": "conversion", "duration": 10.5},
        )

        assert alert.data == {"operation": "conversion", "duration": 10.5}

    def test_get_alerts(self, alert_mgr):
        """Test retrieving alerts"""
        from agent_metrics.alerts import AlertSeverity

        alert_mgr.create_alert("type1", AlertSeverity.INFO, "msg1")
        alert_mgr.create_alert("type2", AlertSeverity.WARNING, "msg2")

        alerts = alert_mgr.get_alerts()
        assert len(alerts) == 2

    def test_get_alerts_by_severity(self, alert_mgr):
        """Test filtering alerts by severity"""
        from agent_metrics.alerts import AlertSeverity

        alert_mgr.create_alert("type1", AlertSeverity.INFO, "info msg")
        alert_mgr.create_alert("type2", AlertSeverity.ERROR, "error msg")
        alert_mgr.create_alert("type3", AlertSeverity.ERROR, "error msg 2")

        error_alerts = alert_mgr.get_alerts(severity=AlertSeverity.ERROR)
        assert len(error_alerts) == 2

    def test_get_alerts_by_type(self, alert_mgr):
        """Test filtering alerts by type"""
        from agent_metrics.alerts import AlertSeverity

        alert_mgr.create_alert("slow_op", AlertSeverity.WARNING, "slow")
        alert_mgr.create_alert("slow_op", AlertSeverity.WARNING, "slow2")
        alert_mgr.create_alert("memory", AlertSeverity.CRITICAL, "mem")

        slow_op_alerts = alert_mgr.get_alerts(alert_type="slow_op")
        assert len(slow_op_alerts) == 2

    def test_clear_alerts(self, alert_mgr):
        """Test clearing alerts"""
        from agent_metrics.alerts import AlertSeverity

        alert_mgr.create_alert("type1", AlertSeverity.INFO, "msg1")
        alert_mgr.create_alert("type2", AlertSeverity.WARNING, "msg2")

        alert_mgr.clear_alerts()
        assert len(alert_mgr._alerts) == 0

    def test_max_alerts_limit(self, alert_mgr):
        """Test max alerts limit is enforced"""
        from agent_metrics.alerts import AlertSeverity

        # Set low limit
        alert_mgr._max_alerts = 3

        alert_mgr.create_alert("type1", AlertSeverity.INFO, "msg1")
        alert_mgr.create_alert("type2", AlertSeverity.INFO, "msg2")
        alert_mgr.create_alert("type3", AlertSeverity.INFO, "msg3")
        alert_mgr.create_alert("type4", AlertSeverity.INFO, "msg4")

        assert len(alert_mgr._alerts) == 3

    def test_add_and_remove_callback(self, alert_mgr):
        """Test adding and removing alert callbacks"""
        callback = Mock()
        
        # Add callback
        alert_mgr.add_callback("test_type", callback)
        assert callback in alert_mgr._callbacks["test_type"]
        
        # Remove callback
        alert_mgr.remove_callback("test_type", callback)
        assert callback not in alert_mgr._callbacks["test_type"]


class TestPerformanceMonitor:
    """Test PerformanceMonitor class"""

    @pytest.fixture
    def perf_monitor(self):
        """Create PerformanceMonitor instance"""
        from agent_metrics.performance_monitor import PerformanceMonitor
        return PerformanceMonitor()

    def test_monitor_initialization(self, perf_monitor):
        """Test PerformanceMonitor initializes correctly"""
        assert perf_monitor._active_operations == {}
        assert perf_monitor._completed_operations == []
        assert perf_monitor._aggregated_metrics is not None

    def test_start_and_complete_operation(self, perf_monitor):
        """Test starting and completing an operation"""
        op_id = perf_monitor.start_operation("test_op")

        assert op_id is not None
        assert "test_op" in op_id

        # Complete the operation
        metric = perf_monitor.complete_operation(op_id, success=True)

        assert metric is not None
        assert metric.success is True
        assert metric.duration is not None

    def test_complete_operation_error(self, perf_monitor):
        """Test completing an operation with error"""
        op_id = perf_monitor.start_operation("test_op")

        metric = perf_monitor.complete_operation(op_id, success=False, error="Test error")

        assert metric.success is False
        assert metric.error == "Test error"

    def test_get_metrics(self, perf_monitor):
        """Test getting operation metrics"""
        op_id = perf_monitor.start_operation("test_op")
        perf_monitor.complete_operation(op_id, success=True)

        metrics = perf_monitor.get_metrics()
        assert "test_op" in metrics

    def test_get_summary(self, perf_monitor):
        """Test getting performance summary"""
        op_id = perf_monitor.start_operation("test_op")
        perf_monitor.complete_operation(op_id, success=True)

        summary = perf_monitor.get_summary()
        # get_summary returns summary stats, not keyed by operation name
        assert summary["total_operations"] == 1
        assert summary["operation_types"] == 1

    def test_timed_operation_decorator(self):
        """Test timed_operation decorator"""
        from agent_metrics.performance_monitor import timed_operation

        @timed_operation("test_decorated_op")
        def test_function():
            time.sleep(0.01)
            return "result"

        result = test_function()
        assert result == "result"


class TestLLMUsageTracker:
    """Test LLMUsageTracker class"""

    @pytest.fixture
    def llm_tracker(self):
        """Create LLMUsageTracker instance"""
        from agent_metrics.llm_usage_tracker import LLMUsageTracker
        return LLMUsageTracker()

    def test_tracker_initialization(self, llm_tracker):
        """Test LLMUsageTracker initializes correctly"""
        assert llm_tracker._calls == []
        assert llm_tracker._model_stats is not None

    def test_track_call(self, llm_tracker):
        """Test tracking an LLM call"""
        call = llm_tracker.track_call(
            model="gpt-4",
            provider="openai",
            input_tokens=100,
            output_tokens=50,
            duration=1.5,
        )

        assert call is not None
        assert call.model == "gpt-4"
        assert call.input_tokens == 100
        assert call.output_tokens == 50
        # Cost is calculated automatically from tokens
        assert call.cost > 0

    def test_track_call_with_error(self, llm_tracker):
        """Test tracking an LLM call with error"""
        call = llm_tracker.track_call(
            model="gpt-4",
            provider="openai",
            input_tokens=100,
            output_tokens=50,
            duration=1.5,
            success=False,
            error="Rate limit exceeded",
        )

        assert call.success is False
        assert call.error == "Rate limit exceeded"

    def test_get_usage_by_model(self, llm_tracker):
        """Test getting usage statistics by model"""
        llm_tracker.track_call("gpt-4", "openai", 100, 50, 1.0)
        llm_tracker.track_call("gpt-4", "openai", 200, 100, 2.0)

        usage = llm_tracker.get_usage_by_model()
        assert "gpt-4" in usage

    def test_get_total_usage(self, llm_tracker):
        """Test getting total usage"""
        llm_tracker.track_call("gpt-4", "openai", 100, 50, 1.0)
        llm_tracker.track_call("gpt-4", "openai", 200, 100, 2.0)

        total = llm_tracker.get_total_usage()
        assert total["total_calls"] == 2


class TestMemoryMonitor:
    """Test MemoryMonitor class"""

    @pytest.fixture
    def mem_monitor(self):
        """Create MemoryMonitor instance"""
        from agent_metrics.memory_monitor import MemoryMonitor
        return MemoryMonitor()

    def test_monitor_initialization(self, mem_monitor):
        """Test MemoryMonitor initializes correctly"""
        assert mem_monitor._snapshots == []
        assert mem_monitor._alerts == []

    def test_take_snapshot(self, mem_monitor):
        """Test taking a memory snapshot"""
        snapshot = mem_monitor.take_snapshot()

        assert snapshot is not None
        assert snapshot.timestamp > 0
        assert len(mem_monitor._snapshots) >= 1

    def test_get_current_usage(self, mem_monitor):
        """Test getting current memory usage"""
        mem_monitor.take_snapshot()

        usage = mem_monitor.get_current_usage()
        assert usage is not None


class TestMetricsDashboard:
    """Test MetricsDashboard class"""

    @pytest.fixture
    def dashboard(self):
        """Create MetricsDashboard instance"""
        from agent_metrics.dashboard import MetricsDashboard
        return MetricsDashboard()

    def test_dashboard_initialization(self, dashboard):
        """Test MetricsDashboard initializes correctly"""
        assert dashboard._start_time is not None

    def test_get_all_metrics(self, dashboard):
        """Test getting all metrics"""
        # Take some metrics first
        from agent_metrics.performance_monitor import performance_tracker
        from agent_metrics.memory_monitor import memory_monitor
        
        # Record a simple operation
        op_id = performance_tracker.start_operation("test_op")
        performance_tracker.complete_operation(op_id)
        
        # Take a memory snapshot
        memory_monitor.take_snapshot()

        data = dashboard.get_all_metrics()

        assert "performance" in data
        assert "memory" in data
        assert "timestamp" in data


class TestIntegration:
    """Integration tests for agent_metrics module"""

    def test_full_monitoring_workflow(self):
        """Test complete monitoring workflow"""
        from agent_metrics.performance_monitor import PerformanceMonitor
        from agent_metrics.llm_usage_tracker import LLMUsageTracker
        from agent_metrics.alerts import AlertManager, AlertSeverity
        from agent_metrics.memory_monitor import MemoryMonitor

        # Record operations
        pm = PerformanceMonitor()
        op_id = pm.start_operation("convert_block")
        pm.complete_operation(op_id, success=True)

        op_id2 = pm.start_operation("convert_item")
        pm.complete_operation(op_id2, success=True)

        # Record LLM usage (cost is auto-calculated from tokens)
        llm = LLMUsageTracker()
        llm.track_call("gpt-4", "openai", 100, 50, 1.0)

        # Record memory
        mem = MemoryMonitor()
        mem.take_snapshot()

        # Create alert
        am = AlertManager()
        am.create_alert("performance", AlertSeverity.INFO, "Operations completed")

        # Verify all tracked
        metrics = pm.get_metrics()
        assert "convert_block" in metrics or "convert_item" in metrics
        
        usage = llm.get_usage_by_model()
        assert "gpt-4" in usage
        
        alerts = am.get_alerts()
        assert len(alerts) == 1