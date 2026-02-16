"""
Metrics Service for ModPorter AI
Provides Prometheus metrics for monitoring conversion success rates, performance, and API costs.

Issue: #384 - Monitoring dashboards with Grafana/Prometheus (Phase 3)
"""

from prometheus_client import Counter, Histogram, Gauge, CollectorRegistry, generate_latest
from typing import Optional
import time
from datetime import datetime
from collections import defaultdict
import threading


# Create a custom registry
registry = CollectorRegistry()

# ============================================
# API Metrics
# ============================================

# Request counter by endpoint and status
http_requests_total = Counter(
    'modporter_http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status'],
    registry=registry
)

# Request duration histogram
http_request_duration_seconds = Histogram(
    'modporter_http_request_duration_seconds',
    'HTTP request duration in seconds',
    ['method', 'endpoint'],
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
    registry=registry
)

# ============================================
# Conversion Metrics
# ============================================

# Conversion job counter by status
conversion_jobs_total = Counter(
    'modporter_conversion_jobs_total',
    'Total conversion jobs',
    ['status', 'target_version'],
    registry=registry
)

# Conversion duration histogram
conversion_duration_seconds = Histogram(
    'modporter_conversion_duration_seconds',
    'Conversion duration in seconds',
    ['target_version'],
    buckets=[10, 30, 60, 120, 300, 600, 900, 1800],
    registry=registry
)

# Current conversion queue size
conversion_queue_size = Gauge(
    'modporter_conversion_queue_size',
    'Current number of conversion jobs in queue',
    registry=registry
)

# Active conversions gauge
active_conversions = Gauge(
    'modporter_active_conversions',
    'Number of currently active conversion jobs',
    registry=registry
)

# ============================================
# Agent Metrics
# ============================================

# Agent execution counter
agent_executions_total = Counter(
    'modporter_agent_executions_total',
    'Total agent executions',
    ['agent_name', 'status'],
    registry=registry
)

# Agent execution duration
agent_duration_seconds = Histogram(
    'modporter_agent_duration_seconds',
    'Agent execution duration in seconds',
    ['agent_name'],
    buckets=[1, 5, 10, 30, 60, 120, 300],
    registry=registry
)

# ============================================
# Token/ Cost Metrics
# ============================================

# LLM token usage
llm_tokens_total = Counter(
    'modporter_llm_tokens_total',
    'Total LLM tokens used',
    ['model', 'prompt_completion'],
    registry=registry
)

# LLM API cost in dollars
llm_cost_dollars = Counter(
    'modporter_llm_cost_dollars',
    'Total LLM API cost in dollars',
    ['model'],
    registry=registry
)

# ============================================
# Asset Metrics
# ============================================

# Assets processed counter
assets_processed_total = Counter(
    'modporter_assets_processed_total',
    'Total assets processed',
    ['asset_type', 'status'],
    registry=registry
)

# Asset conversion duration
asset_conversion_duration_seconds = Histogram(
    'modporter_asset_conversion_duration_seconds',
    'Asset conversion duration in seconds',
    ['asset_type'],
    buckets=[0.1, 0.5, 1.0, 5.0, 10.0, 30.0, 60.0],
    registry=registry
)

# ============================================
# Database Metrics
# ============================================

# Database operation duration
db_operation_duration_seconds = Histogram(
    'modporter_db_operation_duration_seconds',
    'Database operation duration in seconds',
    ['operation', 'table'],
    buckets=[0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0],
    registry=registry
)

# ============================================
# Cache Metrics
# ============================================

# Cache hit/miss counter
cache_operations_total = Counter(
    'modporter_cache_operations_total',
    'Total cache operations',
    ['operation', 'cache_name'],
    registry=registry
)

# ============================================
# Business Metrics
# ============================================

# Conversion success rate (gauge for dashboard)
conversion_success_rate = Gauge(
    'modporter_conversion_success_rate',
    'Current conversion success rate (percentage)',
    registry=registry
)

# Average conversion time (gauge)
average_conversion_time_seconds = Gauge(
    'modporter_average_conversion_time_seconds',
    'Average conversion time in seconds',
    registry=registry
)

# Total conversions completed
conversions_completed_total = Gauge(
    'modporter_conversions_completed_total',
    'Total number of successful conversions',
    registry=registry
)

# Total conversions failed
conversions_failed_total = Gauge(
    'modporter_conversions_failed_total',
    'Total number of failed conversions',
    registry=registry
)


# ============================================
# Internal Tracking (thread-safe)
# ============================================

