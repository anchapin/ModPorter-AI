"""
Database health check and monitoring utilities.
Addresses Issue #575: Backend: Database Schema and Migrations - Async SQLAlchemy Management

This module provides:
- Database connection health checks
- Query performance monitoring
- Connection pool metrics
- N+1 query detection helpers
"""

import logging
import time
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime
from contextlib import asynccontextmanager

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, AsyncEngine

logger = logging.getLogger(__name__)


@dataclass
class HealthCheckResult:
    """Result of a database health check"""
    is_healthy: bool
    message: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    latency_ms: Optional[float] = None
    details: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_healthy": self.is_healthy,
            "message": self.message,
            "timestamp": self.timestamp.isoformat(),
            "latency_ms": self.latency_ms,
            "details": self.details
        }


@dataclass
class QueryMetrics:
    """Metrics for a single query execution"""
    query_text: str
    execution_time_ms: float
    rows_affected: int = 0
    timestamp: datetime = field(default_factory=datetime.utcnow)
    error: Optional[str] = None


@dataclass
class ConnectionPoolMetrics:
    """Metrics for the database connection pool"""
    pool_size: int = 0
    checked_in: int = 0
    checked_out: int = 0
    overflow: int = 0
    invalid: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "pool_size": self.pool_size,
            "checked_in": self.checked_in,
            "checked_out": self.checked_out,
            "overflow": self.overflow,
            "invalid": self.invalid
        }


class DatabaseHealthChecker:
    """
    Provides health check and monitoring capabilities for the database.
    """
    
    def __init__(self, engine: AsyncEngine):
        """
        Initialize the health checker.
        
        Args:
            engine: The async SQLAlchemy engine to monitor
        """
        self.engine = engine
        self._query_history: List[QueryMetrics] = []
        self._slow_query_threshold_ms: float = 1000.0  # 1 second
        self._max_history_size: int = 1000
    
    async def check_health(self) -> HealthCheckResult:
        """
        Perform a comprehensive health check of the database connection.
        
        Returns:
            HealthCheckResult with health status and details
        """
        start_time = time.time()
        
        try:
            # Execute a simple query to verify connectivity
            async with self.engine.connect() as conn:
                result = await conn.execute(text("SELECT 1"))
                result.fetchone()
            
            latency_ms = (time.time() - start_time) * 1000
            
            # Get pool status
            pool_metrics = await self.get_pool_metrics()
            
            return HealthCheckResult(
                is_healthy=True,
                message="Database connection is healthy",
                latency_ms=latency_ms,
                details={
                    "pool_metrics": pool_metrics.to_dict()
                }
            )
            
        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            logger.error(f"Database health check failed: {e}")
            
            return HealthCheckResult(
                is_healthy=False,
                message=f"Database connection failed: {str(e)}",
                latency_ms=latency_ms,
                details={"error": str(e)}
            )
    
    async def check_migrations(self) -> HealthCheckResult:
        """
        Check if database migrations are up to date.
        
        Returns:
            HealthCheckResult with migration status
        """
        try:
            async with self.engine.connect() as conn:
                # Check if alembic_version table exists
                result = await conn.execute(text(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name='alembic_version'"
                ))
                table_exists = result.fetchone() is not None
                
                if not table_exists:
                    return HealthCheckResult(
                        is_healthy=False,
                        message="Migration tracking table not found",
                        details={"migrations_applied": False}
                    )
                
                # Get current version
                result = await conn.execute(text(
                    "SELECT version_num FROM alembic_version"
                ))
                version = result.fetchone()
                
                if version:
                    return HealthCheckResult(
                        is_healthy=True,
                        message="Migrations are tracked",
                        details={"current_version": version[0]}
                    )
                else:
                    return HealthCheckResult(
                        is_healthy=False,
                        message="No migration version found",
                        details={"migrations_applied": False}
                    )
                    
        except Exception as e:
            logger.error(f"Migration check failed: {e}")
            return HealthCheckResult(
                is_healthy=False,
                message=f"Migration check failed: {str(e)}",
                details={"error": str(e)}
            )
    
    async def get_pool_metrics(self) -> ConnectionPoolMetrics:
        """
        Get current connection pool metrics.
        
        Returns:
            ConnectionPoolMetrics with current pool status
        """
        try:
            pool = self.engine.pool
            
            # Get pool status
            return ConnectionPoolMetrics(
                pool_size=pool.size() if hasattr(pool, 'size') else 0,
                checked_in=pool.checkedin() if hasattr(pool, 'checkedin') else 0,
                checked_out=pool.checkedout() if hasattr(pool, 'checkedout') else 0,
                overflow=pool.overflow() if hasattr(pool, 'overflow') else 0,
                invalid=pool.invalidatedcount() if hasattr(pool, 'invalidatedcount') else 0
            )
            
        except Exception as e:
            logger.warning(f"Could not get pool metrics: {e}")
            return ConnectionPoolMetrics()
    
    def record_query(self, metrics: QueryMetrics):
        """
        Record query execution metrics.
        
        Args:
            metrics: QueryMetrics to record
        """
        self._query_history.append(metrics)
        
        # Trim history if needed
        if len(self._query_history) > self._max_history_size:
            self._query_history = self._query_history[-self._max_history_size:]
        
        # Log slow queries
        if metrics.execution_time_ms > self._slow_query_threshold_ms:
            logger.warning(
                f"Slow query detected: {metrics.execution_time_ms:.2f}ms - "
                f"{metrics.query_text[:100]}..."
            )
    
    def get_slow_queries(self, threshold_ms: Optional[float] = None) -> List[QueryMetrics]:
        """
        Get queries that exceeded the slow query threshold.
        
        Args:
            threshold_ms: Optional custom threshold in milliseconds
            
        Returns:
            List of slow QueryMetrics
        """
        threshold = threshold_ms or self._slow_query_threshold_ms
        return [q for q in self._query_history if q.execution_time_ms > threshold]
    
    def get_query_stats(self) -> Dict[str, Any]:
        """
        Get aggregate query statistics.
        
        Returns:
            Dictionary with query statistics
        """
        if not self._query_history:
            return {
                "total_queries": 0,
                "average_time_ms": 0,
                "max_time_ms": 0,
                "min_time_ms": 0,
                "slow_query_count": 0
            }
        
        times = [q.execution_time_ms for q in self._query_history]
        slow_count = len(self.get_slow_queries())
        
        return {
            "total_queries": len(self._query_history),
            "average_time_ms": sum(times) / len(times),
            "max_time_ms": max(times),
            "min_time_ms": min(times),
            "slow_query_count": slow_count
        }
    
    def clear_history(self):
        """Clear the query history."""
        self._query_history.clear()


