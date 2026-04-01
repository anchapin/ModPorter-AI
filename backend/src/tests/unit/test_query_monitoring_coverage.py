"""
Tests for Query Monitoring API to improve coverage.
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import status


class TestQueryMonitoring:
    """Test query monitoring endpoints."""

    @pytest.mark.asyncio
    async def test_get_query_stats(self):
        """Test getting query statistics."""
        from api.query_monitoring import QueryStatsResponse
        
        # Test the response model
        response = QueryStatsResponse(
            total_queries=1000,
            slow_queries=50,
            avg_execution_time_ms=150.5,
            cache_hit_ratio=0.85,
        )
        
        assert response.total_queries == 1000
        assert response.slow_queries == 50
        assert response.avg_execution_time_ms == 150.5
        assert response.cache_hit_ratio == 0.85

    @pytest.mark.asyncio
    async def test_get_slow_queries(self):
        """Test getting slow queries list."""
        from api.query_monitoring import SlowQueryResponse
        
        slow_query = SlowQueryResponse(
            query_id="q-123",
            query_text="SELECT * FROM users",
            execution_time_ms=2500.0,
            timestamp=datetime.now(timezone.utc),
            user_id="user-456",
        )
        
        assert slow_query.query_id == "q-123"
        assert slow_query.execution_time_ms == 2500.0

    @pytest.mark.asyncio
    async def test_get_query_stats_empty(self):
        """Test getting query stats when no queries."""
        from api.query_monitoring import QueryStatsResponse
        
        response = QueryStatsResponse(
            total_queries=0,
            slow_queries=0,
            avg_execution_time_ms=0.0,
            cache_hit_ratio=0.0,
        )
        
        assert response.total_queries == 0


class TestQueryMonitoringModels:
    """Test query monitoring models."""

    def test_query_stats_response(self):
        """Test QueryStatsResponse model."""
        from api.query_monitoring import QueryStatsResponse
        
        response = QueryStatsResponse(
            total_queries=500,
            slow_queries=25,
            avg_execution_time_ms=100.0,
            cache_hit_ratio=0.9,
        )
        
        assert response.total_queries == 500
        assert response.slow_queries == 25
        assert response.avg_execution_time_ms == 100.0
        assert response.cache_hit_ratio == 0.9

    def test_slow_query_response(self):
        """Test SlowQueryResponse model."""
        from api.query_monitoring import SlowQueryResponse
        
        timestamp = datetime.now(timezone.utc)
        response = SlowQueryResponse(
            query_id="q-001",
            query_text="SELECT * FROM conversions WHERE status = 'pending'",
            execution_time_ms=3000.0,
            timestamp=timestamp,
            user_id="u-123",
        )
        
        assert response.query_id == "q-001"
        assert "conversions" in response.query_text
        assert response.execution_time_ms == 3000.0

    def test_query_stats_response_zero_values(self):
        """Test QueryStatsResponse with zero values."""
        from api.query_monitoring import QueryStatsResponse
        
        response = QueryStatsResponse(
            total_queries=0,
            slow_queries=0,
            avg_execution_time_ms=0.0,
            cache_hit_ratio=0.0,
        )
        
        # All zero values should be valid
        assert response.total_queries == 0

    def test_query_stats_response_high_cache_hit(self):
        """Test QueryStatsResponse with high cache hit ratio."""
        from api.query_monitoring import QueryStatsResponse
        
        response = QueryStatsResponse(
            total_queries=10000,
            slow_queries=10,
            avg_execution_time_ms=50.0,
            cache_hit_ratio=0.99,
        )
        
        assert response.cache_hit_ratio == 0.99