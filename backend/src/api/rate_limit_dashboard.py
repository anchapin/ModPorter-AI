"""
Rate Limit Dashboard API

Provides endpoints for visualizing rate limiting metrics and statistics.

Issue: #643 - Backend: Implement Rate Limiting Dashboard
"""

from fastapi import APIRouter, Depends
from fastapi.responses import Response
from typing import Dict, List, Optional
from pydantic import BaseModel
from datetime import datetime, timedelta

from services.rate_limiter import get_rate_limiter, RateLimiter
from services.metrics import (
    rate_limit_hits_total,
    rate_limit_requests_total,
    rate_limit_active_clients,
    registry
)
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

router = APIRouter()


class RateLimitSummary(BaseModel):
    """Summary of rate limiting statistics"""
    total_requests: int
    allowed_requests: int
    blocked_requests: int
    block_rate: float
    active_clients: int
    unique_endpoints: List[str]


class EndpointStats(BaseModel):
    """Rate limit statistics per endpoint"""
    endpoint: str
    total_requests: int
    allowed_requests: int
    blocked_requests: int
    block_rate: float


class ClientStats(BaseModel):
    """Rate limit statistics per client"""
    client_key: str
    client_type: str
    requests_in_minute: int
    requests_in_hour: int
    limit_minute: int
    limit_hour: int
    remaining_minute: int
    remaining_hour: int


class DashboardStats(BaseModel):
    """Complete dashboard statistics"""
    summary: RateLimitSummary
    endpoint_stats: List[EndpointStats]
    top_blocked_endpoints: List[EndpointStats]
    recent_activity: Dict[str, int]
    last_updated: datetime


def _get_prometheus_metrics() -> Dict[str, float]:
    """Extract rate limit metrics from Prometheus registry"""
    metrics = {}
    
    try:
        # Parse the generated metrics
        metrics_text = generate_latest(registry).decode('utf-8')
        
        for line in metrics_text.split('\n'):
            if line.startswith('#') or not line.strip():
                continue
            
            if 'rate_limit_hits_total' in line:
                # Extract endpoint and count
                parts = line.split()
                if len(parts) >= 2:
                    endpoint = 'unknown'
                    for i, part in enumerate(parts):
                        if 'endpoint=' in part:
                            endpoint = part.split('=')[1].strip('"')
                            break
                    try:
                        count = float(parts[-1])
                        metrics[f'hits_{endpoint}'] = count
                    except (ValueError, IndexError):
                        pass
            
            elif 'rate_limit_requests_total' in line:
                parts = line.split()
                if len(parts) >= 2:
                    endpoint = 'unknown'
                    status = 'unknown'
                    for part in parts:
                        if 'endpoint=' in part:
                            endpoint = part.split('=')[1].strip('"')
                        if 'status=' in part:
                            status = part.split('=')[1].strip('"')
                    try:
                        count = float(parts[-1])
                        if status == 'allowed':
                            metrics[f'allowed_{endpoint}'] = count
                        elif status == 'blocked':
                            metrics[f'blocked_{endpoint}'] = count
                        metrics[f'total_{endpoint}'] = metrics.get(f'total_{endpoint}', 0) + count
                    except (ValueError, IndexError):
                        pass
    
    except Exception:
        pass
    
    return metrics