class MetricsTracker:
    """Thread-safe metrics tracker for calculating rates."""
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._conversion_times = defaultdict(list)
        self._success_count = 0
        self._failure_count = 0
        self._lock = threading.Lock()
        self._initialized = True
    
    def record_conversion(self, duration_seconds: float, success: bool, target_version: str):
        """Record a conversion for metrics tracking."""
        with self._lock:
            if success:
                self._success_count += 1
            else:
                self._failure_count += 1
            
            # Keep only last 1000 conversion times
            self._conversion_times[target_version].append(duration_seconds)
            if len(self._conversion_times[target_version]) > 1000:
                self._conversion_times[target_version] = self._conversion_times[target_version][-1000:]
            
            # Update gauge metrics
            total = self._success_count + self._failure_count
            if total > 0:
                rate = (self._success_count / total) * 100
                conversion_success_rate.set(rate)
            
            # Calculate average conversion time
            all_times = []
            for times in self._conversion_times.values():
                all_times.extend(times)
            if all_times:
                avg_time = sum(all_times) / len(all_times)
                average_conversion_time_seconds.set(avg_time)
            
            # Update total counts
            conversions_completed_total.set(self._success_count)
            conversions_failed_total.set(self._failure_count)
    
    def get_stats(self):
        """Get current statistics."""
        with self._lock:
            total = self._success_count + self._failure_count
            return {
                'success_count': self._success_count,
                'failure_count': self._failure_count,
                'total': total,
                'success_rate': (self._success_count / total * 100) if total > 0 else 0,
                'average_time': sum(sum(times) for times in self._conversion_times.values()) / 
                               sum(len(times) for times in self._conversion_times.values()) if 
                               sum(len(times) for times in self._conversion_times.values()) > 0 else 0
            }


# Global metrics tracker instance
metrics_tracker = MetricsTracker()


# ============================================
# Helper Functions
# ============================================

def record_http_request(method: str, endpoint: str, status: int, duration: float):
    """Record an HTTP request metric."""
    http_requests_total.labels(method=method, endpoint=endpoint, status=str(status)).inc()
    http_request_duration_seconds.labels(method=method, endpoint=endpoint).observe(duration)


def record_conversion_job(status: str, target_version: str = "1.20.0", duration: Optional[float] = None):
    """Record a conversion job metric."""
    conversion_jobs_total.labels(status=status, target_version=target_version).inc()
    
    if duration is not None:
        conversion_duration_seconds.labels(target_version=target_version).observe(duration)
        metrics_tracker.record_conversion(duration, status == "completed", target_version)


def record_agent_execution(agent_name: str, status: str, duration: Optional[float] = None):
    """Record an agent execution metric."""
    agent_executions_total.labels(agent_name=agent_name, status=status).inc()
    
    if duration is not None:
        agent_duration_seconds.labels(agent_name=agent_name).observe(duration)


def record_llm_usage(model: str, prompt_tokens: int, completion_tokens: int, cost: float):
    """Record LLM token usage and cost."""
    llm_tokens_total.labels(model=model, prompt_completion="prompt").inc(prompt_tokens)
    llm_tokens_total.labels(model=model, prompt_completion="completion").inc(completion_tokens)
    llm_cost_dollars.labels(model=model).inc(cost)


def record_asset_processed(asset_type: str, status: str, duration: Optional[float] = None):
    """Record an asset processed metric."""
    assets_processed_total.labels(asset_type=asset_type, status=status).inc()
    
    if duration is not None:
        asset_conversion_duration_seconds.labels(asset_type=asset_type).observe(duration)


def record_db_operation(operation: str, table: str, duration: float):
    """Record a database operation metric."""
    db_operation_duration_seconds.labels(operation=operation, table=table).observe(duration)


def record_cache_operation(operation: str, cache_name: str):
    """Record a cache operation metric."""
    cache_operations_total.labels(operation=operation, cache_name=cache_name).inc()


def update_queue_size(size: int):
    """Update the conversion queue size gauge."""
    conversion_queue_size.set(size)


def update_active_conversions(count: int):
    """Update the active conversions gauge."""
    active_conversions.set(count)


def get_metrics() -> bytes:
    """Get Prometheus metrics in text format."""
    return generate_latest(registry)


# ============================================
# Metrics Middleware for FastAPI
# ============================================

class MetricsMiddleware:
    """FastAPI middleware for recording HTTP metrics."""
    
    def __init__(self, app):
        self.app = app
    
    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        
        # Extract path and method
        method = scope.get("method", "UNKNOWN")
        path = scope.get("path", "/")
        
        # Start timer
        start_time = time.time()
        
        # Custom send to capture status code
        status_code = 200
        async def send_wrapper(message):
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message.get("status", 200)
            await send(message)
        
        await self.app(scope, receive, send_wrapper)
        
        # Calculate duration
        duration = time.time() - start_time
        
        # Normalize endpoint for grouping
        endpoint = self._normalize_endpoint(path)
        
        # Record metrics
        record_http_request(method, endpoint, status_code, duration)
    
    def _normalize_endpoint(self, path: str) -> str:
        """Normalize endpoint path for grouping."""
        # Convert UUIDs and IDs to placeholder
        import re
        # Replace UUIDs
        path = re.sub(r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}', '{id}', path)
        # Replace numeric IDs
        path = re.sub(r'/\d+', '/{id}', path)
        return path
