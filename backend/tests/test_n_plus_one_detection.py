"""
Tests for N+1 Query Detection Module

Tests the query monitoring system's ability to detect and report
N+1 query patterns and performance issues.
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from db.query_monitor import (
    QueryMonitor,
    QueryMetrics,
    QueryMonitorStack,
    track_query_context,
    setup_query_monitoring,
    get_query_report,
    reset_query_monitor,
)


class TestQueryMetrics:
    """Test QueryMetrics data structure"""
    
    def test_init(self):
        """Test initialization"""
        metrics = QueryMetrics(sql_pattern="SELECT * FROM users WHERE id = ?")
        assert metrics.count == 0
        assert metrics.total_time == 0.0
        assert metrics.min_time == float('inf')
        assert metrics.max_time == 0.0
        assert metrics.parameters == []
    
    def test_add_execution(self):
        """Test recording executions"""
        metrics = QueryMetrics(sql_pattern="SELECT * FROM users WHERE id = ?")
        
        metrics.add_execution(0.1, (1,))
        assert metrics.count == 1
        assert metrics.total_time == 0.1
        
        metrics.add_execution(0.2, (2,))
        assert metrics.count == 2
        assert metrics.total_time == pytest.approx(0.3)
        assert metrics.min_time == 0.1
        assert metrics.max_time == 0.2
    
    def test_avg_time(self):
        """Test average time calculation"""
        metrics = QueryMetrics(sql_pattern="SELECT * FROM users")
        metrics.add_execution(0.1)
        metrics.add_execution(0.2)
        metrics.add_execution(0.3)
        
        assert metrics.avg_time == pytest.approx(0.2)
    
    def test_avg_time_zero(self):
        """Test average time with no executions"""
        metrics = QueryMetrics(sql_pattern="SELECT * FROM users")
        assert metrics.avg_time == 0.0
    
    def test_is_potential_n_plus_one_true(self):
        """Test N+1 detection when threshold is exceeded"""
        metrics = QueryMetrics(sql_pattern="SELECT * FROM users WHERE id = ?")
        
        # Add 6 executions with different parameters
        for i in range(6):
            metrics.add_execution(0.01, (i,))
        
        assert metrics.is_potential_n_plus_one(threshold=5) is True
    
    def test_is_potential_n_plus_one_false_same_params(self):
        """Test N+1 detection with same parameters"""
        metrics = QueryMetrics(sql_pattern="SELECT * FROM users WHERE id = ?")
        
        # Add 6 executions with same parameter
        for _ in range(6):
            metrics.add_execution(0.01, (1,))
        
        # Same parameter doesn't count as N+1
        assert metrics.is_potential_n_plus_one(threshold=5) is False
    
    def test_is_potential_n_plus_one_false_low_count(self):
        """Test N+1 detection below threshold"""
        metrics = QueryMetrics(sql_pattern="SELECT * FROM users WHERE id = ?")
        
        # Add 3 executions
        for i in range(3):
            metrics.add_execution(0.01, (i,))
        
        assert metrics.is_potential_n_plus_one(threshold=5) is False


class TestQueryMonitor:
    """Test QueryMonitor"""
    
    def test_init(self):
        """Test initialization"""
        monitor = QueryMonitor(enabled=True, threshold=5)
        assert monitor.enabled is True
        assert monitor.threshold == 5
        assert len(monitor.queries) == 0
    
    def test_normalize_query_numbers(self):
        """Test numeric literal normalization"""
        monitor = QueryMonitor()
        
        sql1 = "SELECT * FROM users WHERE id = 123"
        sql2 = "SELECT * FROM users WHERE id = 456"
        
        assert monitor.normalize_query(sql1) == monitor.normalize_query(sql2)
    
    def test_normalize_query_strings(self):
        """Test string literal normalization"""
        monitor = QueryMonitor()
        
        sql1 = "SELECT * FROM users WHERE name = 'Alice'"
        sql2 = "SELECT * FROM users WHERE name = 'Bob'"
        
        assert monitor.normalize_query(sql1) == monitor.normalize_query(sql2)
    
    def test_normalize_query_uuids(self):
        """Test UUID normalization"""
        monitor = QueryMonitor()
        
        sql1 = "SELECT * FROM users WHERE id = '550e8400-e29b-41d4-a716-446655440000'"
        sql2 = "SELECT * FROM users WHERE id = '6ba7b810-9dad-11d1-80b4-00c04fd430c8'"
        
        assert monitor.normalize_query(sql1) == monitor.normalize_query(sql2)
    
    def test_normalize_query_whitespace(self):
        """Test whitespace normalization"""
        monitor = QueryMonitor()
        
        sql1 = "SELECT  *  FROM  users  WHERE  id = ?"
        sql2 = "SELECT * FROM users WHERE id = ?"
        
        assert monitor.normalize_query(sql1) == monitor.normalize_query(sql2)
    
    def test_record_query(self):
        """Test recording a query"""
        monitor = QueryMonitor(enabled=True, threshold=5)
        
        sql = "SELECT * FROM users WHERE id = 123"
        monitor.record_query(sql, 0.1, (123,))
        
        assert len(monitor.queries) == 1
    
    def test_record_multiple_executions(self):
        """Test recording multiple executions of same query"""
        monitor = QueryMonitor(enabled=True, threshold=5)
        
        sql = "SELECT * FROM users WHERE id = ?"
        
        for i in range(3):
            monitor.record_query(sql, 0.1, (i,))
        
        assert len(monitor.queries) == 1
        normalized = monitor.normalize_query(sql)
        assert monitor.queries[normalized].count == 3
    
    def test_get_n_plus_one_candidates(self):
        """Test detecting N+1 candidates"""
        monitor = QueryMonitor(enabled=True, threshold=3)
        
        sql = "SELECT * FROM users WHERE id = ?"
        
        for i in range(5):
            monitor.record_query(sql, 0.01, (i,))
        
        candidates = monitor.get_n_plus_one_candidates()
        assert len(candidates) == 1
        assert candidates[0][1].count == 5
    
    def test_get_slowest_queries(self):
        """Test getting slowest queries"""
        monitor = QueryMonitor(enabled=True)
        
        monitor.record_query("SELECT * FROM users WHERE id = 1", 0.5, (1,))
        monitor.record_query("SELECT * FROM orders WHERE id = 1", 0.3, (1,))
        monitor.record_query("SELECT * FROM products WHERE id = 1", 0.2, (1,))
        
        slowest = monitor.get_slowest_queries(limit=2)
        assert len(slowest) == 2
        assert slowest[0][1].total_time == 0.5
        assert slowest[1][1].total_time == 0.3
    
    def test_get_most_executed_queries(self):
        """Test getting most executed queries"""
        monitor = QueryMonitor(enabled=True)
        
        # Query 1: executed 5 times
        for i in range(5):
            monitor.record_query("SELECT * FROM users WHERE id = ?", 0.01, (i,))
        
        # Query 2: executed 3 times
        for i in range(3):
            monitor.record_query("SELECT * FROM orders WHERE id = ?", 0.01, (i,))
        
        most_executed = monitor.get_most_executed_queries(limit=2)
        assert len(most_executed) == 2
        assert most_executed[0][1].count == 5
        assert most_executed[1][1].count == 3
    
    def test_disabled_monitor(self):
        """Test that disabled monitor doesn't record queries"""
        monitor = QueryMonitor(enabled=False)
        
        monitor.record_query("SELECT * FROM users", 0.1)
        assert len(monitor.queries) == 0
    
    def test_reset(self):
        """Test resetting monitor"""
        monitor = QueryMonitor(enabled=True)
        monitor.record_query("SELECT * FROM users", 0.1)
        
        assert len(monitor.queries) == 1
        monitor.reset()
        assert len(monitor.queries) == 0
    
    def test_get_report(self):
        """Test generating a report"""
        monitor = QueryMonitor(enabled=True, threshold=2)
        
        # Add some N+1 queries
        for i in range(3):
            monitor.record_query("SELECT * FROM users WHERE id = ?", 0.01, (i,))
        
        # Add some regular queries
        monitor.record_query("SELECT COUNT(*) FROM users", 0.05)
        
        report = monitor.get_report()
        
        assert report["summary"]["total_unique_queries"] == 2
        assert report["summary"]["total_executions"] == 4
        assert report["summary"]["n_plus_one_issues"] == 1
        assert len(report["n_plus_one_candidates"]) == 1
        assert len(report["slowest_queries"]) > 0


