"""
Comprehensive tests for Performance Monitoring System
"""

import pytest
import asyncio
import time
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

from src.services.performance_monitor import (
    PerformanceMetric,
    PerformanceThreshold,
    MetricsCollector,
    AdaptiveOptimizer,
    OptimizationAction,
    PerformanceMonitor,
    performance_monitor,
    monitor_performance,
)


class TestPerformanceMetric:
    """Test PerformanceMetric dataclass"""

    def test_performance_metric_creation(self):
        """Test creating a PerformanceMetric"""
        timestamp = datetime.now()
        metric = PerformanceMetric(
            timestamp=timestamp,
            operation_type="test_operation",
            operation_id="test_123",
            duration_ms=100.5,
            cpu_percent=45.2,
            memory_mb=512.0,
            db_connections=5,
            cache_hit_rate=0.85,
            queue_length=3,
            error_count=0,
            metadata={"key": "value"},
        )

        assert metric.timestamp == timestamp
        assert metric.operation_type == "test_operation"
        assert metric.operation_id == "test_123"
        assert metric.duration_ms == 100.5
        assert metric.cpu_percent == 45.2
        assert metric.memory_mb == 512.0
        assert metric.db_connections == 5
        assert metric.cache_hit_rate == 0.85
        assert metric.queue_length == 3
        assert metric.error_count == 0
        assert metric.metadata == {"key": "value"}

    def test_performance_metric_defaults(self):
        """Test PerformanceMetric with default values"""
        timestamp = datetime.now()
        metric = PerformanceMetric(
            timestamp=timestamp,
            operation_type="test",
            operation_id="test_123",
            duration_ms=50.0,
            cpu_percent=30.0,
            memory_mb=256.0,
            db_connections=2,
            cache_hit_rate=0.9,
        )

        assert metric.queue_length == 0  # Default value
        assert metric.error_count == 0  # Default value
        assert metric.metadata == {}  # Default value


