"""
Graph Caching API Endpoints

This module provides REST API endpoints for knowledge graph caching,
including cache management, performance monitoring, and optimization.
"""

import logging
from typing import Dict, List, Optional, Any
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from db.base import get_db
from src.services.graph_caching import (
    graph_caching_service,
    CacheStrategy,
    CacheInvalidationStrategy,
)

logger = logging.getLogger(__name__)

router = APIRouter()


# Cache Management Endpoints


@router.post("/cache/warm-up")
async def warm_up_cache(db: AsyncSession = Depends(get_db)):
    """Warm up cache with frequently accessed data."""
    try:
        result = await graph_caching_service.warm_up(db)

        if not result["success"]:
            raise HTTPException(status_code=500, detail=result["error"])

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error warming up cache: {e}")
        raise HTTPException(status_code=500, detail=f"Cache warm-up failed: {str(e)}")


@router.get("/cache/stats")
async def get_cache_stats(
    cache_type: Optional[str] = Query(
        None, description="Type of cache to get stats for"
    ),
):
    """Get cache performance statistics."""
    try:
        result = await graph_caching_service.get_cache_stats(cache_type)

        return {
            "success": True,
            "cache_stats": result,
            "timestamp": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        logger.error(f"Error getting cache stats: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to get cache stats: {str(e)}"
        )


@router.post("/cache/optimize")
async def optimize_cache(optimization_data: Dict[str, Any] = None):
    """Optimize cache performance."""
    try:
        strategy = (
            optimization_data.get("strategy", "adaptive")
            if optimization_data
            else "adaptive"
        )

        result = await graph_caching_service.optimize_cache(strategy)

        if not result["success"]:
            raise HTTPException(status_code=500, detail=result["error"])

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error optimizing cache: {e}")
        raise HTTPException(
            status_code=500, detail=f"Cache optimization failed: {str(e)}"
        )


@router.post("/cache/invalidate")
async def invalidate_cache(invalidation_data: Dict[str, Any]):
    """Invalidate cache entries."""
    try:
        cache_type = invalidation_data.get("cache_type")
        pattern = invalidation_data.get("pattern")
        cascade = invalidation_data.get("cascade", True)

        result = await graph_caching_service.invalidate(cache_type, pattern, cascade)

        return {
            "success": True,
            "invalidated_entries": result,
            "cache_type": cache_type,
            "pattern": pattern,
            "cascade": cascade,
            "message": "Cache invalidation completed",
        }

    except Exception as e:
        logger.error(f"Error invalidating cache: {e}")
        raise HTTPException(
            status_code=500, detail=f"Cache invalidation failed: {str(e)}"
        )


@router.get("/cache/entries")
async def get_cache_entries(
    cache_type: str = Query(..., description="Type of cache to get entries for"),
    limit: int = Query(100, le=1000, description="Maximum number of entries to return"),
):
    """Get entries from a specific cache."""
    try:
        with graph_caching_service.lock:
            if cache_type not in graph_caching_service.l1_cache:
                raise HTTPException(
                    status_code=404, detail=f"Cache type '{cache_type}' not found"
                )

            cache_data = graph_caching_service.l1_cache[cache_type]
            entries = []

            for key, entry in list(cache_data.items())[:limit]:
                entries.append(
                    {
                        "key": key,
                        "created_at": entry.created_at.isoformat(),
                        "last_accessed": entry.last_accessed.isoformat(),
                        "access_count": entry.access_count,
                        "size_bytes": entry.size_bytes,
                        "ttl_seconds": entry.ttl_seconds,
                        "metadata": entry.metadata,
                    }
                )

            return {
                "success": True,
                "cache_type": cache_type,
                "entries": entries,
                "total_entries": len(cache_data),
                "returned_entries": len(entries),
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting cache entries: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to get cache entries: {str(e)}"
        )


# Cache Configuration Endpoints


@router.get("/cache/config")
async def get_cache_config():
    """Get cache configuration."""
    try:
        with graph_caching_service.lock:
            configs = {}

            for cache_type, config in graph_caching_service.cache_configs.items():
                configs[cache_type] = {
                    "max_size_mb": config.max_size_mb,
                    "max_entries": config.max_entries,
                    "ttl_seconds": config.ttl_seconds,
                    "strategy": config.strategy.value,
                    "invalidation_strategy": config.invalidation_strategy.value,
                    "refresh_interval_seconds": config.refresh_interval_seconds,
                    "enable_compression": config.enable_compression,
                    "enable_serialization": config.enable_serialization,
                }

        return {
            "success": True,
            "cache_configs": configs,
            "total_cache_types": len(configs),
        }

    except Exception as e:
        logger.error(f"Error getting cache config: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to get cache config: {str(e)}"
        )


@router.post("/cache/config")
async def update_cache_config(config_data: Dict[str, Any]):
    """Update cache configuration."""
    try:
        cache_type = config_data.get("cache_type")

        if not cache_type:
            raise HTTPException(status_code=400, detail="cache_type is required")

        # Get existing config or create new one
        existing_config = graph_caching_service.cache_configs.get(cache_type)

        if existing_config:
            # Update existing config
            new_config = existing_config

            if "max_size_mb" in config_data:
                new_config.max_size_mb = config_data["max_size_mb"]

            if "max_entries" in config_data:
                new_config.max_entries = config_data["max_entries"]

            if "ttl_seconds" in config_data:
                new_config.ttl_seconds = config_data["ttl_seconds"]

            if "strategy" in config_data:
                try:
                    new_config.strategy = CacheStrategy(config_data["strategy"])
                except ValueError:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Invalid strategy: {config_data['strategy']}",
                    )

            if "invalidation_strategy" in config_data:
                try:
                    new_config.invalidation_strategy = CacheInvalidationStrategy(
                        config_data["invalidation_strategy"]
                    )
                except ValueError:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Invalid invalidation_strategy: {config_data['invalidation_strategy']}",
                    )

            if "enable_compression" in config_data:
                new_config.enable_compression = config_data["enable_compression"]

            if "enable_serialization" in config_data:
                new_config.enable_serialization = config_data["enable_serialization"]
        else:
            # Create new config
            try:
                strategy = CacheStrategy(config_data.get("strategy", "lru"))
                invalidation_strategy = CacheInvalidationStrategy(
                    config_data.get("invalidation_strategy", "time_based")
                )

                new_config = {
                    "max_size_mb": config_data.get("max_size_mb", 100.0),
                    "max_entries": config_data.get("max_entries", 10000),
                    "ttl_seconds": config_data.get("ttl_seconds"),
                    "strategy": strategy,
                    "invalidation_strategy": invalidation_strategy,
                    "refresh_interval_seconds": config_data.get(
                        "refresh_interval_seconds", 300
                    ),
                    "enable_compression": config_data.get("enable_compression", True),
                    "enable_serialization": config_data.get(
                        "enable_serialization", True
                    ),
                }

                from src.services.graph_caching import CacheConfig

                graph_caching_service.cache_configs[cache_type] = CacheConfig(
                    **new_config
                )

            except ValueError as e:
                raise HTTPException(
                    status_code=400, detail=f"Configuration error: {str(e)}"
                )

        return {
            "success": True,
            "cache_type": cache_type,
            "config_updated": True,
            "message": f"Cache configuration updated for {cache_type}",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating cache config: {e}")
        raise HTTPException(
            status_code=500, detail=f"Cache config update failed: {str(e)}"
        )


# Performance Monitoring Endpoints


@router.get("/cache/performance")
async def get_performance_metrics():
    """Get detailed cache performance metrics."""
    try:
        with graph_caching_service.lock:
            # Calculate detailed metrics
            stats = graph_caching_service.cache_stats
            performance_metrics = {}

            for cache_type, cache_stats in stats.items():
                if cache_type == "overall":
                    continue

                performance_metrics[cache_type] = {
                    "basic_stats": {
                        "hits": cache_stats.hits,
                        "misses": cache_stats.misses,
                        "sets": cache_stats.sets,
                        "deletes": cache_stats.deletes,
                        "evictions": cache_stats.evictions,
                    },
                    "performance_stats": {
                        "hit_ratio": cache_stats.hit_ratio,
                        "avg_access_time_ms": cache_stats.avg_access_time_ms,
                        "total_size_bytes": cache_stats.total_size_bytes,
                        "memory_usage_mb": cache_stats.memory_usage_mb,
                    },
                    "efficiency": {
                        "operations_per_second": (
                            (cache_stats.hits + cache_stats.misses)
                            / max(cache_stats.avg_access_time_ms / 1000, 0.001)
                        ),
                        "bytes_per_hit": cache_stats.total_size_bytes
                        / max(cache_stats.hits, 1),
                        "hit_per_mb": cache_stats.hits
                        / max(cache_stats.memory_usage_mb, 0.001),
                    },
                }

            # Overall metrics
            overall = stats.get("overall")
            if overall:
                performance_metrics["overall"] = {
                    "total_hits": overall.hits,
                    "total_misses": overall.misses,
                    "total_sets": overall.sets,
                    "total_deletes": overall.deletes,
                    "total_evictions": overall.evictions,
                    "overall_hit_ratio": overall.hit_ratio,
                    "overall_avg_access_time_ms": overall.avg_access_time_ms,
                    "total_memory_usage_mb": overall.memory_usage_mb,
                    "total_size_bytes": overall.total_size_bytes,
                }

        return {
            "success": True,
            "performance_metrics": performance_metrics,
            "calculated_at": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        logger.error(f"Error getting performance metrics: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to get performance metrics: {str(e)}"
        )


@router.get("/cache/history")
async def get_cache_history(
    hours: int = Query(24, le=168, description="Hours of history to retrieve"),
    cache_type: Optional[str] = Query(None, description="Filter by cache type"),
):
    """Get cache operation history."""
    try:
        with graph_caching_service.lock:
            history = graph_caching_service.performance_history

            # Filter by time
            cutoff_time = datetime.utcnow() - timedelta(hours=hours)
            filtered_history = [
                entry
                for entry in history
                if datetime.fromisoformat(entry["timestamp"]) > cutoff_time
            ]

            # Filter by cache type if specified
            if cache_type:
                filtered_history = [
                    entry
                    for entry in filtered_history
                    if entry.get("cache_type") == cache_type
                ]

            # Calculate statistics
            total_operations = len(filtered_history)
            operations_by_type = {}
            operations_by_cache = {}
            avg_access_times = []

            for entry in filtered_history:
                op_type = entry.get("operation", "unknown")
                ct = entry.get("cache_type", "unknown")
                access_time = entry.get("access_time_ms", 0)

                operations_by_type[op_type] = operations_by_type.get(op_type, 0) + 1
                operations_by_cache[ct] = operations_by_cache.get(ct, 0) + 1

                if access_time > 0:
                    avg_access_times.append(access_time)

            avg_access_time = (
                sum(avg_access_times) / len(avg_access_times) if avg_access_times else 0
            )

            return {
                "success": True,
                "history_period_hours": hours,
                "cache_type_filter": cache_type,
                "total_operations": total_operations,
                "operations_by_type": operations_by_type,
                "operations_by_cache": operations_by_cache,
                "avg_access_time_ms": avg_access_time,
                "entries_returned": len(filtered_history),
                "history": filtered_history[-100:],  # Last 100 entries
            }

    except Exception as e:
        logger.error(f"Error getting cache history: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to get cache history: {str(e)}"
        )


# Cache Strategies Endpoints


@router.get("/cache/strategies")
async def get_cache_strategies():
    """Get available caching strategies."""
    try:
        from src.services.graph_caching import CacheStrategy

        strategies = []
        for strategy in CacheStrategy:
            strategies.append(
                {
                    "value": strategy.value,
                    "name": strategy.value.replace("_", " ").title(),
                    "description": _get_strategy_description(strategy),
                    "use_cases": _get_strategy_use_cases(strategy),
                }
            )

        return {
            "success": True,
            "cache_strategies": strategies,
            "total_strategies": len(strategies),
        }

    except Exception as e:
        logger.error(f"Error getting cache strategies: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to get cache strategies: {str(e)}"
        )


@router.get("/cache/invalidation-strategies")
async def get_invalidation_strategies():
    """Get available cache invalidation strategies."""
    try:
        from src.services.graph_caching import CacheInvalidationStrategy

        strategies = []
        for strategy in CacheInvalidationStrategy:
            strategies.append(
                {
                    "value": strategy.value,
                    "name": strategy.value.replace("_", " ").title(),
                    "description": _get_invalidation_description(strategy),
                    "use_cases": _get_invalidation_use_cases(strategy),
                }
            )

        return {
            "success": True,
            "invalidation_strategies": strategies,
            "total_strategies": len(strategies),
        }

    except Exception as e:
        logger.error(f"Error getting invalidation strategies: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to get invalidation strategies: {str(e)}"
        )


# Utility Endpoints


@router.post("/cache/test")
async def test_cache_performance(
    test_data: Dict[str, Any], db: AsyncSession = Depends(get_db)
):
    """Test cache performance with specified parameters."""
    try:
        test_type = test_data.get("test_type", "read")
        iterations = test_data.get("iterations", 100)
        data_size = test_data.get("data_size", "small")

        # Test cache performance
        start_time = time.time()

        if test_type == "read":
            # Test read performance
            cache_times = []
            for i in range(iterations):
                cache_start = time.time()
                await graph_caching_service.get("nodes", f"test_key_{i}")
                cache_end = time.time()
                cache_times.append((cache_end - cache_start) * 1000)

        elif test_type == "write":
            # Test write performance
            cache_times = []
            for i in range(iterations):
                cache_start = time.time()
                await graph_caching_service.set(
                    "nodes", f"test_key_{i}", {"data": f"test_data_{i}"}
                )
                cache_end = time.time()
                cache_times.append((cache_end - cache_start) * 1000)

        test_time = (time.time() - start_time) * 1000

        # Calculate statistics
        avg_cache_time = sum(cache_times) / len(cache_times) if cache_times else 0
        min_cache_time = min(cache_times) if cache_times else 0
        max_cache_time = max(cache_times) if cache_times else 0

        return {
            "success": True,
            "test_type": test_type,
            "iterations": iterations,
            "data_size": data_size,
            "total_time_ms": test_time,
            "cache_performance": {
                "avg_time_ms": avg_cache_time,
                "min_time_ms": min_cache_time,
                "max_time_ms": max_cache_time,
                "operations_per_second": iterations / (test_time / 1000)
                if test_time > 0
                else 0,
            },
            "cache_stats": await graph_caching_service.get_cache_stats(),
        }

    except Exception as e:
        logger.error(f"Error testing cache performance: {e}")
        raise HTTPException(
            status_code=500, detail=f"Cache performance test failed: {str(e)}"
        )


@router.delete("/cache/clear")
async def clear_cache(
    cache_type: Optional[str] = Query(
        None, description="Type of cache to clear (None for all)"
    ),
):
    """Clear cache entries."""
    try:
        with graph_caching_service.lock:
            cleared_count = 0

            if cache_type:
                # Clear specific cache type
                if cache_type in graph_caching_service.l1_cache:
                    old_size = len(graph_caching_service.l1_cache[cache_type])
                    graph_caching_service.l1_cache[cache_type].clear()
                    cleared_count = old_size
            else:
                # Clear all caches
                for ct, cache_data in graph_caching_service.l1_cache.items():
                    cleared_count += len(cache_data)
                    cache_data.clear()

                # Clear L2 cache
                graph_caching_service.l2_cache.clear()

        return {
            "success": True,
            "cache_type": cache_type or "all",
            "cleared_entries": cleared_count,
            "message": "Cache cleared successfully",
        }

    except Exception as e:
        logger.error(f"Error clearing cache: {e}")
        raise HTTPException(status_code=500, detail=f"Cache clear failed: {str(e)}")


@router.get("/cache/health")
async def get_cache_health():
    """Get cache health status."""
    try:
        with graph_caching_service.lock:
            health_status = "healthy"
            issues = []

            # Check cache stats
            overall_stats = graph_caching_service.cache_stats.get("overall")

            if overall_stats:
                # Check hit ratio
                if overall_stats.hit_ratio < 0.5:
                    health_status = "warning"
                    issues.append("Low cache hit ratio")

                # Check memory usage
                if overall_stats.memory_usage_mb > 200:  # 200MB threshold
                    if health_status == "healthy":
                        health_status = "warning"
                    issues.append("High memory usage")

                # Check access time
                if overall_stats.avg_access_time_ms > 100:  # 100ms threshold
                    if health_status == "healthy":
                        health_status = "warning"
                    issues.append("High average access time")

            # Check cache configurations
            config_issues = []
            for cache_type, config in graph_caching_service.cache_configs.items():
                if config.max_size_mb > 500:  # 500MB per cache type
                    config_issues.append(f"Large cache size for {cache_type}")

            if config_issues:
                if health_status == "healthy":
                    health_status = "warning"
                issues.extend(config_issues)

            return {
                "success": True,
                "health_status": health_status,
                "issues": issues,
                "cache_stats": overall_stats.__dict__ if overall_stats else {},
                "total_cache_types": len(graph_caching_service.l1_cache),
                "cleanup_thread_running": graph_caching_service.cleanup_thread
                is not None,
                "check_timestamp": datetime.utcnow().isoformat(),
            }

    except Exception as e:
        logger.error(f"Error getting cache health: {e}")
        raise HTTPException(
            status_code=500, detail=f"Cache health check failed: {str(e)}"
        )


# Private Helper Methods


def _get_strategy_description(strategy) -> str:
    """Get description for a caching strategy."""
    descriptions = {
        CacheStrategy.LRU: "Least Recently Used - evicts items that haven't been accessed recently",
        CacheStrategy.LFU: "Least Frequently Used - evicts items with lowest access frequency",
        CacheStrategy.FIFO: "First In, First Out - evicts oldest items first",
        CacheStrategy.TTL: "Time To Live - evicts items based on age",
        CacheStrategy.WRITE_THROUGH: "Write Through - writes to cache and storage simultaneously",
        CacheStrategy.WRITE_BEHIND: "Write Behind - writes to cache first, then to storage",
        CacheStrategy.REFRESH_AHEAD: "Refresh Ahead - proactively refreshes cache entries",
    }
    return descriptions.get(strategy, "Unknown caching strategy")


def _get_strategy_use_cases(strategy) -> List[str]:
    """Get use cases for a caching strategy."""
    use_cases = {
        CacheStrategy.LRU: [
            "General purpose caching",
            "Web page caching",
            "Database query results",
        ],
        CacheStrategy.LFU: [
            "Access pattern prediction",
            "Frequently accessed data",
            "Hot data management",
        ],
        CacheStrategy.FIFO: ["Simple caching", "Ordered data", "Session data"],
        CacheStrategy.TTL: [
            "Time-sensitive data",
            "API responses",
            "Configuration data",
        ],
        CacheStrategy.WRITE_THROUGH: [
            "Critical data",
            "Financial data",
            "Real-time updates",
        ],
        CacheStrategy.WRITE_BEHIND: [
            "High write volume",
            "Logging systems",
            "Analytics data",
        ],
        CacheStrategy.REFRESH_AHEAD: [
            "Predictable access patterns",
            "Preloading data",
            "Background updates",
        ],
    }
    return use_cases.get(strategy, ["General use"])


def _get_invalidation_description(strategy) -> str:
    """Get description for an invalidation strategy."""
    descriptions = {
        CacheInvalidationStrategy.TIME_BASED: "Invalidates entries based on time thresholds",
        CacheInvalidationStrategy.EVENT_DRIVEN: "Invalidates entries in response to specific events",
        CacheInvalidationStrategy.MANUAL: "Requires manual invalidation of cache entries",
        CacheInvalidationStrategy.PROACTIVE: "Proactively invalidates entries based on predictions",
        CacheInvalidationStrategy.ADAPTIVE: "Adapts invalidation strategy based on usage patterns",
    }
    return descriptions.get(strategy, "Unknown invalidation strategy")


def _get_invalidation_use_cases(strategy) -> List[str]:
    """Get use cases for an invalidation strategy."""
    use_cases = {
        CacheInvalidationStrategy.TIME_BASED: [
            "API responses",
            "News feeds",
            "Market data",
        ],
        CacheInvalidationStrategy.EVENT_DRIVEN: [
            "User updates",
            "System changes",
            "Data modifications",
        ],
        CacheInvalidationStrategy.MANUAL: [
            "Administrative control",
            "Data migrations",
            "System maintenance",
        ],
        CacheInvalidationStrategy.PROACTIVE: [
            "Predictive caching",
            "Load balancing",
            "Performance optimization",
        ],
        CacheInvalidationStrategy.ADAPTIVE: [
            "Dynamic systems",
            "Variable workloads",
            "Smart caching",
        ],
    }
    return use_cases.get(strategy, ["General use"])


# Add missing imports
from datetime import datetime, timedelta
import time