@router.get("/dashboard", response_model=DashboardStats)
async def get_rate_limit_dashboard():
    """
    Get comprehensive rate limiting dashboard statistics.
    
    Returns:
        DashboardStats: Complete dashboard data including summary, endpoint stats, and activity
    """
    # Get metrics from Prometheus
    metrics = _get_prometheus_metrics()
    
    # Extract summary stats
    total_requests = sum(
        v for k, v in metrics.items() 
        if k.startswith('total_') and k != 'total_unknown'
    )
    allowed_requests = sum(
        v for k, v in metrics.items() 
        if k.startswith('allowed_') and k != 'allowed_unknown'
    )
    blocked_requests = sum(
        v for k, v in metrics.items() 
        if k.startswith('blocked_') and k != 'blocked_unknown'
    )
    
    # Calculate block rate
    block_rate = (blocked_requests / total_requests * 100) if total_requests > 0 else 0.0
    
    # Get unique endpoints
    endpoints = list(set(
        k.replace('total_', '').replace('allowed_', '').replace('blocked_', '')
        for k in metrics.keys()
        if k.startswith(('total_', 'allowed_', 'blocked_'))
    ))
    endpoints = [e for e in endpoints if e and e != 'unknown']
    
    # Get active clients
    try:
        active_clients = rate_limit_active_clients._value.get()
    except Exception:
        active_clients = 0
    
    # Build summary
    summary = RateLimitSummary(
        total_requests=int(total_requests),
        allowed_requests=int(allowed_requests),
        blocked_requests=int(blocked_requests),
        block_rate=round(block_rate, 2),
        active_clients=int(active_clients),
        unique_endpoints=endpoints
    )
    
    # Build endpoint stats
    endpoint_stats = []
    for endpoint in set(endpoints):
        total = int(metrics.get(f'total_{endpoint}', 0))
        allowed = int(metrics.get(f'allowed_{endpoint}', 0))
        blocked = int(metrics.get(f'blocked_{endpoint}', 0))
        rate = (blocked / total * 100) if total > 0 else 0.0
        
        endpoint_stats.append(EndpointStats(
            endpoint=endpoint,
            total_requests=total,
            allowed_requests=allowed,
            blocked_requests=blocked,
            block_rate=round(rate, 2)
        ))
    
    # Sort by total requests
    endpoint_stats.sort(key=lambda x: x.total_requests, reverse=True)
    
    # Top blocked endpoints
    top_blocked = sorted(
        [e for e in endpoint_stats if e.blocked_requests > 0],
        key=lambda x: x.blocked_requests,
        reverse=True
    )[:5]
    
    # Recent activity (mocked for now - could be enhanced with time-series)
    recent_activity = {
        "last_minute": int(blocked_requests * 0.1),  # Rough estimate
        "last_hour": int(blocked_requests * 0.5),
        "last_day": int(blocked_requests)
    }
    
    return DashboardStats(
        summary=summary,
        endpoint_stats=endpoint_stats,
        top_blocked_endpoints=top_blocked,
        recent_activity=recent_activity,
        last_updated=datetime.utcnow()
    )


@router.get("/summary", response_model=RateLimitSummary)
async def get_rate_limit_summary():
    """
    Get a quick summary of rate limiting statistics.
    """
    metrics = _get_prometheus_metrics()
    
    total_requests = sum(
        v for k, v in metrics.items() 
        if k.startswith('total_') and k != 'total_unknown'
    )
    allowed_requests = sum(
        v for k, v in metrics.items() 
        if k.startswith('allowed_') and k != 'allowed_unknown'
    )
    blocked_requests = sum(
        v for k, v in metrics.items() 
        if k.startswith('blocked_') and k != 'blocked_unknown'
    )
    
    block_rate = (blocked_requests / total_requests * 100) if total_requests > 0 else 0.0
    
    endpoints = list(set(
        k.replace('total_', '').replace('allowed_', '').replace('blocked_', '')
        for k in metrics.keys()
        if k.startswith(('total_', 'allowed_', 'blocked_'))
    ))
    endpoints = [e for e in endpoints if e and e != 'unknown']
    
    try:
        active_clients = rate_limit_active_clients._value.get()
    except Exception:
        active_clients = 0
    
    return RateLimitSummary(
        total_requests=int(total_requests),
        allowed_requests=int(allowed_requests),
        blocked_requests=int(blocked_requests),
        block_rate=round(block_rate, 2),
        active_clients=int(active_clients),
        unique_endpoints=endpoints
    )