class TestMetricsCollector:
    """Test MetricsCollector class"""

    @pytest.fixture
    def metrics_collector(self):
        """Create a MetricsCollector instance for testing"""
        return MetricsCollector(max_samples=100)

    def test_metrics_collector_initialization(self, metrics_collector):
        """Test MetricsCollector initialization"""
        assert metrics_collector.maxlen == 100
        assert len(metrics_collector.metrics) == 0
        assert len(metrics_collector.operation_metrics) == 0
        assert len(metrics_collector.system_metrics) == 0

    def test_record_metric(self, metrics_collector):
        """Test recording a performance metric"""
        timestamp = datetime.now()
        metric = PerformanceMetric(
            timestamp=timestamp,
            operation_type="conversion",
            operation_id="conv_123",
            duration_ms=150.0,
            cpu_percent=60.0,
            memory_mb=1024.0,
            db_connections=8,
            cache_hit_rate=0.8,
        )

        metrics_collector.record_metric(metric)

        assert len(metrics_collector.metrics) == 1
        assert metrics_collector.metrics[0] == metric
        assert "conversion" in metrics_collector.operation_metrics
        assert len(metrics_collector.operation_metrics["conversion"]) == 1
        assert metrics_collector.operation_metrics["conversion"][0] == 150.0

    def test_record_multiple_metrics(self, metrics_collector):
        """Test recording multiple performance metrics"""
        metrics = [
            PerformanceMetric(
                timestamp=datetime.now(),
                operation_type="conversion",
                operation_id=f"conv_{i}",
                duration_ms=100.0 + i * 10,
                cpu_percent=50.0,
                memory_mb=512.0,
                db_connections=5,
                cache_hit_rate=0.8,
            )
            for i in range(5)
        ]

        for metric in metrics:
            metrics_collector.record_metric(metric)

        assert len(metrics_collector.metrics) == 5
        assert len(metrics_collector.operation_metrics["conversion"]) == 5
        assert metrics_collector.operation_metrics["conversion"] == [
            100.0,
            110.0,
            120.0,
            130.0,
            140.0,
        ]

    def test_operation_metrics_trimming(self, metrics_collector):
        """Test that operation metrics are trimmed when they exceed limits"""
        # Add more than 1000 metrics for one operation type
        for i in range(1100):
            metric = PerformanceMetric(
                timestamp=datetime.now(),
                operation_type="test_operation",
                operation_id=f"test_{i}",
                duration_ms=100.0 + i,
                cpu_percent=50.0,
                memory_mb=512.0,
                db_connections=5,
                cache_hit_rate=0.8,
            )
            metrics_collector.record_metric(metric)

        # Should keep only last 500 metrics
        assert len(metrics_collector.operation_metrics["test_operation"]) == 500
        # First metric should be from index 600 (1100 - 500)
        assert (
            metrics_collector.operation_metrics["test_operation"][0] == 700.0
        )  # 100 + 600

    @patch("src.services.performance_monitor.psutil")
    def test_collect_system_metrics(self, mock_psutil, metrics_collector):
        """Test collecting system metrics"""
        # Mock psutil functions
        mock_psutil.cpu_percent.return_value = 45.5
        mock_psutil.virtual_memory.return_value = Mock(
            percent=60.2,
            used=1073741824,  # 1GB in bytes
        )
        mock_psutil.disk_usage.return_value = Mock(percent=75.0)
        mock_psutil.net_io_counters.return_value = Mock(
            bytes_sent=1000000, bytes_recv=2000000
        )
        mock_psutil.pids.return_value = [1, 2, 3, 4, 5]

        metrics = metrics_collector.collect_system_metrics()

        assert metrics["cpu_percent"] == 45.5
        assert metrics["memory_percent"] == 60.2
        assert metrics["memory_mb"] == 1024.0  # 1GB in MB
        assert metrics["disk_usage"] == 75.0
        assert metrics["network_io"] == 3000000  # bytes_sent + bytes_recv
        assert metrics["process_count"] == 5
        assert "timestamp" in metrics

    def test_get_operation_stats_empty(self, metrics_collector):
        """Test getting operation stats when no metrics exist"""
        stats = metrics_collector.get_operation_stats("nonexistent_operation")

        assert stats == {}

    def test_get_operation_stats_with_data(self, metrics_collector):
        """Test getting operation stats with actual data"""
        # Add some test metrics
        base_time = datetime.now()
        durations = [100, 150, 200, 120, 180, 90, 160]

        for i, duration in enumerate(durations):
            metric = PerformanceMetric(
                timestamp=base_time + timedelta(seconds=i),
                operation_type="test_operation",
                operation_id=f"test_{i}",
                duration_ms=duration,
                cpu_percent=50.0,
                memory_mb=512.0,
                db_connections=5,
                cache_hit_rate=0.8,
            )
            metrics_collector.record_metric(metric)

        stats = metrics_collector.get_operation_stats("test_operation")

        assert stats["count"] == 7
        assert stats["avg_ms"] == sum(durations) / len(durations)
        assert stats["min_ms"] == min(durations)
        assert stats["max_ms"] == max(durations)
        assert "median_ms" in stats
        assert "p95_ms" in stats
        assert "p99_ms" in stats
        assert "std_dev" in stats

    def test_get_trend_analysis_insufficient_data(self, metrics_collector):
        """Test trend analysis with insufficient data"""
        # Add only 3 metrics (less than required 10)
        for i in range(3):
            metric = PerformanceMetric(
                timestamp=datetime.now() + timedelta(seconds=i),
                operation_type="test_operation",
                operation_id=f"test_{i}",
                duration_ms=100 + i * 10,
                cpu_percent=50.0,
                memory_mb=512.0,
                db_connections=5,
                cache_hit_rate=0.8,
            )
            metrics_collector.record_metric(metric)

        trend = metrics_collector.get_trend_analysis("test_operation")

        assert trend["trend"] == 0.0
        assert trend["confidence"] == 0.0

    def test_get_trend_analysis_sufficient_data(self, metrics_collector):
        """Test trend analysis with sufficient data"""
        # Add 15 metrics with increasing duration
        base_time = datetime.now()
        for i in range(15):
            metric = PerformanceMetric(
                timestamp=base_time + timedelta(minutes=i),
                operation_type="test_operation",
                operation_id=f"test_{i}",
                duration_ms=100 + i * 5,  # Increasing trend
                cpu_percent=50.0,
                memory_mb=512.0,
                db_connections=5,
                cache_hit_rate=0.8,
            )
            metrics_collector.record_metric(metric)

        trend = metrics_collector.get_trend_analysis("test_operation")

        assert trend["trend"] > 0  # Should detect increasing trend
        assert trend["confidence"] >= 0  # Confidence should be valid
        assert trend["samples"] == 15


