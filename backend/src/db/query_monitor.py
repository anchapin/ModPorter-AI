"""
N+1 Query Detection and Monitoring Module

This module provides tools to detect and prevent N+1 query problems in the database layer.
It monitors SQL execution, detects query patterns, and provides reporting for performance
optimization.

Features:
- Detects N+1 query patterns (same query executed multiple times)
- Tracks query execution metrics (count, time, parameters)
- Provides warnings and logging for potential performance issues
- Integrates with SQLAlchemy event system
"""

import logging
import time
import threading
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, field
from functools import wraps
from contextlib import contextmanager

from sqlalchemy import event
from sqlalchemy.engine import Engine

logger = logging.getLogger(__name__)


@dataclass
class QueryMetrics:
    """Metrics for a single query pattern"""
    sql_pattern: str
    count: int = 0
    total_time: float = 0.0
    min_time: float = float('inf')
    max_time: float = 0.0
    parameters: List[Tuple] = field(default_factory=list)
    
    def add_execution(self, execution_time: float, params: Optional[Tuple] = None):
        """Record a query execution"""
        self.count += 1
        self.total_time += execution_time
        self.min_time = min(self.min_time, execution_time)
        self.max_time = max(self.max_time, execution_time)
        if params:
            self.parameters.append(params)
    
    @property
    def avg_time(self) -> float:
        """Calculate average execution time"""
        return self.total_time / self.count if self.count > 0 else 0.0
    
    def is_potential_n_plus_one(self, threshold: int = 5) -> bool:
        """Check if this query matches N+1 pattern (executed multiple times with different params)"""
        return self.count > threshold and len(set(self.parameters)) > 1


class QueryMonitor:
    """Monitor and detect N+1 queries in database operations"""
    
    def __init__(self, enabled: bool = True, threshold: int = 5):
        """
        Initialize query monitor
        
        Args:
            enabled: Whether monitoring is active
            threshold: Number of executions to trigger N+1 warning
        """
        self.enabled = enabled
        self.threshold = threshold
        self.queries: Dict[str, QueryMetrics] = {}
        self.lock = threading.RLock()
        self._stack: List[Dict] = []
    
    def normalize_query(self, sql: str) -> str:
        """
        Normalize SQL query for pattern matching
        
        Removes values from WHERE clauses, IN clauses, etc. to group similar queries.

        Example:
            SELECT * FROM users WHERE id = 123
            SELECT * FROM users WHERE id = 456
        Both normalize to: SELECT * FROM users WHERE id = ?
        """
        import re
        # Replace numeric literals with ?
        normalized = re.sub(r'\d+', '?', sql)
        # Replace string literals with ?
        normalized = re.sub(r"'[^']*'", '?', normalized)
        # Replace UUID patterns with ?
        normalized = re.sub(
            r"'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}'",
            '?',
            normalized,
            flags=re.IGNORECASE
        )
        # Normalize whitespace
        normalized = ' '.join(normalized.split())
        return normalized
    
    def record_query(self, sql: str, execution_time: float, params: Optional[Tuple] = None):
        """Record a query execution"""
        if not self.enabled:
            return
        
        normalized = self.normalize_query(sql)
        
        with self.lock:
            if normalized not in self.queries:
                self.queries[normalized] = QueryMetrics(sql_pattern=normalized)
            
            self.queries[normalized].add_execution(execution_time, params)
            
            # Check for N+1 pattern
            metrics = self.queries[normalized]
            if metrics.is_potential_n_plus_one(self.threshold):
                logger.warning(
                    f"Potential N+1 query detected: {normalized} "
                    f"(executed {metrics.count} times, total: {metrics.total_time:.2f}s)"
                )
    
    def get_n_plus_one_candidates(self) -> List[Tuple[str, QueryMetrics]]:
        """Get list of potential N+1 queries"""
        with self.lock:
            return [
                (sql, metrics)
                for sql, metrics in self.queries.items()
                if metrics.is_potential_n_plus_one(self.threshold)
            ]
    
    def get_slowest_queries(self, limit: int = 10) -> List[Tuple[str, QueryMetrics]]:
        """Get slowest queries by total time"""
        with self.lock:
            sorted_queries = sorted(
                self.queries.items(),
                key=lambda x: x[1].total_time,
                reverse=True
            )
            return sorted_queries[:limit]
    
    def get_most_executed_queries(self, limit: int = 10) -> List[Tuple[str, QueryMetrics]]:
        """Get most frequently executed queries"""
        with self.lock:
            sorted_queries = sorted(
                self.queries.items(),
                key=lambda x: x[1].count,
                reverse=True
            )
            return sorted_queries[:limit]
    
    def reset(self):
        """Clear all recorded metrics"""
        with self.lock:
            self.queries.clear()
            self._stack.clear()
    
    def get_report(self) -> Dict:
        """Generate a comprehensive query performance report"""
        with self.lock:
            n_plus_one = self.get_n_plus_one_candidates()
            slowest = self.get_slowest_queries(10)
            most_executed = self.get_most_executed_queries(10)
            
            total_queries = len(self.queries)
            total_executions = sum(m.count for m in self.queries.values())
            total_time = sum(m.total_time for m in self.queries.values())
            
            return {
                "summary": {
                    "total_unique_queries": total_queries,
                    "total_executions": total_executions,
                    "total_time_seconds": total_time,
                    "n_plus_one_issues": len(n_plus_one),
                },
                "n_plus_one_candidates": [
                    {
                        "query": sql,
                        "execution_count": metrics.count,
                        "total_time": metrics.total_time,
                        "avg_time": metrics.avg_time,
                    }
                    for sql, metrics in n_plus_one
                ],
                "slowest_queries": [
                    {
                        "query": sql,
                        "execution_count": metrics.count,
                        "total_time": metrics.total_time,
                        "avg_time": metrics.avg_time,
                        "min_time": metrics.min_time,
                        "max_time": metrics.max_time,
                    }
                    for sql, metrics in slowest
                ],
                "most_executed_queries": [
                    {
                        "query": sql,
                        "execution_count": metrics.count,
                        "total_time": metrics.total_time,
                        "avg_time": metrics.avg_time,
                    }
                    for sql, metrics in most_executed
                ],
            }