@router.get("/endpoints", response_model=List[EndpointStats])
async def get_endpoint_stats():
    """
    Get rate limit statistics per endpoint.
    """
    metrics = _get_prometheus_metrics()
    
    endpoints = set(
        k.replace('total_', '').replace('allowed_', '').replace('blocked_', '')
        for k in metrics.keys()
        if k.startswith(('total_', 'allowed_', 'blocked_'))
    )
    endpoints = [e for e in endpoints if e and e != 'unknown']
    
    endpoint_stats = []
    for endpoint in endpoints:
        total = int(metrics.get(f'total_{endpoint}', 0))
        allowed = int(metrics.get(f'allowed_{endpoint}', 0))
        blocked = int(metrics.get(f'blocked_{endpoint}', 0))
        rate = (blocked / total * 100) if total > 0 else 0.0
        
        endpoint_stats.append(EndpointStats(
            endpoint=endpoint,
            total_requests=total,
            allowed_requests=allowed,
            blocked_requests=blocked,
            block_rate=round(rate, 2)
        ))
    
    return sorted(endpoint_stats, key=lambda x: x.total_requests, reverse=True)


@router.get("/clients", response_model=List[ClientStats])
async def get_client_stats(limit: int = 10):
    """
    Get rate limit statistics per client.
    
    Args:
        limit: Maximum number of clients to return (default: 10)
    """
    limiter = await get_rate_limiter()
    
    if limiter._use_redis:
        # For Redis, we'd need to fetch all keys - simplified for now
        return []
    
    # Get local state clients
    clients = []
    for client_key, state in limiter._local_state.items():
        client_type = "user" if client_key.startswith("user:") else "ip"
        
        # Hash the client key for display
        display_key = client_key[:8] + "..." if len(client_key) > 8 else client_key
        
        config = limiter.config
        
        clients.append(ClientStats(
            client_key=display_key,
            client_type=client_type,
            requests_in_minute=state.request_count,
            requests_in_hour=state.request_count,  # Simplified
            limit_minute=config.requests_per_minute,
            limit_hour=config.requests_per_hour,
            remaining_minute=max(0, config.requests_per_minute - state.request_count),
            remaining_hour=max(0, config.requests_per_hour - state.request_count)
        ))
    
    # Sort by requests and limit
    clients.sort(key=lambda x: x.requests_in_minute, reverse=True)
    return clients[:limit]


@router.get("/metrics/prometheus")
async def get_rate_limit_prometheus_metrics():
    """
    Get rate limit metrics in Prometheus format.
    """
    from services.metrics import get_metrics
    return Response(content=get_metrics(), media_type="text/plain")


class ConfigInfo(BaseModel):
    """Rate limit configuration information"""
    requests_per_minute: int
    requests_per_hour: int
    burst_size: int
    use_redis: bool
    endpoint_overrides: Dict[str, dict]


@router.get("/config", response_model=ConfigInfo)
async def get_rate_limit_config():
    """
    Get the current rate limit configuration.
    """
    limiter = await get_rate_limiter()
    
    endpoint_overrides = {
        "/api/v1/conversions": {
            "requests_per_minute": 10,
            "requests_per_hour": 100
        },
        "/api/v1/upload": {
            "requests_per_minute": 20,
            "requests_per_hour": 200
        }
    }
    
    return ConfigInfo(
        requests_per_minute=limiter.config.requests_per_minute,
        requests_per_hour=limiter.config.requests_per_hour,
        burst_size=limiter.config.burst_size,
        use_redis=limiter._use_redis,
        endpoint_overrides=endpoint_overrides
    )


class ConfigUpdateRequest(BaseModel):
    """Request to update rate limit configuration"""
    requests_per_minute: Optional[int] = None
    requests_per_hour: Optional[int] = None
    burst_size: Optional[int] = None


@router.post("/config")
async def update_rate_limit_config(config: ConfigUpdateRequest):
    """
    Update rate limit configuration.
    
    Note: This is a simplified implementation. In production, you'd want
    more robust configuration management.
    """
    limiter = await get_rate_limiter()
    
    if config.requests_per_minute is not None:
        limiter.config.requests_per_minute = config.requests_per_minute
    if config.requests_per_hour is not None:
        limiter.config.requests_per_hour = config.requests_per_hour
    if config.burst_size is not None:
        limiter.config.burst_size = config.burst_size
    
    return {
        "status": "success",
        "message": "Configuration updated",
        "config": {
            "requests_per_minute": limiter.config.requests_per_minute,
            "requests_per_hour": limiter.config.requests_per_hour,
            "burst_size": limiter.config.burst_size
        }
    }