class TestAdaptiveOptimizer:
    """Test AdaptiveOptimizer class"""

    @pytest.fixture
    def adaptive_optimizer(self):
        """Create an AdaptiveOptimizer instance for testing"""
        metrics_collector = MetricsCollector()
        return AdaptiveOptimizer(metrics_collector)

    def test_adaptive_optimizer_initialization(self, adaptive_optimizer):
        """Test AdaptiveOptimizer initialization"""
        assert adaptive_optimizer.metrics is not None
        assert len(adaptive_optimizer.optimization_actions) == 0
        assert len(adaptive_optimizer.action_history) == 0
        assert len(adaptive_optimizer.learning_rates) == 0

    def test_register_optimization_action(self, adaptive_optimizer):
        """Test registering an optimization action"""

        async def test_action():
            return {"success": True, "improvement": 15}

        action = OptimizationAction(
            action_type="test_action",
            description="Test optimization action",
            priority=5,
            condition="cpu_percent > 80",
            action_func=test_action,
            cooldown_minutes=10,
        )

        adaptive_optimizer.register_optimization_action(action)

        assert len(adaptive_optimizer.optimization_actions) == 1
        assert adaptive_optimizer.optimization_actions[0] == action

    @pytest.mark.asyncio
    async def test_execute_optimization_success(self, adaptive_optimizer):
        """Test executing a successful optimization action"""

        async def test_action():
            await asyncio.sleep(0.01)  # Simulate some work
            return {"improvement": 20, "resource_saved": "10%"}

        action = OptimizationAction(
            action_type="test_action",
            description="Test optimization action",
            priority=5,
            condition="cpu_percent > 80",
            action_func=test_action,
            cooldown_minutes=10,
        )

        result = await adaptive_optimizer.execute_optimization(action)

        assert result["action_type"] == "test_action"
        assert result["success"] is True
        assert result["result"]["improvement"] == 20
        assert "duration_ms" in result
        assert len(adaptive_optimizer.action_history) == 1

    @pytest.mark.asyncio
    async def test_execute_optimization_failure(self, adaptive_optimizer):
        """Test executing a failed optimization action"""

        async def failing_action():
            raise ValueError("Test error")

        action = OptimizationAction(
            action_type="failing_action",
            description="Failing optimization action",
            priority=5,
            condition="cpu_percent > 80",
            action_func=failing_action,
            cooldown_minutes=10,
        )

        result = await adaptive_optimizer.execute_optimization(action)

        assert result["action_type"] == "failing_action"
        assert result["success"] is False
        assert "Test error" in result["error"]
        assert len(adaptive_optimizer.action_history) == 1

    def test_update_learning_success(self, adaptive_optimizer):
        """Test learning rate update on success"""
        initial_rate = adaptive_optimizer.learning_rates.get("test_action", 0.01)
        adaptive_optimizer._update_learning("test_action", True, {"improvement": 15})

        new_rate = adaptive_optimizer.learning_rates["test_action"]
        assert new_rate > initial_rate  # Should increase on success

    def test_update_learning_failure(self, adaptive_optimizer):
        """Test learning rate update on failure"""
        initial_rate = adaptive_optimizer.learning_rates.get("test_action", 0.01)
        adaptive_optimizer._update_learning("test_action", False, None)

        new_rate = adaptive_optimizer.learning_rates["test_action"]
        assert new_rate < initial_rate  # Should decrease on failure

    def test_learning_rate_bounds(self, adaptive_optimizer):
        """Test that learning rates stay within bounds"""
        # Test upper bound
        adaptive_optimizer.learning_rates["test_action"] = 0.09
        adaptive_optimizer._update_learning("test_action", True, {"improvement": 20})
        assert adaptive_optimizer.learning_rates["test_action"] <= 0.1

        # Test lower bound
        adaptive_optimizer.learning_rates["test_action"] = 0.002
        adaptive_optimizer._update_learning("test_action", False, None)
        assert adaptive_optimizer.learning_rates["test_action"] >= 0.001


