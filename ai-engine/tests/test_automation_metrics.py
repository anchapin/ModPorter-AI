"""
Unit tests for Automation Analytics modules
"""

import asyncio
import pytest
from datetime import datetime, timedelta
import sys

sys.path.insert(0, '/home/alex/Projects/ModPorter-AI/ai-engine')

from agent_metrics.automation_metrics import AutomationMetrics
from agent_metrics.bottleneck_detector import BottleneckDetector
from agent_metrics.trend_analyzer import TrendAnalyzer
from agent_metrics.automation_dashboard import AutomationDashboard


class TestAutomationMetrics:
    """Tests for AutomationMetrics class."""
    
    @pytest.fixture
    def metrics(self):
        """Create a fresh metrics instance."""
        return AutomationMetrics()
    
    @pytest.mark.asyncio
    async def test_record_successful_conversion(self, metrics):
        """Test recording a successful conversion."""
        await metrics.record_conversion(
            success=True,
            mode="Simple",
            processing_time=10.5,
        )
        
        assert metrics.get_success_rate() == 1.0
        assert metrics._metrics["total_conversions"] == 1
        assert metrics._metrics["successful_conversions"] == 1
    
    @pytest.mark.asyncio
    async def test_record_failed_conversion(self, metrics):
        """Test recording a failed conversion."""
        await metrics.record_conversion(
            success=False,
            mode="Complex",
            processing_time=45.0,
            error_type="ParseError",
        )
        
        assert metrics.get_success_rate() == 0.0
        assert metrics._metrics["failed_conversions"] == 1
        assert metrics._metrics["manual_intervention"] == 1
    
    @pytest.mark.asyncio
    async def test_record_auto_recovered(self, metrics):
        """Test recording an auto-recovered conversion."""
        await metrics.record_conversion(
            success=False,
            mode="Complex",
            processing_time=50.0,
            error_type="TranslationError",
            auto_recovered=True,
        )
        
        assert metrics.get_auto_recovery_rate() == 1.0
        assert metrics._metrics["auto_recovered"] == 1
        assert metrics._metrics["manual_intervention"] == 0
    
    @pytest.mark.asyncio
    async def test_mode_success_rates(self, metrics):
        """Test calculating success rates per mode."""
        await metrics.record_conversion(True, "Simple", 10.0)
        await metrics.record_conversion(True, "Simple", 12.0)
        await metrics.record_conversion(False, "Complex", 45.0)
        await metrics.record_conversion(False, "Complex", 50.0)
        
        rates = metrics.get_mode_success_rates()
        
        assert rates["Simple"] == 1.0
        assert rates["Complex"] == 0.0
    
    @pytest.mark.asyncio
    async def test_processing_time(self, metrics):
        """Test average processing time calculation."""
        await metrics.record_conversion(True, "Simple", 10.0)
        await metrics.record_conversion(True, "Simple", 20.0)
        await metrics.record_conversion(True, "Simple", 30.0)
        
        assert metrics.get_avg_processing_time() == 20.0
    
    @pytest.mark.asyncio
    async def test_top_error_types(self, metrics):
        """Test getting top error types."""
        await metrics.record_conversion(False, "Complex", 45.0, "ParseError")
        await metrics.record_conversion(False, "Complex", 46.0, "ParseError")
        await metrics.record_conversion(False, "Complex", 47.0, "TranslationError")
        
        top_errors = metrics.get_top_error_types()
        
        assert top_errors[0]["type"] == "ParseError"
        assert top_errors[0]["count"] == 2
    
    @pytest.mark.asyncio
    async def test_retry_tracking(self, metrics):
        """Test retry success rate tracking."""
        await metrics.record_retry(True)
        await metrics.record_retry(True)
        await metrics.record_retry(False)
        
        assert metrics.get_retry_success_rate() == pytest.approx(2/3, rel=0.01)


