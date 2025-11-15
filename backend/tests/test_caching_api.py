
from datetime import datetime
from unittest.mock import AsyncMock, patch, MagicMock

import pytest
from fastapi.testclient import TestClient

from src.main import app
from src.services.graph_caching import CacheStrategy, CacheInvalidationStrategy

client = TestClient(app)


@pytest.fixture
def mock_cache_service():
    with patch("src.api.caching.graph_caching_service", new_callable=MagicMock) as mock_service:
        mock_service.get_cache_stats = AsyncMock(return_value={"overall": {"hits": 100, "misses": 20}})
        mock_service.warm_up = AsyncMock(return_value={"success": True, "warmed_up": 50})
        mock_service.invalidate = AsyncMock(return_value=10)
        mock_service.cache_configs = {
            "nodes": MagicMock(
                max_size_mb=100.0,
                max_entries=10000,
                ttl_seconds=3600,
                strategy=CacheStrategy.LRU,
                invalidation_strategy=CacheInvalidationStrategy.TIME_BASED,
                refresh_interval_seconds=300,
                enable_compression=True,
                enable_serialization=True,
            )
        }
        mock_service.cache_stats = {"overall": MagicMock(hit_ratio=0.8, memory_usage_mb=50.0, avg_access_time_ms=10.0)}
        mock_service.l1_cache = {"nodes": {"key1": "value1"}}
        yield mock_service


@pytest.mark.asyncio
async def test_get_cache_stats_success(mock_cache_service):
    """
    Tests getting cache stats successfully.
    """
    response = client.get("/api/v1/caching/cache/stats")

    assert response.status_code == 200
    json_response = response.json()
    assert json_response["success"] is True
    assert json_response["cache_stats"]["overall"]["hits"] == 100


@pytest.mark.asyncio
async def test_warm_up_cache_success(mock_cache_service):
    """
    Tests warming up the cache successfully.
    """
    response = client.post("/api/v1/caching/cache/warm-up")

    assert response.status_code == 200
    json_response = response.json()
    assert json_response["success"] is True
    assert json_response["warmed_up"] == 50


@pytest.mark.asyncio
async def test_invalidate_cache_success(mock_cache_service):
    """
    Tests invalidating the cache successfully.
    """
    invalidation_data = {
        "cache_type": "nodes",
        "pattern": "user:*",
    }
    response = client.post("/api/v1/caching/cache/invalidate", json=invalidation_data)

    assert response.status_code == 200
    json_response = response.json()
    assert json_response["success"] is True
    assert json_response["invalidated_entries"] == 10


@pytest.mark.asyncio
async def test_get_cache_config_success(mock_cache_service):
    """
    Tests getting cache configuration successfully.
    """
    response = client.get("/api/v1/caching/cache/config")

    assert response.status_code == 200
    json_response = response.json()
    assert json_response["success"] is True
    assert "nodes" in json_response["cache_configs"]
    assert json_response["cache_configs"]["nodes"]["max_size_mb"] == 100.0


@pytest.mark.asyncio
async def test_update_cache_config_success(mock_cache_service):
    """
    Tests updating cache configuration successfully.
    """
    update_data = {
        "cache_type": "nodes",
        "max_size_mb": 200.0,
    }
    response = client.post("/api/v1/caching/cache/config", json=update_data)

    assert response.status_code == 200
    json_response = response.json()
    assert json_response["success"] is True
    assert json_response["config_updated"] is True
    mock_cache_service.cache_configs["nodes"].max_size_mb == 200.0


@pytest.mark.asyncio
async def test_get_performance_metrics_success(mock_cache_service):
    """
    Tests getting performance metrics successfully.
    """
    response = client.get("/api/v1/caching/cache/performance")

    assert response.status_code == 200
    json_response = response.json()
    assert json_response["success"] is True
    assert "overall" in json_response["performance_metrics"]


@pytest.mark.asyncio
async def test_clear_cache_success(mock_cache_service):
    """
    Tests clearing the cache successfully.
    """
    response = client.delete("/api/v1/caching/cache/clear?cache_type=nodes")

    assert response.status_code == 200
    json_response = response.json()
    assert json_response["success"] is True
    assert json_response["cleared_entries"] > 0


@pytest.mark.asyncio
async def test_get_cache_health_success(mock_cache_service):
    """
    Tests getting cache health successfully.
    """
    response = client.get("/api/v1/caching/cache/health")

    assert response.status_code == 200
    json_response = response.json()
    assert json_response["success"] is True
    assert json_response["health_status"] == "healthy"