class QueryMonitorStack:
    """Thread-local context for tracking nested query operations"""
    
    def __init__(self):
        self.stack = threading.local()
    
    def push(self, name: str) -> Dict:
        """Push a context onto the stack"""
        if not hasattr(self.stack, 'contexts'):
            self.stack.contexts = []
        
        context = {
            'name': name,
            'start_time': time.time(),
            'query_count': 0,
        }
        self.stack.contexts.append(context)
        return context
    
    def pop(self) -> Optional[Dict]:
        """Pop a context from the stack"""
        if hasattr(self.stack, 'contexts') and self.stack.contexts:
            return self.stack.contexts.pop()
        return None
    
    def increment_query_count(self):
        """Increment query count for current context"""
        if hasattr(self.stack, 'contexts') and self.stack.contexts:
            self.stack.contexts[-1]['query_count'] += 1
    
    def get_current_context(self) -> Optional[Dict]:
        """Get current (topmost) context"""
        if hasattr(self.stack, 'contexts') and self.stack.contexts:
            return self.stack.contexts[-1]
        return None


# Global instances
_query_monitor = QueryMonitor()
_query_stack = QueryMonitorStack()


def setup_query_monitoring(engine: Engine, enabled: bool = True):
    """
    Setup SQLAlchemy event listeners for query monitoring
    
    Args:
        engine: SQLAlchemy engine to monitor
        enabled: Whether to enable monitoring
    """
    _query_monitor.enabled = enabled
    
    @event.listens_for(engine, "before_cursor_execute")
    def receive_before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
        """Track query start time"""
        context._query_start_time = time.time()
    
    @event.listens_for(engine, "after_cursor_execute")
    def receive_after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
        """Record query metrics"""
        if not hasattr(context, '_query_start_time'):
            return
        
        execution_time = time.time() - context._query_start_time
        _query_monitor.record_query(statement, execution_time, tuple(parameters) if parameters else None)
        _query_stack.increment_query_count()


@contextmanager
def track_query_context(name: str, warn_threshold: int = 10):
    """
    Context manager to track queries within a specific operation
    
    Usage:
        with track_query_context("load_users_with_addons"):
            # ... your code that performs queries
    
    Args:
        name: Name of the operation being tracked
        warn_threshold: Number of queries to trigger a warning
    """
    context = _query_stack.push(name)
    try:
        yield context
    finally:
        elapsed = time.time() - context['start_time']
        query_count = context['query_count']
        
        if query_count > warn_threshold:
            logger.warning(
                f"Operation '{name}' executed {query_count} queries in {elapsed:.2f}s "
                f"(warn threshold: {warn_threshold})"
            )
        else:
            logger.debug(
                f"Operation '{name}' executed {query_count} queries in {elapsed:.2f}s"
            )
        
        _query_stack.pop()


def track_queries(warn_threshold: int = 10):
    """
    Decorator to track queries for a function
    
    Usage:
        @track_queries(warn_threshold=5)
        async def load_users():
            # ... function code
    """
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            with track_query_context(func.__name__, warn_threshold):
                return await func(*args, **kwargs)
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            with track_query_context(func.__name__, warn_threshold):
                return func(*args, **kwargs)
        
        if asyncio_iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
    
    return decorator


def asyncio_iscoroutinefunction(func):
    """Check if function is async"""
    import inspect
    return inspect.iscoroutinefunction(func)


def get_query_report() -> Dict:
    """Get current query monitoring report"""
    return _query_monitor.get_report()


def reset_query_monitor():
    """Reset query monitoring data"""
    _query_monitor.reset()


def enable_query_monitoring():
    """Enable query monitoring"""
    _query_monitor.enabled = True


def disable_query_monitoring():
    """Disable query monitoring"""
    _query_monitor.enabled = False