class TestBottleneckDetector:
    """Tests for BottleneckDetector class."""
    
    @pytest.fixture
    def detector(self):
        """Create a fresh detector instance."""
        return BottleneckDetector()
    
    @pytest.mark.asyncio
    async def test_record_stage_time(self, detector):
        """Test recording stage time."""
        await detector.record_stage_time("conv-1", "parsing", 2.5)
        await detector.record_stage_time("conv-1", "translation", 25.0)
        
        stats = detector.get_stage_statistics()
        
        assert "parsing" in stats
        assert stats["parsing"]["avg"] == 2.5
        assert stats["translation"]["avg"] == 25.0
    
    @pytest.mark.asyncio
    async def test_bottleneck_detection(self, detector):
        """Test bottleneck detection."""
        # Record times above threshold
        for _ in range(10):
            await detector.record_stage_time("conv-1", "parsing", 8.0)
        
        bottlenecks = detector.get_bottlenecks()
        
        assert len(bottlenecks) > 0
        assert any(b["stage"] == "parsing" for b in bottlenecks)
    
    @pytest.mark.asyncio
    async def test_percentiles(self, detector):
        """Test percentile calculation."""
        for i in range(100):
            await detector.record_stage_time(f"conv-{i}", "translation", float(i))
        
        percentiles = detector.get_stage_percentiles("translation")
        
        assert "p50" in percentiles
        assert "p95" in percentiles
        assert percentiles["p50"] == 50.0
    
    def test_total_pipeline_time(self, detector):
        """Test total pipeline time calculation."""
        # Add some mock data
        detector._stage_times["parsing"] = [2.0, 3.0, 4.0]  # avg = 3.0
        detector._stage_times["translation"] = [20.0, 25.0, 30.0]  # avg = 25.0
        
        total = detector.get_total_pipeline_time()
        
        # Total = avg(parsing) + avg(translation) = 3.0 + 25.0 = 28.0
        assert total == 28.0


class TestTrendAnalyzer:
    """Tests for TrendAnalyzer class."""
    
    @pytest.fixture
    def analyzer(self):
        """Create a fresh analyzer instance."""
        return TrendAnalyzer(retention_days=7)
    
    @pytest.mark.asyncio
    async def test_record_snapshot(self, analyzer):
        """Test recording a metrics snapshot."""
        await analyzer.record_snapshot({
            "success_rate": 0.85,
            "avg_processing_time": 25.0,
        })
        
        summary = analyzer.get_summary()
        
        assert summary["data_points"] == 1
    
    @pytest.mark.asyncio
    async def test_metric_trend(self, analyzer):
        """Test getting metric trend."""
        # Record multiple snapshots
        for i in range(10):
            await analyzer.record_metric("success_rate", 0.7 + i * 0.02)
        
        trend = analyzer.get_metric_trend("success_rate", "1h")
        
        assert len(trend) == 10
    
    @pytest.mark.asyncio
    async def test_anomaly_detection(self, analyzer):
        """Test anomaly detection."""
        # Record normal values
        for _ in range(20):
            await analyzer.record_metric("success_rate", 0.85)
        
        # Record outliers
        await analyzer.record_metric("success_rate", 0.2)
        await analyzer.record_metric("success_rate", 0.15)
        
        anomalies = analyzer.detect_anomalies("success_rate", threshold=2.0)
        
        assert len(anomalies) >= 2
    
    @pytest.mark.asyncio
    async def test_calculate_trend(self, analyzer):
        """Test trend calculation."""
        # Record improving trend
        for i in range(10):
            await analyzer.record_metric("success_rate", 0.5 + i * 0.03)
        
        trend = analyzer.calculate_trend("success_rate", "1h")
        
        assert trend > 0  # Should be improving
    
    def test_improvement_recommendations(self, analyzer):
        """Test recommendation generation."""
        # Add mock data
        analyzer._historical_data = [
            {"timestamp": datetime.now() - timedelta(hours=i), "metrics": {"success_rate": 0.7}}
            for i in range(20)
        ]
        
        recommendations = analyzer.get_improvement_recommendations()
        
        assert isinstance(recommendations, list)


