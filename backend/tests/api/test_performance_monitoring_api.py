"""
Tests for Performance Monitoring API Endpoints
"""

import pytest
from datetime import datetime
from unittest.mock import Mock, AsyncMock, patch
from fastapi.testclient import TestClient
from fastapi import FastAPI

from src.api.performance_monitoring import router
from src.services.performance_monitor import performance_monitor
from src.services.adaptive_optimizer import adaptive_engine


@pytest.fixture
def app():
    """Create FastAPI app for testing"""
    app = FastAPI()
    app.include_router(router)
    return app


@pytest.fixture
def client(app):
    """Create test client"""
    return TestClient(app)


@pytest.fixture
async def mock_optimization_integrator():
    """Create a mock optimization integrator"""
    mock = AsyncMock()
    mock.initialized = True
    mock.service_integrations = {"cache_manager": Mock(), "batch_processor": Mock()}

    # Mock method return values
    mock.get_optimization_report.return_value = {
        "generated_at": datetime.now(),
        "performance_report": {"total_operations": 100},
        "adaptive_summary": {"total_adaptations": 50},
        "service_metrics": {"cache": {"hit_rate": 0.85}},
        "optimization_status": {
            "monitoring_active": True,
            "adaptive_engine_initialized": True,
            "services_integrated": 2,
        },
    }

    mock.manual_optimization_trigger.return_value = {
        "success": True,
        "optimization_type": "cache_optimization",
        "result": {"improvement": 15},
        "timestamp": datetime.now(),
    }

    return mock


@pytest.fixture
def setup_performance_monitor():
    """Setup performance monitor with test data"""
    # Add some test metrics
    from src.services.performance_monitor import PerformanceMetric

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
    performance_monitor.metrics_collector.record_metric(metric)

    # Add test thresholds
    from src.services.performance_monitor import PerformanceThreshold

    threshold = PerformanceThreshold(
        metric_name="test_metric",
        warning_threshold=50.0,
        critical_threshold=80.0,
        window_minutes=5,
        consecutive_violations=3,
    )
    performance_monitor.register_threshold(threshold)


class TestPerformanceStatusEndpoint:
    """Test /performance/status endpoint"""

    @patch("src.api.performance_monitoring.get_optimization_integrator")
    def test_get_performance_status_success(
        self, mock_get_integrator, client, mock_optimization_integrator
    ):
        """Test successful performance status retrieval"""
        mock_get_integrator.return_value = mock_optimization_integrator

        response = client.get("/api/v1/performance/status")

        assert response.status_code == 200
        data = response.json()
        assert data["status_code"] == 200
        assert "data" in data
        assert "monitoring_active" in data["data"]
        assert "current_system_metrics" in data["data"]

    @patch("src.api.performance_monitoring.get_optimization_integrator")
    def test_get_performance_status_uninitialized(self, mock_get_integrator, client):
        """Test performance status when integrator is not initialized"""
        mock_integrator = AsyncMock()
        mock_integrator.initialize.side_effect = Exception("Initialization failed")
        mock_get_integrator.return_value = mock_integrator

        response = client.get("/api/v1/performance/status")

        assert response.status_code == 503
        data = response.json()
        assert "Performance monitoring service unavailable" in data["detail"]


