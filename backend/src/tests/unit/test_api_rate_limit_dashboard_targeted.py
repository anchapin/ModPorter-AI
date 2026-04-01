"""
Unit tests for Rate Limit Dashboard API.

Issue: #643 - Backend: Implement Rate Limiting Dashboard
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient
from fastapi import FastAPI
from datetime import datetime, timezone

from api.rate_limit_dashboard import (
    router,
    RateLimitSummary,
    EndpointStats,
    ClientStats,
    DashboardStats,
    ConfigInfo,
    ConfigUpdateRequest,
)


app = FastAPI()
app.include_router(router)
client = TestClient(app)


class TestDashboardEndpoint:
    """Tests for dashboard endpoint."""

    @patch("api.rate_limit_dashboard._get_prometheus_metrics")
    @patch("api.rate_limit_dashboard.rate_limit_active_clients")
    def test_get_dashboard_with_data(self, mock_active_clients, mock_get_metrics):
        """Test dashboard with existing metrics."""
        mock_get_metrics.return_value = {
            "total_/api/test": 100.0,
            "allowed_/api/test": 80.0,
            "blocked_/api/test": 20.0,
        }
        mock_active_clients._value.get.return_value = 5

        response = client.get("/dashboard")
        assert response.status_code == 200
        data = response.json()

        assert "summary" in data
        assert data["summary"]["total_requests"] == 100
        assert data["summary"]["allowed_requests"] == 80
        assert data["summary"]["blocked_requests"] == 20
        assert data["summary"]["block_rate"] == 20.0
        assert data["summary"]["active_clients"] == 5
        assert "/api/test" in data["summary"]["unique_endpoints"]

    @patch("api.rate_limit_dashboard._get_prometheus_metrics")
    def test_get_dashboard_empty_metrics(self, mock_get_metrics):
        """Test dashboard with no metrics."""
        mock_get_metrics.return_value = {}

        response = client.get("/dashboard")
        assert response.status_code == 200
        data = response.json()

        assert data["summary"]["total_requests"] == 0
        assert data["summary"]["allowed_requests"] == 0
        assert data["summary"]["blocked_requests"] == 0
        assert data["summary"]["block_rate"] == 0.0

    @patch("api.rate_limit_dashboard._get_prometheus_metrics")
    @patch("api.rate_limit_dashboard.rate_limit_active_clients")
    def test_dashboard_endpoint_stats(self, mock_active_clients, mock_get_metrics):
        """Test dashboard includes endpoint stats."""
        mock_get_metrics.return_value = {
            "total_/api/a": 100.0,
            "allowed_/api/a": 80.0,
            "blocked_/api/a": 20.0,
            "total_/api/b": 50.0,
            "allowed_/api/b": 45.0,
            "blocked_/api/b": 5.0,
        }
        mock_active_clients._value.get.return_value = 3

        response = client.get("/dashboard")
        assert response.status_code == 200
        data = response.json()

        assert "endpoint_stats" in data
        assert len(data["endpoint_stats"]) == 2

    @patch("api.rate_limit_dashboard._get_prometheus_metrics")
    @patch("api.rate_limit_dashboard.rate_limit_active_clients")
    def test_dashboard_top_blocked(self, mock_active_clients, mock_get_metrics):
        """Test dashboard includes top blocked endpoints."""
        mock_get_metrics.return_value = {
            "total_/api/a": 100.0,
            "allowed_/api/a": 50.0,
            "blocked_/api/a": 50.0,
            "total_/api/b": 50.0,
            "allowed_/api/b": 45.0,
            "blocked_/api/b": 5.0,
        }
        mock_active_clients._value.get.return_value = 1

        response = client.get("/dashboard")
        assert response.status_code == 200
        data = response.json()

        assert "top_blocked_endpoints" in data
        assert len(data["top_blocked_endpoints"]) <= 5

    @patch("api.rate_limit_dashboard._get_prometheus_metrics")
    def test_dashboard_recent_activity(self, mock_get_metrics):
        """Test dashboard includes recent activity."""
        mock_get_metrics.return_value = {
            "total_/api/test": 100.0,
            "allowed_/api/test": 80.0,
            "blocked_/api/test": 20.0,
        }

        response = client.get("/dashboard")
        assert response.status_code == 200
        data = response.json()

        assert "recent_activity" in data
        assert "last_minute" in data["recent_activity"]
        assert "last_hour" in data["recent_activity"]
        assert "last_day" in data["recent_activity"]


class TestSummaryEndpoint:
    """Tests for summary endpoint."""

    @patch("api.rate_limit_dashboard._get_prometheus_metrics")
    @patch("api.rate_limit_dashboard.rate_limit_active_clients")
    def test_get_summary_with_data(self, mock_active_clients, mock_get_metrics):
        """Test summary with metrics."""
        mock_get_metrics.return_value = {
            "total_/api/test": 200.0,
            "allowed_/api/test": 150.0,
            "blocked_/api/test": 50.0,
        }
        mock_active_clients._value.get.return_value = 10

        response = client.get("/summary")
        assert response.status_code == 200
        data = response.json()

        assert data["total_requests"] == 200
        assert data["allowed_requests"] == 150
        assert data["blocked_requests"] == 50
        assert data["block_rate"] == 25.0
        assert data["active_clients"] == 10

    @patch("api.rate_limit_dashboard._get_prometheus_metrics")
    def test_get_summary_empty(self, mock_get_metrics):
        """Test summary with no metrics."""
        mock_get_metrics.return_value = {}

        response = client.get("/summary")
        assert response.status_code == 200
        data = response.json()

        assert data["total_requests"] == 0
        assert data["block_rate"] == 0.0
        assert data["active_clients"] == 0

    @patch("api.rate_limit_dashboard._get_prometheus_metrics")
    def test_get_summary_ignores_unknown(self, mock_get_metrics):
        """Test summary ignores unknown endpoints."""
        mock_get_metrics.return_value = {
            "total_unknown": 100.0,
            "allowed_unknown": 80.0,
            "blocked_unknown": 20.0,
            "total_/api/test": 50.0,
        }

        response = client.get("/summary")
        assert response.status_code == 200
        data = response.json()

        assert data["total_requests"] == 50


class TestEndpointsStatsEndpoint:
    """Tests for endpoints stats endpoint."""

    @patch("api.rate_limit_dashboard._get_prometheus_metrics")
    def test_get_endpoint_stats(self, mock_get_metrics):
        """Test getting endpoint stats."""
        mock_get_metrics.return_value = {
            "total_/api/a": 100.0,
            "allowed_/api/a": 80.0,
            "blocked_/api/a": 20.0,
            "total_/api/b": 50.0,
            "allowed_/api/b": 40.0,
            "blocked_/api/b": 10.0,
        }

        response = client.get("/endpoints")
        assert response.status_code == 200
        data = response.json()

        assert len(data) == 2
        data_sorted = sorted(data, key=lambda x: x["endpoint"])
        assert data_sorted[0]["endpoint"] == "/api/a"
        assert data_sorted[0]["total_requests"] == 100

    @patch("api.rate_limit_dashboard._get_prometheus_metrics")
    def test_get_endpoint_stats_sorted(self, mock_get_metrics):
        """Test endpoint stats are sorted by total requests."""
        mock_get_metrics.return_value = {
            "total_/api/a": 50.0,
            "total_/api/b": 200.0,
            "total_/api/c": 100.0,
            "allowed_/api/a": 50.0,
            "allowed_/api/b": 180.0,
            "allowed_/api/c": 90.0,
            "blocked_/api/a": 0.0,
            "blocked_/api/b": 20.0,
            "blocked_/api/c": 10.0,
        }

        response = client.get("/endpoints")
        assert response.status_code == 200
        data = response.json()

        assert data[0]["endpoint"] == "/api/b"
        assert data[0]["total_requests"] == 200
        assert data[1]["endpoint"] == "/api/c"
        assert data[2]["endpoint"] == "/api/a"

    @patch("api.rate_limit_dashboard._get_prometheus_metrics")
    def test_get_endpoint_stats_empty(self, mock_get_metrics):
        """Test getting endpoint stats with no data."""
        mock_get_metrics.return_value = {}

        response = client.get("/endpoints")
        assert response.status_code == 200
        data = response.json()
        assert data == []


class TestClientStatsEndpoint:
    """Tests for client stats endpoint."""

    @patch("api.rate_limit_dashboard.get_rate_limiter", new_callable=AsyncMock)
    def test_get_client_stats_no_redis(self, mock_get_limiter):
        """Test getting client stats without Redis."""
        mock_limiter = MagicMock()
        mock_limiter._use_redis = False
        mock_limiter._local_state = {}
        mock_limiter.config = MagicMock()
        mock_limiter.config.requests_per_minute = 60
        mock_limiter.config.requests_per_hour = 1000
        mock_get_limiter.return_value = mock_limiter

        response = client.get("/clients")
        assert response.status_code == 200
        data = response.json()
        assert data == []

    @patch("api.rate_limit_dashboard.get_rate_limiter", new_callable=AsyncMock)
    def test_get_client_stats_with_users(self, mock_get_limiter):
        """Test getting client stats with user clients."""
        mock_state = MagicMock()
        mock_state.request_count = 15

        mock_limiter = MagicMock()
        mock_limiter._use_redis = False
        mock_limiter._local_state = {"user:user123": mock_state}
        mock_limiter.config = MagicMock()
        mock_limiter.config.requests_per_minute = 60
        mock_limiter.config.requests_per_hour = 1000
        mock_get_limiter.return_value = mock_limiter

        response = client.get("/clients")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["client_type"] == "user"
        assert data[0]["requests_in_minute"] == 15
        assert data[0]["limit_minute"] == 60

    @patch("api.rate_limit_dashboard.get_rate_limiter", new_callable=AsyncMock)
    def test_get_client_stats_with_ips(self, mock_get_limiter):
        """Test getting client stats with IP clients."""
        mock_state = MagicMock()
        mock_state.request_count = 25

        mock_limiter = MagicMock()
        mock_limiter._use_redis = False
        mock_limiter._local_state = {"ip:192.168.1.1": mock_state}
        mock_limiter.config = MagicMock()
        mock_limiter.config.requests_per_minute = 60
        mock_limiter.config.requests_per_hour = 1000
        mock_get_limiter.return_value = mock_limiter

        response = client.get("/clients")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["client_type"] == "ip"

    @patch("api.rate_limit_dashboard.get_rate_limiter", new_callable=AsyncMock)
    def test_get_client_stats_limit(self, mock_get_limiter):
        """Test client stats respects limit parameter."""
        mock_limiter = MagicMock()
        mock_limiter._use_redis = False
        mock_limiter._local_state = {}
        for i in range(20):
            mock_limiter._local_state[f"user:user{i}"] = MagicMock(request_count=i)
        mock_limiter.config = MagicMock()
        mock_limiter.config.requests_per_minute = 60
        mock_limiter.config.requests_per_hour = 1000
        mock_get_limiter.return_value = mock_limiter

        response = client.get("/clients?limit=5")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 5

    @patch("api.rate_limit_dashboard.get_rate_limiter", new_callable=AsyncMock)
    def test_get_client_stats_with_redis(self, mock_get_limiter):
        """Test getting client stats with Redis enabled."""
        mock_limiter = MagicMock()
        mock_limiter._use_redis = True
        mock_get_limiter.return_value = mock_limiter

        response = client.get("/clients")
        assert response.status_code == 200
        data = response.json()
        assert data == []


class TestConfigEndpoint:
    """Tests for config endpoints."""

    @patch("api.rate_limit_dashboard.get_rate_limiter", new_callable=AsyncMock)
    def test_get_config(self, mock_get_limiter):
        """Test getting rate limit config."""
        mock_limiter = MagicMock()
        mock_limiter._use_redis = False
        mock_limiter.config = MagicMock()
        mock_limiter.config.requests_per_minute = 100
        mock_limiter.config.requests_per_hour = 5000
        mock_limiter.config.burst_size = 20
        mock_get_limiter.return_value = mock_limiter

        response = client.get("/config")
        assert response.status_code == 200
        data = response.json()

        assert data["requests_per_minute"] == 100
        assert data["requests_per_hour"] == 5000
        assert data["burst_size"] == 20
        assert data["use_redis"] is False
        assert "endpoint_overrides" in data

    @patch("api.rate_limit_dashboard.get_rate_limiter", new_callable=AsyncMock)
    def test_update_config(self, mock_get_limiter):
        """Test updating rate limit config."""
        mock_limiter = MagicMock()
        mock_limiter.config = MagicMock()
        mock_limiter.config.requests_per_minute = 100
        mock_limiter.config.requests_per_hour = 5000
        mock_limiter.config.burst_size = 20
        mock_get_limiter.return_value = mock_limiter

        response = client.post("/config", json={"requests_per_minute": 200})
        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "success"
        assert data["config"]["requests_per_minute"] == 200

    @patch("api.rate_limit_dashboard.get_rate_limiter", new_callable=AsyncMock)
    def test_update_config_multiple_fields(self, mock_get_limiter):
        """Test updating multiple config fields."""
        mock_limiter = MagicMock()
        mock_limiter.config = MagicMock()
        mock_limiter.config.requests_per_minute = 100
        mock_limiter.config.requests_per_hour = 5000
        mock_limiter.config.burst_size = 20
        mock_get_limiter.return_value = mock_limiter

        response = client.post(
            "/config",
            json={"requests_per_minute": 150, "requests_per_hour": 3000, "burst_size": 30},
        )
        assert response.status_code == 200
        data = response.json()

        assert data["config"]["requests_per_minute"] == 150
        assert data["config"]["requests_per_hour"] == 3000
        assert data["config"]["burst_size"] == 30


class TestRateLimitSummaryModel:
    """Tests for RateLimitSummary model."""

    def test_summary_model_creation(self):
        """Test creating RateLimitSummary model."""
        summary = RateLimitSummary(
            total_requests=100,
            allowed_requests=80,
            blocked_requests=20,
            block_rate=20.0,
            active_clients=5,
            unique_endpoints=["/api/test"],
        )
        assert summary.total_requests == 100
        assert summary.allowed_requests == 80
        assert summary.block_rate == 20.0


class TestEndpointStatsModel:
    """Tests for EndpointStats model."""

    def test_endpoint_stats_creation(self):
        """Test creating EndpointStats model."""
        stats = EndpointStats(
            endpoint="/api/test",
            total_requests=100,
            allowed_requests=80,
            blocked_requests=20,
            block_rate=20.0,
        )
        assert stats.endpoint == "/api/test"
        assert stats.total_requests == 100


class TestClientStatsModel:
    """Tests for ClientStats model."""

    def test_client_stats_creation(self):
        """Test creating ClientStats model."""
        stats = ClientStats(
            client_key="user123",
            client_type="user",
            requests_in_minute=15,
            requests_in_hour=100,
            limit_minute=60,
            limit_hour=1000,
            remaining_minute=45,
            remaining_hour=900,
        )
        assert stats.client_key == "user123"
        assert stats.remaining_minute == 45


class TestDashboardStatsModel:
    """Tests for DashboardStats model."""

    def test_dashboard_stats_creation(self):
        """Test creating DashboardStats model."""
        summary = RateLimitSummary(
            total_requests=100,
            allowed_requests=80,
            blocked_requests=20,
            block_rate=20.0,
            active_clients=5,
            unique_endpoints=["/api/test"],
        )
        dashboard = DashboardStats(
            summary=summary,
            endpoint_stats=[],
            top_blocked_endpoints=[],
            recent_activity={"last_minute": 2, "last_hour": 10, "last_day": 20},
            last_updated=datetime.now(timezone.utc),
        )
        assert dashboard.summary.total_requests == 100
        assert dashboard.recent_activity["last_hour"] == 10


class TestConfigModels:
    """Tests for config models."""

    def test_config_info_creation(self):
        """Test creating ConfigInfo model."""
        config = ConfigInfo(
            requests_per_minute=100,
            requests_per_hour=5000,
            burst_size=20,
            use_redis=False,
            endpoint_overrides={},
        )
        assert config.requests_per_minute == 100
        assert config.use_redis is False

    def test_config_update_request(self):
        """Test ConfigUpdateRequest model."""
        update = ConfigUpdateRequest(requests_per_minute=200, burst_size=30)
        assert update.requests_per_minute == 200
        assert update.burst_size == 30