class TestAutomationDashboard:
    """Tests for AutomationDashboard class."""
    
    @pytest.fixture
    def dashboard(self):
        """Create a fresh dashboard instance."""
        return AutomationDashboard()
    
    @pytest.mark.asyncio
    async def test_start_end_conversion(self, dashboard):
        """Test conversion lifecycle."""
        await dashboard.start_conversion("conv-1")
        await dashboard.end_conversion(
            conversion_id="conv-1",
            success=True,
            mode="Simple",
            processing_time=15.0,
        )
        
        overview = dashboard.get_dashboard_data()["overview"]
        
        assert overview["total_conversions"] == 1
        assert overview["success_rate"] == 1.0
    
    @pytest.mark.asyncio
    async def test_active_conversions(self, dashboard):
        """Test active conversions tracking."""
        await dashboard.start_conversion("conv-1")
        await dashboard.start_conversion("conv-2")
        
        realtime = dashboard.get_realtime_update()
        
        assert realtime["active_conversions"] == 2
    
    def test_dashboard_data(self, dashboard):
        """Test getting full dashboard data."""
        data = dashboard.get_dashboard_data()
        
        assert "overview" in data
        assert "by_mode" in data
        assert "bottlenecks" in data
        assert "alerts" in data
    
    def test_realtime_update(self, dashboard):
        """Test lightweight realtime update."""
        realtime = dashboard.get_realtime_update()
        
        assert "success_rate" in realtime
        assert "active_conversions" in realtime
        assert "timestamp" in realtime
    
    def test_health_status(self, dashboard):
        """Test health status."""
        health = dashboard.get_health_status()
        
        assert "status" in health
        assert "alerts" in health
    
    def test_export_json(self, dashboard):
        """Test JSON export."""
        json_data = dashboard.export_json()
        
        assert json_data.startswith("{")
        assert json_data.endswith("}")
    
    def test_export_csv(self, dashboard):
        """Test CSV export."""
        csv_data = dashboard.export_csv()
        
        assert "metric,value" in csv_data
    
    @pytest.mark.asyncio
    async def test_alerts(self, dashboard):
        """Test alert generation."""
        # Record some failed conversions to trigger alerts
        for _ in range(5):
            await dashboard.end_conversion(
                conversion_id=f"conv-{_}",
                success=False,
                mode="Complex",
                processing_time=150.0,  # High to trigger time alert
                error_type="ParseError",
            )
        
        alerts = dashboard._get_active_alerts()
        
        # Should have warnings for low success rate and high processing time
        assert len(alerts) > 0


# Performance tests
class TestPerformance:
    """Performance tests to verify <1 second query time."""
    
    @pytest.mark.asyncio
    async def test_query_response_time(self):
        """Test that dashboard query responds in <1 second."""
        import time
        
        dashboard = AutomationDashboard()
        
        # Add some test data
        for i in range(100):
            await dashboard.end_conversion(
                conversion_id=f"conv-{i}",
                success=i % 10 != 0,  # 90% success rate
                mode=["Simple", "Standard", "Complex"][i % 3],
                processing_time=10.0 + i % 20,
            )
        
        # Time the query
        start = time.time()
        data = dashboard.get_dashboard_data()
        elapsed = time.time() - start
        
        assert elapsed < 1.0, f"Query took {elapsed:.3f}s, should be <1s"
    
    @pytest.mark.asyncio
    async def test_realtime_update_performance(self):
        """Test realtime update responds in <100ms."""
        import time
        
        dashboard = AutomationDashboard()
        
        start = time.time()
        realtime = dashboard.get_realtime_update()
        elapsed = time.time() - start
        
        assert elapsed < 0.1, f"Realtime update took {elapsed:.3f}s, should be <0.1s"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