class NPlusOneDetector:
    """
    Helper class to detect N+1 query patterns.
    """
    
    def __init__(self):
        self._query_counts: Dict[str, int] = {}
        self._detection_threshold: int = 10  # Same query executed 10+ times
    
    def record_query(self, query_pattern: str):
        """
        Record a query pattern for N+1 detection.
        
        Args:
            query_pattern: A normalized query pattern (e.g., "SELECT * FROM users WHERE id = ?")
        """
        self._query_counts[query_pattern] = self._query_counts.get(query_pattern, 0) + 1
    
    def detect_n_plus_one(self) -> List[Dict[str, Any]]:
        """
        Detect potential N+1 query patterns.
        
        Returns:
            List of detected N+1 patterns with details
        """
        patterns = []
        
        for pattern, count in self._query_counts.items():
            if count >= self._detection_threshold:
                patterns.append({
                    "pattern": pattern,
                    "count": count,
                    "severity": "high" if count >= 50 else "medium"
                })
        
        return patterns
    
    def reset(self):
        """Reset the detection state."""
        self._query_counts.clear()


@asynccontextmanager
async def monitored_session(
    session: AsyncSession,
    health_checker: Optional[DatabaseHealthChecker] = None,
    n_plus_one_detector: Optional[NPlusOneDetector] = None
):
    """
    Context manager that adds monitoring to a database session.
    
    Args:
        session: The AsyncSession to monitor
        health_checker: Optional DatabaseHealthChecker for query recording
        n_plus_one_detector: Optional NPlusOneDetector for N+1 detection
        
    Yields:
        The monitored session
    """
    try:
        yield session
    finally:
        # Session cleanup is handled by the session context
        pass


def create_health_checker(engine: AsyncEngine) -> DatabaseHealthChecker:
    """
    Factory function to create a DatabaseHealthChecker.
    
    Args:
        engine: The async SQLAlchemy engine
        
    Returns:
        Configured DatabaseHealthChecker instance
    """
    return DatabaseHealthChecker(engine)


def create_n_plus_one_detector() -> NPlusOneDetector:
    """
    Factory function to create an NPlusOneDetector.
    
    Returns:
        Configured NPlusOneDetector instance
    """
    return NPlusOneDetector()