"""
Unit tests for query monitoring module.
"""

import pytest
from unittest.mock import MagicMock, patch
from src.db.query_monitor import (
    QueryMonitor,
    QueryMetrics,
    QueryMonitorStack,
    setup_query_monitoring,
    track_query_context,
    track_queries,
    get_query_report,
    reset_query_monitor,
    enable_query_monitoring,
    disable_query_monitoring,
)


class TestQueryMetrics:
    """Test cases for QueryMetrics dataclass."""

    def test_initialization(self):
        """Test QueryMetrics initialization."""
        metrics = QueryMetrics(sql_pattern="SELECT * FROM users")
        
        assert metrics.sql_pattern == "SELECT * FROM users"
        assert metrics.count == 0
        assert metrics.total_time == 0.0
        assert metrics.min_time == float("inf")
        assert metrics.max_time == 0.0

    def test_add_execution(self):
        """Test recording query execution."""
        metrics = QueryMetrics(sql_pattern="SELECT * FROM users")
        
        metrics.add_execution(0.5, (1,))
        metrics.add_execution(0.3, (2,))
        
        assert metrics.count == 2
        assert metrics.total_time == 0.8
        assert metrics.min_time == 0.3
        assert metrics.max_time == 0.5

    def test_avg_time(self):
        """Test average time calculation."""
        metrics = QueryMetrics(sql_pattern="SELECT * FROM users")
        
        metrics.add_execution(0.5)
        metrics.add_execution(1.5)
        
        assert metrics.avg_time == 1.0

    def test_avg_time_zero_count(self):
        """Test average time with zero count."""
        metrics = QueryMetrics(sql_pattern="SELECT * FROM users")
        
        assert metrics.avg_time == 0.0

    def test_is_potential_n_plus_one(self):
        """Test N+1 detection."""
        metrics = QueryMetrics(sql_pattern="SELECT * FROM users WHERE id = ?")
        
        # Add multiple executions with different parameters
        for i in range(6):
            metrics.add_execution(0.1, (i,))
        
        assert metrics.is_potential_n_plus_one(threshold=5) is True
        assert metrics.is_potential_n_plus_one(threshold=10) is False

    def test_is_potential_n_plus_one_same_params(self):
        """Test N+1 detection with same parameters."""
        metrics = QueryMetrics(sql_pattern="SELECT * FROM users")
        
        # Add multiple executions with same parameters
        for _ in range(6):
            metrics.add_execution(0.1, (1,))
        
        assert metrics.is_potential_n_plus_one(threshold=5) is False


class TestQueryMonitor:
    """Test cases for QueryMonitor class."""

    @pytest.fixture
    def monitor(self):
        """Create a fresh QueryMonitor instance."""
        return QueryMonitor(enabled=True, threshold=3)

    def test_initialization(self, monitor):
        """Test QueryMonitor initialization."""
        assert monitor.enabled is True
        assert monitor.threshold == 3
        assert monitor.queries == {}

    def test_normalize_query(self, monitor):
        """Test SQL normalization."""
        # Test numeric literals
        sql = "SELECT * FROM users WHERE id = 123"
        normalized = monitor.normalize_query(sql)
        assert "123" not in normalized
        assert "?" in normalized

    def test_normalize_query_strings(self, monitor):
        """Test SQL string normalization."""
        sql = "SELECT * FROM users WHERE name = 'John'"
        normalized = monitor.normalize_query(sql)
        assert "'John'" not in normalized

    def test_normalize_query_uuid(self, monitor):
        """Test SQL UUID normalization."""
        sql = "SELECT * FROM users WHERE id = '12345678-1234-1234-1234-123456789012'"
        normalized = monitor.normalize_query(sql)
        assert "12345678" not in normalized

    def test_record_query(self, monitor):
        """Test recording a query."""
        monitor.record_query("SELECT * FROM users", 0.5, (1,))
        
        assert len(monitor.queries) == 1

    def test_record_query_disabled(self, monitor):
        """Test recording when disabled."""
        monitor.enabled = False
        monitor.record_query("SELECT * FROM users", 0.5, (1,))
        
        assert len(monitor.queries) == 0

    def test_get_n_plus_one_candidates(self, monitor):
        """Test getting N+1 candidates."""
        # Add queries that would trigger N+1 detection
        for i in range(5):
            monitor.record_query("SELECT * FROM users WHERE id = ?", 0.1, (i,))
        
        candidates = monitor.get_n_plus_one_candidates()
        assert len(candidates) == 1

    def test_get_slowest_queries(self, monitor):
        """Test getting slowest queries."""
        monitor.record_query("SELECT * FROM slow", 2.0, (1,))
        monitor.record_query("SELECT * FROM fast", 0.1, (1,))
        
        slowest = monitor.get_slowest_queries(limit=1)
        assert len(slowest) == 1
        assert "slow" in slowest[0][0]

    def test_get_most_executed_queries(self, monitor):
        """Test getting most executed queries."""
        for _ in range(5):
            monitor.record_query("SELECT * FROM frequent", 0.1, (1,))
        for _ in range(2):
            monitor.record_query("SELECT * FROM rare", 0.1, (1,))
        
        most_executed = monitor.get_most_executed_queries(limit=1)
        assert len(most_executed) == 1
        assert "frequent" in most_executed[0][0]

    def test_reset(self, monitor):
        """Test resetting monitor."""
        monitor.record_query("SELECT * FROM users", 0.5, (1,))
        
        monitor.reset()
        
        assert len(monitor.queries) == 0

    def test_get_report(self, monitor):
        """Test getting query report."""
        monitor.record_query("SELECT * FROM users", 0.5, (1,))
        monitor.record_query("SELECT * FROM users", 0.3, (2,))
        
        report = monitor.get_report()
        
        assert "summary" in report
        assert "n_plus_one_candidates" in report
        assert "slowest_queries" in report
        assert "most_executed_queries" in report
        assert report["summary"]["total_unique_queries"] == 1
        assert report["summary"]["total_executions"] == 2


