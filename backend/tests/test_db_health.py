"""
Tests for database health check and monitoring utilities.
Addresses Issue #575: Backend: Database Schema and Migrations - Async SQLAlchemy Management
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

# Import the module under test
from db.health import (
    HealthCheckResult,
    QueryMetrics,
    ConnectionPoolMetrics,
    DatabaseHealthChecker,
    NPlusOneDetector,
    monitored_session,
    create_health_checker,
    create_n_plus_one_detector
)


class TestHealthCheckResult:
    """Test HealthCheckResult dataclass"""
    
    def test_health_check_result_creation(self):
        """Test creating a HealthCheckResult"""
        result = HealthCheckResult(
            is_healthy=True,
            message="Database is healthy",
            latency_ms=5.5
        )
        
        assert result.is_healthy is True
        assert result.message == "Database is healthy"
        assert result.latency_ms == 5.5
        assert result.timestamp is not None
    
    def test_health_check_result_to_dict(self):
        """Test converting HealthCheckResult to dictionary"""
        result = HealthCheckResult(
            is_healthy=False,
            message="Connection failed",
            latency_ms=100.0,
            details={"error": "timeout"}
        )
        
        result_dict = result.to_dict()
        
        assert result_dict["is_healthy"] is False
        assert result_dict["message"] == "Connection failed"
        assert result_dict["latency_ms"] == 100.0
        assert result_dict["details"]["error"] == "timeout"
        assert "timestamp" in result_dict


class TestQueryMetrics:
    """Test QueryMetrics dataclass"""
    
    def test_query_metrics_creation(self):
        """Test creating QueryMetrics"""
        metrics = QueryMetrics(
            query_text="SELECT * FROM users",
            execution_time_ms=15.5,
            rows_affected=10
        )
        
        assert metrics.query_text == "SELECT * FROM users"
        assert metrics.execution_time_ms == 15.5
        assert metrics.rows_affected == 10
        assert metrics.error is None
    
    def test_query_metrics_with_error(self):
        """Test QueryMetrics with error"""
        metrics = QueryMetrics(
            query_text="SELECT * FROM invalid_table",
            execution_time_ms=5.0,
            error="Table not found"
        )
        
        assert metrics.error == "Table not found"


class TestConnectionPoolMetrics:
    """Test ConnectionPoolMetrics dataclass"""
    
    def test_pool_metrics_creation(self):
        """Test creating ConnectionPoolMetrics"""
        metrics = ConnectionPoolMetrics(
            pool_size=10,
            checked_in=8,
            checked_out=2,
            overflow=0
        )
        
        assert metrics.pool_size == 10
        assert metrics.checked_in == 8
        assert metrics.checked_out == 2
    
    def test_pool_metrics_to_dict(self):
        """Test converting ConnectionPoolMetrics to dictionary"""
        metrics = ConnectionPoolMetrics(
            pool_size=5,
            checked_in=3,
            checked_out=2
        )
        
        result = metrics.to_dict()
        
        assert result["pool_size"] == 5
        assert result["checked_in"] == 3
        assert result["checked_out"] == 2


class TestDatabaseHealthChecker:
    """Test DatabaseHealthChecker class"""
    
    @pytest.fixture
    def mock_engine(self):
        """Create a mock AsyncEngine"""
        engine = Mock(spec=AsyncEngine)
        engine.pool = Mock()
        engine.pool.size = Mock(return_value=10)
        engine.pool.checkedin = Mock(return_value=8)
        engine.pool.checkedout = Mock(return_value=2)
        engine.pool.overflow = Mock(return_value=0)
        engine.pool.invalidatedcount = Mock(return_value=0)
        return engine
    
    @pytest.fixture
    def health_checker(self, mock_engine):
        """Create a DatabaseHealthChecker instance"""
        return DatabaseHealthChecker(mock_engine)
    
    def test_health_checker_initialization(self, mock_engine):
        """Test DatabaseHealthChecker initialization"""
        checker = DatabaseHealthChecker(mock_engine)
        
        assert checker.engine == mock_engine
        assert checker._slow_query_threshold_ms == 1000.0
        assert len(checker._query_history) == 0
    
    @pytest.mark.asyncio
    async def test_check_health_success(self, health_checker, mock_engine):
        """Test successful health check"""
        # Mock the connection
        mock_conn = AsyncMock()
        mock_result = Mock()
        mock_result.fetchone = Mock(return_value=[1])
        mock_conn.execute = AsyncMock(return_value=mock_result)
        mock_conn.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_conn.__aexit__ = AsyncMock(return_value=None)
        
        mock_engine.connect = Mock(return_value=mock_conn)
        
        result = await health_checker.check_health()
        
        assert result.is_healthy is True
        assert "healthy" in result.message.lower()
        assert result.latency_ms is not None
    
    @pytest.mark.asyncio
    async def test_check_health_failure(self, health_checker, mock_engine):
        """Test failed health check"""
        mock_conn = AsyncMock()
        mock_conn.execute = AsyncMock(side_effect=Exception("Connection refused"))
        mock_conn.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_conn.__aexit__ = AsyncMock(return_value=None)
        
        mock_engine.connect = Mock(return_value=mock_conn)
        
        result = await health_checker.check_health()
        
        assert result.is_healthy is False
        assert "failed" in result.message.lower()
    
    def test_record_query(self, health_checker):
        """Test recording query metrics"""
        metrics = QueryMetrics(
            query_text="SELECT * FROM test",
            execution_time_ms=50.0
        )
        
        health_checker.record_query(metrics)
        
        assert len(health_checker._query_history) == 1
        assert health_checker._query_history[0] == metrics
    
    def test_record_slow_query(self, health_checker, caplog):
        """Test that slow queries are logged"""
        metrics = QueryMetrics(
            query_text="SELECT * FROM large_table",
            execution_time_ms=1500.0  # Over threshold
        )
        
        with caplog.at_level("WARNING"):
            health_checker.record_query(metrics)
        
        assert any("Slow query" in record.message for record in caplog.records)
    
    def test_get_slow_queries(self, health_checker):
        """Test getting slow queries"""
        # Add some queries
        health_checker.record_query(QueryMetrics("fast", 10.0))
        health_checker.record_query(QueryMetrics("slow", 1500.0))
        health_checker.record_query(QueryMetrics("very_slow", 3000.0))
        
        slow_queries = health_checker.get_slow_queries()
        
        assert len(slow_queries) == 2
    
    def test_get_slow_queries_custom_threshold(self, health_checker):
        """Test getting slow queries with custom threshold"""
        health_checker.record_query(QueryMetrics("query1", 100.0))
        health_checker.record_query(QueryMetrics("query2", 200.0))
        
        slow_queries = health_checker.get_slow_queries(threshold_ms=150.0)
        
        assert len(slow_queries) == 1
    
    def test_get_query_stats_empty(self, health_checker):
        """Test getting query stats when empty"""
        stats = health_checker.get_query_stats()
        
        assert stats["total_queries"] == 0
        assert stats["average_time_ms"] == 0
    
    def test_get_query_stats(self, health_checker):
        """Test getting aggregate query stats"""
        health_checker.record_query(QueryMetrics("q1", 10.0))
        health_checker.record_query(QueryMetrics("q2", 20.0))
        health_checker.record_query(QueryMetrics("q3", 30.0))
        
        stats = health_checker.get_query_stats()
        
        assert stats["total_queries"] == 3
        assert stats["average_time_ms"] == 20.0
        assert stats["max_time_ms"] == 30.0
        assert stats["min_time_ms"] == 10.0
    
    def test_clear_history(self, health_checker):
        """Test clearing query history"""
        health_checker.record_query(QueryMetrics("q1", 10.0))
        health_checker.record_query(QueryMetrics("q2", 20.0))
        
        health_checker.clear_history()
        
        assert len(health_checker._query_history) == 0
    
    def test_history_size_limit(self, health_checker):
        """Test that history is trimmed when exceeding max size"""
        health_checker._max_history_size = 10
        
        for i in range(15):
            health_checker.record_query(QueryMetrics(f"q{i}", float(i)))
        
        assert len(health_checker._query_history) == 10


class TestNPlusOneDetector:
    """Test NPlusOneDetector class"""
    
    @pytest.fixture
    def detector(self):
        """Create an NPlusOneDetector instance"""
        return NPlusOneDetector()
    
    def test_detector_initialization(self, detector):
        """Test NPlusOneDetector initialization"""
        assert len(detector._query_counts) == 0
        assert detector._detection_threshold == 10
    
    def test_record_query(self, detector):
        """Test recording query patterns"""
        detector.record_query("SELECT * FROM users WHERE id = ?")
        detector.record_query("SELECT * FROM users WHERE id = ?")
        
        assert detector._query_counts["SELECT * FROM users WHERE id = ?"] == 2
    
    def test_detect_n_plus_one_none(self, detector):
        """Test N+1 detection when no patterns exist"""
        patterns = detector.detect_n_plus_one()
        
        assert len(patterns) == 0
    
    def test_detect_n_plus_one_found(self, detector):
        """Test N+1 detection when patterns exist"""
        # Record the same query 15 times
        for _ in range(15):
            detector.record_query("SELECT * FROM items WHERE user_id = ?")
        
        patterns = detector.detect_n_plus_one()
        
        assert len(patterns) == 1
        assert patterns[0]["count"] == 15
        assert patterns[0]["severity"] == "medium"
    
    def test_detect_n_plus_one_high_severity(self, detector):
        """Test N+1 detection with high severity"""
        # Record the same query 60 times
        for _ in range(60):
            detector.record_query("SELECT * FROM related WHERE parent_id = ?")
        
        patterns = detector.detect_n_plus_one()
        
        assert patterns[0]["severity"] == "high"
    
    def test_reset(self, detector):
        """Test resetting the detector"""
        detector.record_query("SELECT 1")
        detector.record_query("SELECT 2")
        
        detector.reset()
        
        assert len(detector._query_counts) == 0


class TestMonitoredSession:
    """Test monitored_session context manager"""
    
    @pytest.mark.asyncio
    async def test_monitored_session_basic(self):
        """Test basic monitored session usage"""
        mock_session = AsyncMock(spec=AsyncSession)
        
        async with monitored_session(mock_session) as session:
            assert session == mock_session
    
    @pytest.mark.asyncio
    async def test_monitored_session_with_health_checker(self):
        """Test monitored session with health checker"""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_engine = Mock(spec=AsyncEngine)
        health_checker = DatabaseHealthChecker(mock_engine)
        
        async with monitored_session(mock_session, health_checker=health_checker) as session:
            assert session == mock_session


class TestFactoryFunctions:
    """Test factory functions"""
    
    def test_create_health_checker(self):
        """Test create_health_checker factory"""
        mock_engine = Mock(spec=AsyncEngine)
        
        checker = create_health_checker(mock_engine)
        
        assert isinstance(checker, DatabaseHealthChecker)
        assert checker.engine == mock_engine
    
    def test_create_n_plus_one_detector(self):
        """Test create_n_plus_one_detector factory"""
        detector = create_n_plus_one_detector()
        
        assert isinstance(detector, NPlusOneDetector)


class TestIntegration:
    """Integration tests for database health monitoring"""
    
    @pytest.fixture
    def mock_engine(self):
        """Create a mock AsyncEngine"""
        engine = Mock(spec=AsyncEngine)
        engine.pool = Mock()
        engine.pool.size = Mock(return_value=10)
        engine.pool.checkedin = Mock(return_value=8)
        engine.pool.checkedout = Mock(return_value=2)
        engine.pool.overflow = Mock(return_value=0)
        engine.pool.invalidatedcount = Mock(return_value=0)
        return engine
    
    @pytest.mark.asyncio
    async def test_full_health_check_workflow(self, mock_engine):
        """Test complete health check workflow"""
        # Mock successful connection
        mock_conn = AsyncMock()
        mock_result = Mock()
        mock_result.fetchone = Mock(return_value=[1])
        mock_conn.execute = AsyncMock(return_value=mock_result)
        mock_conn.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_conn.__aexit__ = AsyncMock(return_value=None)
        mock_engine.connect = Mock(return_value=mock_conn)
        
        checker = create_health_checker(mock_engine)
        
        # Check health
        health_result = await checker.check_health()
        assert health_result.is_healthy is True
        
        # Record some queries
        checker.record_query(QueryMetrics("SELECT 1", 5.0))
        checker.record_query(QueryMetrics("SELECT 2", 10.0))
        
        # Get stats
        stats = checker.get_query_stats()
        assert stats["total_queries"] == 2
    
    def test_n_plus_one_detection_workflow(self):
        """Test N+1 detection workflow"""
        detector = create_n_plus_one_detector()
        
        # Simulate N+1 pattern
        for i in range(20):
            detector.record_query(f"SELECT * FROM items WHERE parent_id = ?")
        
        patterns = detector.detect_n_plus_one()
        
        assert len(patterns) == 1
        assert patterns[0]["count"] == 20
        
        # Reset and check again
        detector.reset()
        patterns = detector.detect_n_plus_one()
        assert len(patterns) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])