class TestPerformanceReportEndpoint:
    """Test /performance/report endpoint"""

    @patch("src.api.performance_monitoring.get_optimization_integrator")
    def test_get_performance_report_success(
        self, mock_get_integrator, client, mock_optimization_integrator
    ):
        """Test successful performance report generation"""
        mock_get_integrator.return_value = mock_optimization_integrator

        response = client.post(
            "/api/v1/performance/report",
            json={"operation_type": "conversion", "window_minutes": 60},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status_code"] == 200
        assert "performance_report" in data["data"]
        assert "adaptive_summary" in data["data"]
        assert "service_metrics" in data["data"]

    @patch("src.api.performance_monitoring.get_optimization_integrator")
    def test_get_performance_report_invalid_window(
        self, mock_get_integrator, client, mock_optimization_integrator
    ):
        """Test performance report with invalid window minutes"""
        mock_get_integrator.return_value = mock_optimization_integrator

        response = client.post(
            "/api/v1/performance/report",
            json={
                "window_minutes": 2000  # Exceeds max of 1440
            },
        )

        assert response.status_code == 422  # Validation error


class TestOperationMetricsEndpoint:
    """Test /performance/metrics/operation/{operation_type} endpoint"""

    @patch("src.api.performance_monitoring.get_optimization_integrator")
    def test_get_operation_metrics_success(
        self, mock_get_integrator, client, setup_performance_monitor
    ):
        """Test successful operation metrics retrieval"""
        mock_integrator = AsyncMock()
        mock_integrator.initialized = True
        mock_get_integrator.return_value = mock_integrator

        response = client.get(
            "/api/v1/performance/metrics/operation/test_operation?window_minutes=60"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status_code"] == 200
        assert "statistics" in data["data"]
        assert "trend_analysis" in data["data"]
        assert data["data"]["operation_type"] == "test_operation"

    @patch("src.api.performance_monitoring.get_optimization_integrator")
    def test_get_operation_metrics_nonexistent(self, mock_get_integrator, client):
        """Test getting metrics for nonexistent operation"""
        mock_integrator = AsyncMock()
        mock_integrator.initialized = True
        mock_get_integrator.return_value = mock_integrator

        response = client.get(
            "/api/v1/performance/metrics/operation/nonexistent_operation"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["data"]["statistics"] == {}


class TestSystemMetricsEndpoint:
    """Test /performance/metrics/system endpoint"""

    @patch("src.api.performance_monitoring.get_optimization_integrator")
    @patch("src.services.performance_monitor.psutil")
    def test_get_system_metrics_success(self, mock_psutil, mock_get_integrator, client):
        """Test successful system metrics retrieval"""
        mock_integrator = AsyncMock()
        mock_integrator.initialized = True
        mock_get_integrator.return_value = mock_integrator

        # Mock psutil
        mock_psutil.cpu_percent.return_value = 45.5
        mock_psutil.virtual_memory.return_value = Mock(percent=60.2, used=1073741824)
        mock_psutil.net_io_counters.return_value = Mock(
            bytes_sent=1000000, bytes_recv=2000000
        )
        mock_psutil.pids.return_value = [1, 2, 3, 4, 5]

        response = client.get("/api/v1/performance/metrics/system?samples=50")

        assert response.status_code == 200
        data = response.json()
        assert data["status_code"] == 200
        assert "current" in data["data"]
        assert "averages" in data["data"]
        assert "cpu_percent" in data["data"]["current"]
        assert "memory_percent" in data["data"]["current"]


class TestOptimizationTriggerEndpoint:
    """Test /performance/optimization/trigger endpoint"""

    @patch("src.api.performance_monitoring.get_optimization_integrator")
    def test_trigger_optimization_success(
        self, mock_get_integrator, client, mock_optimization_integrator
    ):
        """Test successful optimization trigger"""
        mock_get_integrator.return_value = mock_optimization_integrator

        response = client.post(
            "/api/v1/performance/optimization/trigger",
            json={"optimization_type": "cache_optimization"},
        )

        assert response.status_code == 202
        data = response.json()
        assert data["status_code"] == 202
        assert data["data"]["optimization_type"] == "cache_optimization"
        assert data["data"]["status"] == "started"

    @patch("src.api.performance_monitoring.get_optimization_integrator")
    def test_trigger_optimization_invalid_type(
        self, mock_get_integrator, client, mock_optimization_integrator
    ):
        """Test optimization trigger with invalid type"""
        mock_get_integrator.return_value = mock_optimization_integrator
        mock_optimization_integrator.manual_optimization_trigger.side_effect = (
            ValueError("Invalid optimization type")
        )

        response = client.post(
            "/api/v1/performance/optimization/trigger",
            json={"optimization_type": "invalid_type"},
        )

        assert response.status_code == 202  # Still returns 202 as it's backgrounded


class TestOptimizationOpportunitiesEndpoint:
    """Test /performance/optimization/opportunities endpoint"""

    @patch("src.api.performance_monitoring.get_optimization_integrator")
    def test_get_optimization_opportunities_success(self, mock_get_integrator, client):
        """Test successful optimization opportunities retrieval"""
        mock_integrator = AsyncMock()
        mock_integrator.initialized = True
        mock_get_integrator.return_value = mock_integrator

        # Mock optimization opportunities
        from src.services.performance_monitor import OptimizationAction

        mock_action = OptimizationAction(
            action_type="test_action",
            description="Test optimization",
            priority=5,
            condition="cpu_percent > 80",
            action_func=AsyncMock(),
            cooldown_minutes=10,
        )

        performance_monitor.optimizer.optimization_actions = [mock_action]
        performance_monitor.optimizer.evaluate_optimization_opportunities.return_value = [
            mock_action
        ]

        response = client.get("/api/v1/performance/optimization/opportunities")

        assert response.status_code == 200
        data = response.json()
        assert data["status_code"] == 200
        assert "opportunities" in data["data"]
        assert len(data["data"]["opportunities"]) >= 0


class TestAdaptiveSummaryEndpoint:
    """Test /performance/adaptive/summary endpoint"""

    @patch("src.api.performance_monitoring.get_optimization_integrator")
    def test_get_adaptive_summary_success(self, mock_get_integrator, client):
        """Test successful adaptive summary retrieval"""
        mock_integrator = AsyncMock()
        mock_integrator.initialized = True
        mock_get_integrator.return_value = mock_integrator

        # Mock adaptive engine summary
        adaptive_engine.pattern_learner.patterns = []
        adaptive_engine.pattern_learner.is_trained = True

        response = client.get("/api/v1/performance/adaptive/summary")

        assert response.status_code == 200
        data = response.json()
        assert data["status_code"] == 200
        assert "total_adaptations" in data["data"]
        assert "patterns_learned" in data["data"]
        assert "models_trained" in data["data"]


class TestOptimizationStrategyEndpoint:
    """Test /performance/adaptive/strategy endpoint"""

    @patch("src.api.performance_monitoring.get_optimization_integrator")
    def test_update_optimization_strategy_success(self, mock_get_integrator, client):
        """Test successful optimization strategy update"""
        mock_integrator = AsyncMock()
        mock_integrator.initialized = True
        mock_integrator.service_integrations = {}
        mock_get_integrator.return_value = mock_integrator

        response = client.put(
            "/api/v1/performance/adaptive/strategy", json={"strategy": "aggressive"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status_code"] == 200
        assert data["data"]["strategy"] == "aggressive"

    @patch("src.api.performance_monitoring.get_optimization_integrator")
    def test_update_optimization_strategy_invalid(self, mock_get_integrator, client):
        """Test optimization strategy update with invalid strategy"""
        mock_integrator = AsyncMock()
        mock_integrator.initialized = True
        mock_integrator.service_integrations = {}
        mock_get_integrator.return_value = mock_integrator

        response = client.put(
            "/api/v1/performance/adaptive/strategy",
            json={"strategy": "invalid_strategy"},
        )

        assert response.status_code == 400
        data = response.json()
        assert "Invalid strategy" in data["detail"]


class TestThresholdsEndpoints:
    """Test performance thresholds endpoints"""

    @patch("src.api.performance_monitoring.get_optimization_integrator")
    def test_get_performance_thresholds_success(
        self, mock_get_integrator, client, setup_performance_monitor
    ):
        """Test successful performance thresholds retrieval"""
        mock_integrator = AsyncMock()
        mock_integrator.initialized = True
        mock_get_integrator.return_value = mock_integrator

        response = client.get("/api/v1/performance/thresholds")

        assert response.status_code == 200
        data = response.json()
        assert data["status_code"] == 200
        assert "thresholds" in data["data"]
        assert len(data["data"]["thresholds"]) >= 1

    @patch("src.api.performance_monitoring.get_optimization_integrator")
    def test_create_performance_threshold_success(self, mock_get_integrator, client):
        """Test successful performance threshold creation"""
        mock_integrator = AsyncMock()
        mock_integrator.initialized = True
        mock_get_integrator.return_value = mock_integrator

        response = client.post(
            "/api/v1/performance/thresholds",
            json={
                "metric_name": "new_metric",
                "warning_threshold": 60.0,
                "critical_threshold": 90.0,
                "window_minutes": 5,
                "consecutive_violations": 3,
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["status_code"] == 201
        assert data["data"]["action"] == "created"
        assert data["data"]["metric_name"] == "new_metric"

    @patch("src.api.performance_monitoring.get_optimization_integrator")
    def test_delete_performance_threshold_success(
        self, mock_get_integrator, client, setup_performance_monitor
    ):
        """Test successful performance threshold deletion"""
        mock_integrator = AsyncMock()
        mock_integrator.initialized = True
        mock_get_integrator.return_value = mock_integrator

        response = client.delete("/api/v1/performance/thresholds/test_metric")

        assert response.status_code == 200
        data = response.json()
        assert data["status_code"] == 200
        assert "test_metric" in data["data"]["metric_name"]

    @patch("src.api.performance_monitoring.get_optimization_integrator")
    def test_delete_performance_threshold_not_found(self, mock_get_integrator, client):
        """Test deleting non-existent performance threshold"""
        mock_integrator = AsyncMock()
        mock_integrator.initialized = True
        mock_get_integrator.return_value = mock_integrator

        response = client.delete("/api/v1/performance/thresholds/nonexistent_metric")

        assert response.status_code == 404
        data = response.json()
        assert "Threshold not found" in data["detail"]


class TestAlertHistoryEndpoint:
    """Test /performance/alerts/history endpoint"""

    @patch("src.api.performance_monitoring.get_optimization_integrator")
    def test_get_alert_history_success(self, mock_get_integrator, client):
        """Test successful alert history retrieval"""
        mock_integrator = AsyncMock()
        mock_integrator.initialized = True
        mock_get_integrator.return_value = mock_integrator

        # Mock alert history
        alert_record = {
            "timestamp": datetime.now(),
            "action_type": "test_action",
            "success": True,
            "duration_ms": 150.0,
            "error": None,
        }
        performance_monitor.optimizer.action_history = [alert_record]

        response = client.get("/api/v1/performance/alerts/history?limit=10&hours=24")

        assert response.status_code == 200
        data = response.json()
        assert data["status_code"] == 200
        assert "alerts" in data["data"]
        assert "total_count" in data["data"]


class TestMonitoringControlEndpoints:
    """Test monitoring control endpoints"""

    @patch("src.api.performance_monitoring.get_optimization_integrator")
    async def test_start_monitoring_success(self, mock_get_integrator, client):
        """Test successful monitoring start"""
        mock_integrator = AsyncMock()
        mock_integrator.initialized = False
        mock_integrator.initialize = AsyncMock()
        mock_integrator.service_integrations = {"cache": Mock()}
        mock_get_integrator.return_value = mock_integrator

        response = client.post("/api/v1/performance/monitoring/start")

        assert response.status_code == 200
        data = response.json()
        assert data["status_code"] == 200
        assert "started_at" in data["data"]

    @patch("src.api.performance_monitoring.get_optimization_integrator")
    def test_start_monitoring_already_active(self, mock_get_integrator, client):
        """Test starting monitoring when already active"""
        mock_integrator = AsyncMock()
        mock_integrator.initialized = True

        # Mock that monitoring is already active
        with patch(
            "src.services.performance_monitor.performance_monitor.monitoring_active",
            True,
        ):
            mock_get_integrator.return_value = mock_integrator

            response = client.post("/api/v1/performance/monitoring/start")

            assert response.status_code == 200
            data = response.json()
            assert "already active" in data["message"]

    @patch("src.api.performance_monitoring.get_optimization_integrator")
    def test_stop_monitoring_success(self, mock_get_integrator, client):
        """Test successful monitoring stop"""
        mock_integrator = AsyncMock()
        mock_integrator.initialized = True
        mock_get_integrator.return_value = mock_integrator

        # Mock that monitoring is active
        with patch(
            "src.services.performance_monitor.performance_monitor.monitoring_active",
            True,
        ):
            response = client.post("/api/v1/performance/monitoring/stop")

            assert response.status_code == 200
            data = response.json()
            assert data["status_code"] == 200
            assert "stopped_at" in data["data"]

    @patch("src.api.performance_monitoring.get_optimization_integrator")
    def test_stop_monitoring_not_active(self, mock_get_integrator, client):
        """Test stopping monitoring when not active"""
        mock_integrator = AsyncMock()
        mock_integrator.initialized = True
        mock_get_integrator.return_value = mock_integrator

        # Mock that monitoring is not active
        with patch(
            "src.services.performance_monitor.performance_monitor.monitoring_active",
            False,
        ):
            response = client.post("/api/v1/performance/monitoring/stop")

            assert response.status_code == 200
            data = response.json()
            assert "not active" in data["message"]


class TestHealthCheckEndpoint:
    """Test /performance/health endpoint"""

    def test_health_check_healthy(self, client):
        """Test health check when service is healthy"""
        # Mock healthy state
        with patch(
            "src.services.performance_monitor.performance_monitor.monitoring_active",
            True,
        ):
            with patch(
                "src.services.adaptive_optimizer.adaptive_engine.pattern_learner.is_trained",
                True,
            ):
                response = client.get("/api/v1/performance/health")

                assert response.status_code == 200
                data = response.json()
                assert data["status_code"] == 200
                assert data["data"]["status"] == "healthy"

    def test_health_check_unhealthy(self, client):
        """Test health check when service is unhealthy"""
        # Mock unhealthy state with exception
        with patch(
            "src.services.performance_monitor.performance_monitor.monitoring_active",
            side_effect=Exception("Service error"),
        ):
            response = client.get("/api/v1/performance/health")

            assert response.status_code == 503
            data = response.json()
            assert data["status_code"] == 503
            assert data["data"]["status"] == "unhealthy"


class TestErrorHandling:
    """Test error handling in API endpoints"""

    @patch("src.api.performance_monitoring.get_optimization_integrator")
    def test_general_exception_handling(self, mock_get_integrator, client):
        """Test general exception handling in endpoints"""
        mock_integrator = AsyncMock()
        mock_integrator.get_optimization_report.side_effect = Exception(
            "Unexpected error"
        )
        mock_get_integrator.return_value = mock_integrator

        response = client.post("/api/v1/performance/report", json={})

        assert response.status_code == 500
        data = response.json()
        assert "Unexpected error" in data["detail"]


# Integration test class
@pytest.mark.integration
class TestPerformanceAPIIntegration:
    """Integration tests for performance monitoring API"""

    @patch("src.api.performance_monitoring.get_optimization_integrator")
    async def test_complete_performance_api_flow(self, mock_get_integrator, client):
        """Test complete API flow with mocked integrator"""
        # Setup mock integrator
        mock_integrator = AsyncMock()
        mock_integrator.initialized = True
        mock_integrator.service_integrations = {}
        mock_integrator.get_optimization_report.return_value = {
            "generated_at": datetime.now(),
            "performance_report": {"total_operations": 100},
            "adaptive_summary": {"total_adaptations": 50},
            "service_metrics": {},
            "optimization_status": {"monitoring_active": True},
        }
        mock_get_integrator.return_value = mock_integrator

        # Test status endpoint
        status_response = client.get("/api/v1/performance/status")
        assert status_response.status_code == 200

        # Test report generation
        report_response = client.post("/api/v1/performance/report", json={})
        assert report_response.status_code == 200

        # Test system metrics
        metrics_response = client.get("/api/v1/performance/metrics/system")
        assert metrics_response.status_code == 200

        # Test health check
        health_response = client.get("/api/v1/performance/health")
        assert health_response.status_code == 200

        # Verify the flow completed successfully
        assert True  # If we reach here, all endpoints responded correctly