class TestPerformanceMonitor:
    """Test PerformanceMonitor class"""

    @pytest.fixture
    def performance_monitor_instance(self):
        """Create a PerformanceMonitor instance for testing"""
        return PerformanceMonitor(
            enable_prometheus=False
        )  # Disable Prometheus for testing

    def test_performance_monitor_initialization(self, performance_monitor_instance):
        """Test PerformanceMonitor initialization"""
        assert performance_monitor_instance.metrics_collector is not None
        assert performance_monitor_instance.optimizer is not None
        assert performance_monitor_instance.monitoring_active is False
        assert len(performance_monitor_instance.thresholds) == 0

    def test_register_threshold(self, performance_monitor_instance):
        """Test registering a performance threshold"""
        threshold = PerformanceThreshold(
            metric_name="test_metric",
            warning_threshold=50.0,
            critical_threshold=80.0,
            window_minutes=5,
            consecutive_violations=3,
        )

        performance_monitor_instance.register_threshold(threshold)

        assert len(performance_monitor_instance.thresholds) == 1
        assert performance_monitor_instance.thresholds[0] == threshold

    def test_register_alert_callback(self, performance_monitor_instance):
        """Test registering an alert callback"""
        callback_called = False

        async def test_callback(alert_data):
            nonlocal callback_called
            callback_called = True

        performance_monitor_instance.register_alert_callback(test_callback)

        assert len(performance_monitor_instance.alert_callbacks) == 1
        assert performance_monitor_instance.alert_callbacks[0] == test_callback

    @pytest.mark.asyncio
    async def test_monitor_operation_success(self, performance_monitor_instance):
        """Test monitoring a successful operation"""
        operation_id = None

        async with performance_monitor_instance.monitor_operation(
            "test_operation", "test_123"
        ) as op_id:
            operation_id = op_id
            await asyncio.sleep(0.01)  # Simulate some work

        assert operation_id == "test_123"
        assert len(performance_monitor_instance.metrics_collector.metrics) == 1

        metric = performance_monitor_instance.metrics_collector.metrics[0]
        assert metric.operation_type == "test_operation"
        assert metric.operation_id == "test_123"
        assert metric.duration_ms > 0
        assert metric.error_count == 0

    @pytest.mark.asyncio
    async def test_monitor_operation_failure(self, performance_monitor_instance):
        """Test monitoring a failed operation"""
        with pytest.raises(ValueError, match="Test error"):
            async with performance_monitor_instance.monitor_operation(
                "test_operation", "test_456"
            ):
                raise ValueError("Test error")

        assert len(performance_monitor_instance.metrics_collector.metrics) == 1

        metric = performance_monitor_instance.metrics_collector.metrics[0]
        assert metric.operation_type == "test_operation"
        assert metric.operation_id == "test_456"
        assert metric.error_count == 1
        assert "Test error" in metric.metadata["error"]

    def test_get_performance_report(self, performance_monitor_instance):
        """Test generating performance report"""
        # Add some test metrics
        metric = PerformanceMetric(
            timestamp=datetime.now(),
            operation_type="test_operation",
            operation_id="test_123",
            duration_ms=150.0,
            cpu_percent=60.0,
            memory_mb=1024.0,
            db_connections=8,
            cache_hit_rate=0.8,
        )
        performance_monitor_instance.metrics_collector.record_metric(metric)

        report = performance_monitor_instance.get_performance_report()

        assert "generated_at" in report
        assert "window_minutes" in report
        assert report["total_operations"] == 1
        assert "test_operation" in report["operation_stats"]
        assert "optimization_history" in report
        assert "system_metrics" in report

    def test_get_performance_report_filtered(self, performance_monitor_instance):
        """Test generating performance report with operation type filter"""
        # Add test metrics for different operations
        for op_type in ["conversion", "cache_access"]:
            metric = PerformanceMetric(
                timestamp=datetime.now(),
                operation_type=op_type,
                operation_id=f"{op_type}_123",
                duration_ms=150.0,
                cpu_percent=60.0,
                memory_mb=1024.0,
                db_connections=8,
                cache_hit_rate=0.8,
            )
            performance_monitor_instance.metrics_collector.record_metric(metric)

        report = performance_monitor_instance.get_performance_report(
            operation_type="conversion"
        )

        assert report["operation_stats"].get("conversion") is not None
        assert report["operation_stats"].get("cache_access") is None


class TestMonitorPerformanceDecorator:
    """Test monitor_performance decorator"""

    @pytest.mark.asyncio
    async def test_monitor_performance_decorator_async(self):
        """Test monitor_performance decorator with async function"""

        @monitor_performance("decorated_operation")
        async def test_async_function(x, y):
            await asyncio.sleep(0.01)
            return x + y

        result = await test_async_function(5, 3)

        assert result == 8
        # Check that a metric was recorded (this would need to access the global performance_monitor)
        # For now, just verify the function works correctly

    def test_monitor_performance_decorator_sync(self):
        """Test monitor_performance decorator with sync function"""

        @monitor_performance("sync_operation")
        def test_sync_function(x, y):
            time.sleep(0.01)
            return x * y

        result = test_sync_function(4, 6)

        assert result == 24
        # Check that a metric was recorded


class TestGlobalPerformanceMonitor:
    """Test global performance_monitor instance"""

    def test_global_performance_monitor_exists(self):
        """Test that global performance_monitor instance exists"""
        assert performance_monitor is not None
        assert isinstance(performance_monitor, PerformanceMonitor)


@pytest.mark.asyncio
class TestPerformanceMonitorIntegration:
    """Integration tests for performance monitoring system"""

    async def test_end_to_end_monitoring_flow(self):
        """Test complete monitoring flow"""
        # Create a performance monitor
        monitor = PerformanceMonitor(enable_prometheus=False)

        # Register a threshold
        threshold = PerformanceThreshold(
            metric_name="test_operation",
            warning_threshold=100.0,
            critical_threshold=200.0,
        )
        monitor.register_threshold(threshold)

        # Monitor an operation
        async with monitor.monitor_operation("test_operation", "integration_test"):
            await asyncio.sleep(0.01)

        # Verify metric was recorded
        assert len(monitor.metrics_collector.metrics) == 1

        metric = monitor.metrics_collector.metrics[0]
        assert metric.operation_type == "test_operation"
        assert metric.operation_id == "integration_test"
        assert metric.duration_ms > 0

        # Get performance report
        report = monitor.get_performance_report()
        assert report["total_operations"] == 1
        assert "test_operation" in report["operation_stats"]