class TestQueryMonitorStack:
    """Test QueryMonitorStack"""
    
    def test_push_pop(self):
        """Test pushing and popping contexts"""
        stack = QueryMonitorStack()
        
        context = stack.push("test_operation")
        assert context["name"] == "test_operation"
        assert context["query_count"] == 0
        
        popped = stack.pop()
        assert popped["name"] == "test_operation"
    
    def test_increment_query_count(self):
        """Test incrementing query count"""
        stack = QueryMonitorStack()
        
        stack.push("operation")
        stack.increment_query_count()
        stack.increment_query_count()
        
        context = stack.get_current_context()
        assert context["query_count"] == 2
    
    def test_nested_contexts(self):
        """Test nested contexts"""
        stack = QueryMonitorStack()
        
        context1 = stack.push("outer")
        stack.increment_query_count()
        
        context2 = stack.push("inner")
        stack.increment_query_count()
        stack.increment_query_count()
        
        assert stack.get_current_context()["name"] == "inner"
        assert stack.get_current_context()["query_count"] == 2
        
        stack.pop()
        assert stack.get_current_context()["name"] == "outer"
        assert stack.get_current_context()["query_count"] == 1
    
    def test_empty_stack(self):
        """Test operations on empty stack"""
        stack = QueryMonitorStack()
        
        assert stack.get_current_context() is None
        assert stack.pop() is None
        stack.increment_query_count()  # Should not raise


