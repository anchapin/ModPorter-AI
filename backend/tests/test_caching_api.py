"""
Tests for caching API endpoints.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock, AsyncMock
import json
import time

from src.main import app

client = TestClient(app)


class TestCachingAPI:
    """Test caching management endpoints."""

    def test_cache_health_check(self):
        """Test cache health check endpoint."""
        response = client.get("/api/v1/cache/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "cache_type" in data

    @patch('src.api.caching.get_cache_stats')
    def test_get_cache_stats(self, mock_stats):
        """Test getting cache statistics."""
        mock_stats.return_value = {
            "cache_type": "redis",
            "total_keys": 100,
            "memory_usage": "50MB",
            "hit_rate": 0.85,
            "miss_rate": 0.15,
            "evictions": 5,
            "uptime": 86400
        }
        
        response = client.get("/api/v1/cache/stats")
        assert response.status_code == 200
        data = response.json()
        assert data["total_keys"] == 100
        assert data["hit_rate"] == 0.85

    @patch('src.api.caching.get_cache_keys')
    def test_list_cache_keys(self, mock_keys):
        """Test listing cache keys."""
        mock_keys.return_value = [
            "user:123",
            "conversion:456",
            "session:789",
            "metadata:12345"
        ]
        
        response = client.get("/api/v1/cache/keys")
        assert response.status_code == 200
        data = response.json()
        assert len(data["keys"]) == 4
        assert "user:123" in data["keys"]

    def test_list_cache_keys_with_pattern(self):
        """Test listing cache keys with pattern filter."""
        with patch('src.api.caching.get_cache_keys') as mock_keys:
            mock_keys.return_value = ["user:123", "user:456"]
            
            response = client.get("/api/v1/cache/keys?pattern=user:*")
            assert response.status_code == 200
            data = response.json()
            assert len(data["keys"]) == 2
            mock_keys.assert_called_with("user:*")

    @patch('src.api.caching.get_cache_value')
    def test_get_cache_value(self, mock_get):
        """Test getting a specific cache value."""
        mock_get.return_value = {"user_id": 123, "username": "test_user", "role": "admin"}
        
        response = client.get("/api/v1/cache/user:123")
        assert response.status_code == 200
        data = response.json()
        assert data["user_id"] == 123
        assert data["username"] == "test_user"

    def test_get_cache_value_not_found(self):
        """Test getting a non-existent cache value."""
        with patch('src.api.caching.get_cache_value') as mock_get:
            mock_get.return_value = None
            
            response = client.get("/api/v1/cache/nonexistent:key")
            assert response.status_code == 404

    @patch('src.api.caching.set_cache_value')
    def test_set_cache_value(self, mock_set):
        """Test setting a cache value."""
        mock_set.return_value = True
        
        cache_data = {
            "key": "test:key",
            "value": {"message": "test data", "timestamp": time.time()},
            "ttl": 3600
        }
        
        response = client.post("/api/v1/cache", json=cache_data)
        assert response.status_code == 201
        data = response.json()
        assert data["success"] is True
        mock_set.assert_called_once()

    def test_set_cache_value_with_ttl(self):
        """Test setting cache value with TTL."""
        with patch('src.api.caching.set_cache_value') as mock_set:
            mock_set.return_value = True
            
            cache_data = {
                "key": "temp:key",
                "value": {"temp": True},
                "ttl": 60  # 1 minute TTL
            }
            
            response = client.post("/api/v1/cache", json=cache_data)
            assert response.status_code == 201
            mock_set.assert_called_once()

    @patch('src.api.caching.delete_cache_key')
    def test_delete_cache_key(self, mock_delete):
        """Test deleting a cache key."""
        mock_delete.return_value = True
        
        response = client.delete("/api/v1/cache/user:123")
        assert response.status_code == 204
        mock_delete.assert_called_once_with("user:123")

    def test_delete_cache_key_not_found(self):
        """Test deleting a non-existent cache key."""
        with patch('src.api.caching.delete_cache_key') as mock_delete:
            mock_delete.return_value = False
            
            response = client.delete("/api/v1/cache/nonexistent:key")
            assert response.status_code == 404

    @patch('src.api.caching.clear_cache')
    def test_clear_cache(self, mock_clear):
        """Test clearing entire cache."""
        mock_clear.return_value = {"cleared_keys": 100}
        
        response = client.delete("/api/v1/cache")
        assert response.status_code == 200
        data = response.json()
        assert data["cleared_keys"] == 100

    @patch('src.api.caching.clear_cache_pattern')
    def test_clear_cache_pattern(self, mock_clear):
        """Test clearing cache keys matching pattern."""
        mock_clear.return_value = {"cleared_keys": 25}
        
        response = client.delete("/api/v1/cache?pattern=user:*")
        assert response.status_code == 200
        data = response.json()
        assert data["cleared_keys"] == 25

    @patch('src.api.caching.warm_cache')
    def test_warm_cache(self, mock_warm):
        """Test cache warming."""
        mock_warm.return_value = {
            "warmed_keys": 50,
            "warming_time": 5.2,
            "memory_usage": "25MB"
        }
        
        response = client.post("/api/v1/cache/warm")
        assert response.status_code == 200
        data = response.json()
        assert data["warmed_keys"] == 50

    @patch('src.api.caching.get_cache_performance')
    def test_get_cache_performance(self, mock_perf):
        """Test getting cache performance metrics."""
        mock_perf.return_value = {
            "avg_get_time": 0.001,
            "avg_set_time": 0.002,
            "max_get_time": 0.005,
            "max_set_time": 0.008,
            "operations_per_second": 1000,
            "memory_efficiency": 0.92
        }
        
        response = client.get("/api/v1/cache/performance")
        assert response.status_code == 200
        data = response.json()
        assert data["avg_get_time"] == 0.001
        assert data["operations_per_second"] == 1000

    @patch('src.api.caching.configure_cache')
    def test_configure_cache(self, mock_config):
        """Test cache configuration."""
        mock_config.return_value = {"success": True}
        
        config_data = {
            "max_memory": "512MB",
            "eviction_policy": "lru",
            "default_ttl": 3600,
            "compression": True
        }
        
        response = client.put("/api/v1/cache/config", json=config_data)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    @patch('src.api.caching.get_cache_info')
    def test_get_cache_info(self, mock_info):
        """Test getting cache information."""
        mock_info.return_value = {
            "cache_type": "redis",
            "version": "6.2.0",
            "cluster_nodes": 3,
            "replication": True,
            "persistence": True,
            "configuration": {
                "max_memory": "1GB",
                "eviction_policy": "lru",
                "max_clients": 1000
            }
        }
        
        response = client.get("/api/v1/cache/info")
        assert response.status_code == 200
        data = response.json()
        assert data["cache_type"] == "redis"
        assert data["cluster_nodes"] == 3

    @patch('src.api.caching.backup_cache')
    def test_backup_cache(self, mock_backup):
        """Test cache backup."""
        mock_backup.return_value = {
            "backup_file": "/backups/cache_backup_20230101.db",
            "backup_size": "100MB",
            "backup_time": 60
        }
        
        response = client.post("/api/v1/cache/backup")
        assert response.status_code == 200
        data = response.json()
        assert "backup_file" in data

    @patch('src.api.caching.restore_cache')
    def test_restore_cache(self, mock_restore):
        """Test cache restore."""
        mock_restore.return_value = {
            "restored_keys": 100,
            "restore_time": 30,
            "success": True
        }
        
        restore_data = {"backup_file": "/backups/cache_backup_20230101.db"}
        
        response = client.post("/api/v1/cache/restore", json=restore_data)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_cache_key_validation(self):
        """Test cache key validation."""
        # Test invalid key formats
        invalid_keys = [
            "",  # Empty key
            " ",  # Space only
            "key with spaces",  # Spaces in key
            "a" * 1000  # Too long key
        ]
        
        for invalid_key in invalid_keys:
            response = client.get(f"/api/v1/cache/{invalid_key}")
            # Should return validation error
            assert response.status_code in [400, 422]

    @patch('src.api.caching.get_cache_ttl')
    def test_get_cache_ttl(self, mock_ttl):
        """Test getting TTL for a cache key."""
        mock_ttl.return_value = {"key": "test:key", "ttl": 3600, "remaining": 1800}
        
        response = client.get("/api/v1/cache/test:key/ttl")
        assert response.status_code == 200
        data = response.json()
        assert data["ttl"] == 3600
        assert data["remaining"] == 1800

    @patch('src.api.caching.set_cache_ttl')
    def test_set_cache_ttl(self, mock_set_ttl):
        """Test setting TTL for a cache key."""
        mock_set_ttl.return_value = True
        
        ttl_data = {"key": "test:key", "ttl": 7200}
        
        response = client.put("/api/v1/cache/test:key/ttl", json=ttl_data)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    @patch('src.api.caching.get_cache_size')
    def test_get_cache_size(self, mock_size):
        """Test getting cache size information."""
        mock_size.return_value = {
            "total_keys": 1000,
            "memory_used": "500MB",
            "memory_available": "500MB",
            "size_percentage": 50.0
        }
        
        response = client.get("/api/v1/cache/size")
        assert response.status_code == 200
        data = response.json()
        assert data["total_keys"] == 1000
        assert data["size_percentage"] == 50.0

    @patch('src.api.caching.optimize_cache')
    def test_optimize_cache(self, mock_optimize):
        """Test cache optimization."""
        mock_optimize.return_value = {
            "optimizations_applied": 10,
            "memory_freed": "100MB",
            "fragmentation_reduced": 0.15,
            "optimization_time": 2.5
        }
        
        response = client.post("/api/v1/cache/optimize")
        assert response.status_code == 200
        data = response.json()
        assert data["optimizations_applied"] == 10

    def test_cache_concurrent_operations(self):
        """Test handling concurrent cache operations."""
        import threading
        import time
        
        results = []
        
        def set_value(key_suffix):
            response = client.post("/api/v1/cache", json={
                "key": f"test:key:{key_suffix}",
                "value": {"data": f"value{key_suffix}"}
            })
            results.append(response.status_code)
        
        # Create multiple threads for concurrent operations
        threads = [threading.Thread(target=set_value, args=(i,)) for i in range(5)]
        
        # Start all threads
        for thread in threads:
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # All operations should succeed or fail consistently
        assert all(status == results[0] for status in results)

    @patch('src.api.caching.test_cache_connection')
    def test_cache_connection(self, mock_test):
        """Test cache connection diagnostics."""
        mock_test.return_value = {
            "connection_status": "healthy",
            "latency": 0.001,
            "throughput": 1000,
            "errors": []
        }
        
        response = client.get("/api/v1/cache/connection")
        assert response.status_code == 200
        data = response.json()
        assert data["connection_status"] == "healthy"

    def test_cache_error_handling(self):
        """Test cache error handling."""
        with patch('src.api.caching.get_cache_value', side_effect=Exception("Cache error")):
            response = client.get("/api/v1/cache/test:key")
            assert response.status_code == 500
            data = response.json()
            assert "internal server error" in data["detail"].lower()

    @patch('src.api.caching.get_cache_analytics')
    def test_get_cache_analytics(self, mock_analytics):
        """Test getting cache analytics data."""
        mock_analytics.return_value = {
            "time_range": "24h",
            "top_keys": [
                {"key": "user:123", "hits": 100},
                {"key": "conversion:456", "hits": 85}
            ],
            "hit_rate_trend": [
                {"time": "2023-01-01T00:00:00Z", "rate": 0.80},
                {"time": "2023-01-01T01:00:00Z", "rate": 0.85}
            ],
            "memory_usage_trend": [
                {"time": "2023-01-01T00:00:00Z", "usage": "400MB"},
                {"time": "2023-01-01T01:00:00Z", "usage": "420MB"}
            ]
        }
        
        response = client.get("/api/v1/cache/analytics?time_range=24h")
        assert response.status_code == 200
        data = response.json()
        assert len(data["top_keys"]) == 2
        assert data["hit_rate_trend"][0]["rate"] == 0.80

    def test_cache_response_headers(self):
        """Test that cache responses have appropriate headers."""
        response = client.get("/api/v1/cache/stats")
        headers = response.headers
        # Test for CORS headers
        assert "access-control-allow-origin" in headers
        # Test for cache control
        assert "cache-control" in headers