class TestQueryMonitorStack:
    """Test cases for QueryMonitorStack class."""

    @pytest.fixture
    def stack(self):
        """Create a fresh QueryMonitorStack instance."""
        return QueryMonitorStack()

    def test_push(self, stack):
        """Test pushing context to stack."""
        context = stack.push("test_operation")
        
        assert context["name"] == "test_operation"
        assert "start_time" in context
        assert context["query_count"] == 0

    def test_pop(self, stack):
        """Test popping context from stack."""
        stack.push("test_operation")
        
        popped = stack.pop()
        
        assert popped["name"] == "test_operation"

    def test_increment_query_count(self, stack):
        """Test incrementing query count."""
        stack.push("test_operation")
        
        stack.increment_query_count()
        stack.increment_query_count()
        
        current = stack.get_current_context()
        assert current["query_count"] == 2

    def test_get_current_context(self, stack):
        """Test getting current context."""
        stack.push("first")
        stack.push("second")
        
        current = stack.get_current_context()
        
        assert current["name"] == "second"

    def test_get_current_context_empty(self, stack):
        """Test getting current context when empty."""
        current = stack.get_current_context()
        
        assert current is None


class TestTrackQueryContext:
    """Test cases for track_query_context context manager."""

    def test_track_queries(self):
        """Test tracking queries with context manager."""
        with track_query_context("test_operation", warn_threshold=1) as context:
            # Simulate queries
            pass

    def test_track_queries_above_threshold(self, caplog):
        """Test logging when query count exceeds threshold."""
        with patch('src.db.query_monitor._query_stack') as mock_stack:
            mock_context = {
                "name": "test",
                "start_time": 0,
                "query_count": 15
            }
            mock_stack.push.return_value = mock_context
            mock_stack.pop.return_value = None
            
            with track_query_context("test", warn_threshold=10):
                pass
            
            # The warning should be logged when query_count > warn_threshold


class TestTrackQueriesDecorator:
    """Test cases for track_queries decorator."""

    def test_sync_function_decorator(self):
        """Test decorating a sync function."""
        @track_queries(warn_threshold=5)
        def sync_function():
            return "result"
        
        result = sync_function()
        assert result == "result"

    def test_async_function_decorator(self):
        """Test decorating an async function."""
        @track_queries(warn_threshold=5)
        async def async_function():
            return "result"
        
        # The decorator should return an async function
        import inspect
        assert inspect.iscoroutinefunction(async_function)


class TestModuleFunctions:
    """Test cases for module-level functions."""

    def test_get_query_report(self):
        """Test getting query report."""
        reset_query_monitor()
        
        report = get_query_report()
        
        assert "summary" in report

    def test_enable_disable_monitoring(self):
        """Test enabling and disabling monitoring."""
        disable_query_monitoring()
        
        from src.db.query_monitor import _query_monitor
        assert _query_monitor.enabled is False
        
        enable_query_monitoring()
        assert _query_monitor.enabled is True