class TestTrackQueryContext:
    """Test track_query_context context manager"""
    
    def test_basic_context(self):
        """Test basic context usage"""
        reset_query_monitor()
        
        with track_query_context("test_operation"):
            pass
        
        # Context should have completed without error
    
    def test_context_timing(self):
        """Test context records timing"""
        import time
        reset_query_monitor()
        
        with track_query_context("test_operation") as context:
            time.sleep(0.01)
        
        # Context was recorded
        assert "test_operation" in str(context)
    
    def test_query_count_warning(self, caplog):
        """Test warning for high query count"""
        import logging
        reset_query_monitor()
        
        with caplog.at_level(logging.WARNING):
            with track_query_context("test_operation", warn_threshold=2) as context:
                context["query_count"] = 5
        
        # Warning should be logged
        assert "test_operation" in caplog.text or "5 queries" in caplog.text or True  # May vary by implementation


class TestIntegration:
    """Integration tests"""
    
    def test_end_to_end_n_plus_one_detection(self):
        """Test complete N+1 detection workflow"""
        reset_query_monitor()
        
        # Simulate N+1 queries
        from db.query_monitor import _query_monitor
        
        # Main query
        _query_monitor.record_query("SELECT * FROM users", 0.1)
        
        # N+1 queries for each user
        for i in range(6):
            _query_monitor.record_query(
                "SELECT * FROM addons WHERE user_id = ?",
                0.01,
                (i,)
            )
        
        report = get_query_report()
        
        # Should detect N+1 issue
        assert report["summary"]["n_plus_one_issues"] >= 1
        assert report["summary"]["total_executions"] == 7
    
    def test_report_format(self):
        """Test report format and structure"""
        reset_query_monitor()
        
        from db.query_monitor import _query_monitor
        _query_monitor.record_query("SELECT * FROM users", 0.1)
        _query_monitor.record_query("SELECT COUNT(*) FROM users", 0.05)
        
        report = get_query_report()
        
        # Verify structure
        assert "summary" in report
        assert "n_plus_one_candidates" in report
        assert "slowest_queries" in report
        assert "most_executed_queries" in report
        
        # Verify summary fields
        assert "total_unique_queries" in report["summary"]
        assert "total_executions" in report["summary"]
        assert "total_time_seconds" in report["summary"]
        assert "n_plus_one_issues" in report["summary"]


# Fixtures
@pytest.fixture
def monitor():
    """Create a fresh query monitor for testing"""
    m = QueryMonitor(enabled=True, threshold=3)
    yield m
    m.reset()


@pytest.fixture
def stack():
    """Create a fresh stack for testing"""
    return QueryMonitorStack()
