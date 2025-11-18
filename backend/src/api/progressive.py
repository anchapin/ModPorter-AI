"""
Progressive Loading API Endpoints

This module provides REST API endpoints for progressive loading of complex
knowledge graph visualizations, including level-of-detail and streaming.
"""

import logging
from typing import Dict, List, Optional, Any
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.base import get_db
from src.services.progressive_loading import (
    progressive_loading_service, LoadingStrategy, DetailLevel, LoadingPriority
)

logger = logging.getLogger(__name__)

router = APIRouter()


# Progressive Loading Endpoints

@router.post("/progressive/load")
async def start_progressive_load(
    load_data: Dict[str, Any],
    db: AsyncSession = Depends(get_db)
):
    """Start progressive loading for a visualization."""
    try:
        visualization_id = load_data.get("visualization_id")
        strategy_str = load_data.get("loading_strategy", "lod_based")
        detail_level_str = load_data.get("detail_level", "low")
        priority_str = load_data.get("priority", "medium")
        viewport = load_data.get("viewport")
        parameters = load_data.get("parameters", {})
        
        if not visualization_id:
            raise HTTPException(
                status_code=400,
                detail="visualization_id is required"
            )
        
        # Parse loading strategy
        try:
            strategy = LoadingStrategy(strategy_str)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid loading_strategy: {strategy_str}"
            )
        
        # Parse detail level
        try:
            detail_level = DetailLevel(detail_level_str)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid detail_level: {detail_level_str}"
            )
        
        # Parse priority
        try:
            priority = LoadingPriority(priority_str)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid priority: {priority_str}"
            )
        
        result = await progressive_loading_service.start_progressive_load(
            visualization_id, strategy, detail_level, viewport, priority, parameters, db
        )
        
        if not result["success"]:
            raise HTTPException(status_code=400, detail=result["error"])
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error starting progressive load: {e}")
        raise HTTPException(status_code=500, detail=f"Progressive load failed: {str(e)}")


@router.get("/progressive/tasks/{task_id}")
async def get_loading_progress(task_id: str):
    """Get progress of a progressive loading task."""
    try:
        result = await progressive_loading_service.get_loading_progress(task_id)
        
        if not result["success"]:
            raise HTTPException(status_code=404, detail=result["error"])
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting loading progress: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get loading progress: {str(e)}")


@router.post("/progressive/tasks/{task_id}/update-level")
async def update_loading_level(
    task_id: str,
    update_data: Dict[str, Any]
):
    """Update loading level for an existing task."""
    try:
        detail_level_str = update_data.get("detail_level")
        viewport = update_data.get("viewport")
        
        if not detail_level_str:
            raise HTTPException(
                status_code=400,
                detail="detail_level is required"
            )
        
        # Parse detail level
        try:
            detail_level = DetailLevel(detail_level_str)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid detail_level: {detail_level_str}"
            )
        
        result = await progressive_loading_service.update_loading_level(
            task_id, detail_level, viewport
        )
        
        if not result["success"]:
            raise HTTPException(status_code=400, detail=result["error"])
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating loading level: {e}")
        raise HTTPException(status_code=500, detail=f"Loading level update failed: {str(e)}")


@router.post("/progressive/preload")
async def preload_adjacent_areas(
    preload_data: Dict[str, Any],
    db: AsyncSession = Depends(get_db)
):
    """Preload areas adjacent to current viewport."""
    try:
        visualization_id = preload_data.get("visualization_id")
        current_viewport = preload_data.get("current_viewport")
        preload_distance = preload_data.get("preload_distance", 2.0)
        detail_level_str = preload_data.get("detail_level", "low")
        
        if not all([visualization_id, current_viewport]):
            raise HTTPException(
                status_code=400,
                detail="visualization_id and current_viewport are required"
            )
        
        # Parse detail level
        try:
            detail_level = DetailLevel(detail_level_str)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid detail_level: {detail_level_str}"
            )
        
        result = await progressive_loading_service.preload_adjacent_areas(
            visualization_id, current_viewport, preload_distance, detail_level, db
        )
        
        if not result["success"]:
            raise HTTPException(status_code=400, detail=result["error"])
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error preloading adjacent areas: {e}")
        raise HTTPException(status_code=500, detail=f"Preloading failed: {str(e)}")


@router.get("/progressive/statistics")
async def get_loading_statistics(
    visualization_id: Optional[str] = Query(None, description="Filter by visualization ID")
):
    """Get progressive loading statistics and performance metrics."""
    try:
        result = await progressive_loading_service.get_loading_statistics(visualization_id)
        
        if not result["success"]:
            raise HTTPException(status_code=500, detail=result["error"])
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting loading statistics: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get loading statistics: {str(e)}")


# Strategy and Configuration Endpoints

@router.get("/progressive/loading-strategies")
async def get_loading_strategies():
    """Get available progressive loading strategies."""
    try:
        strategies = []
        
        for strategy in LoadingStrategy:
            strategies.append({
                "value": strategy.value,
                "name": strategy.value.replace("_", " ").title(),
                "description": self._get_strategy_description(strategy),
                "use_cases": self._get_strategy_use_cases(strategy),
                "recommended_for": self._get_strategy_recommendations(strategy),
                "performance_characteristics": self._get_strategy_performance(strategy)
            })
        
        return {
            "success": True,
            "loading_strategies": strategies,
            "total_strategies": len(strategies)
        }
        
    except Exception as e:
        logger.error(f"Error getting loading strategies: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get loading strategies: {str(e)}")


@router.get("/progressive/detail-levels")
async def get_detail_levels():
    """Get available detail levels for progressive loading."""
    try:
        detail_levels = []
        
        for level in DetailLevel:
            detail_levels.append({
                "value": level.value,
                "name": level.value.title(),
                "description": self._get_detail_level_description(level),
                "item_types": self._get_detail_level_items(level),
                "performance_impact": self._get_detail_level_performance(level),
                "memory_usage": self._get_detail_level_memory(level),
                "recommended_conditions": self._get_detail_level_conditions(level)
            })
        
        return {
            "success": True,
            "detail_levels": detail_levels,
            "total_levels": len(detail_levels)
        }
        
    except Exception as e:
        logger.error(f"Error getting detail levels: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get detail levels: {str(e)}")


@router.get("/progressive/priorities")
async def get_loading_priorities():
    """Get available loading priorities."""
    try:
        priorities = []
        
        for priority in LoadingPriority:
            priorities.append({
                "value": priority.value,
                "name": priority.value.title(),
                "description": self._get_priority_description(priority),
                "use_cases": self._get_priority_use_cases(priority),
                "expected_response_time": self._get_priority_response_time(priority),
                "resource_allocation": self._get_priority_resources(priority)
            })
        
        return {
            "success": True,
            "loading_priorities": priorities,
            "total_priorities": len(priorities)
        }
        
    except Exception as e:
        logger.error(f"Error getting loading priorities: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get loading priorities: {str(e)}")


# Utility Endpoints

@router.post("/progressive/estimate-load")
async def estimate_load_time(
    estimate_data: Dict[str, Any],
    db: AsyncSession = Depends(get_db)
):
    """Estimate loading time and resources for given parameters."""
    try:
        visualization_id = estimate_data.get("visualization_id")
        strategy_str = estimate_data.get("loading_strategy", "lod_based")
        detail_level_str = estimate_data.get("detail_level", "medium")
        viewport = estimate_data.get("viewport")
        total_items = estimate_data.get("estimated_total_items")
        
        if not visualization_id:
            raise HTTPException(
                status_code=400,
                detail="visualization_id is required"
            )
        
        # Parse strategy and detail level
        try:
            strategy = LoadingStrategy(strategy_str)
            detail_level = DetailLevel(detail_level_str)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        
        # Estimate based on historical data or defaults
        load_rates = {
            (LoadingStrategy.LOD_BASED, DetailLevel.MINIMAL): 500.0,
            (LoadingStrategy.LOD_BASED, DetailLevel.LOW): 300.0,
            (LoadingStrategy.LOD_BASED, DetailLevel.MEDIUM): 150.0,
            (LoadingStrategy.LOD_BASED, DetailLevel.HIGH): 75.0,
            (LoadingStrategy.LOD_BASED, DetailLevel.FULL): 40.0,
            (LoadingStrategy.DISTANCE_BASED, DetailLevel.MINIMAL): 450.0,
            (LoadingStrategy.DISTANCE_BASED, DetailLevel.LOW): 280.0,
            (LoadingStrategy.DISTANCE_BASED, DetailLevel.MEDIUM): 140.0,
            (LoadingStrategy.DISTANCE_BASED, DetailLevel.HIGH): 70.0,
            (LoadingStrategy.DISTANCE_BASED, DetailLevel.FULL): 35.0,
        }
        
        load_rate = load_rates.get((strategy, detail_level), 100.0)  # items per second
        
        # Estimate total items if not provided
        if not total_items:
            total_items = await self._estimate_items_for_config(
                visualization_id, strategy, detail_level, viewport, db
            )
        
        estimated_time = total_items / load_rate if load_rate > 0 else 60.0
        
        # Memory usage estimation
        memory_per_item = {
            DetailLevel.MINIMAL: 0.5,    # KB
            DetailLevel.LOW: 2.0,
            DetailLevel.MEDIUM: 8.0,
            DetailLevel.HIGH: 20.0,
            DetailLevel.FULL: 50.0
        }
        
        memory_per_item_kb = memory_per_item.get(detail_level, 8.0)
        estimated_memory_mb = (total_items * memory_per_item_kb) / 1024
        
        # Network bandwidth estimation
        network_per_item_kb = {
            DetailLevel.MINIMAL: 1.0,
            DetailLevel.LOW: 5.0,
            DetailLevel.MEDIUM: 20.0,
            DetailLevel.HIGH: 50.0,
            DetailLevel.FULL: 100.0
        }
        
        network_per_item = network_per_item_kb.get(detail_level, 20.0)
        estimated_network_mb = (total_items * network_per_item) / 1024
        
        return {
            "success": True,
            "estimation": {
                "total_items": total_items,
                "loading_strategy": strategy.value,
                "detail_level": detail_level.value,
                "load_rate_items_per_second": load_rate,
                "estimated_time_seconds": estimated_time,
                "estimated_memory_usage_mb": estimated_memory_mb,
                "estimated_network_bandwidth_mb": estimated_network_mb,
                "chunk_recommendations": {
                    "optimal_chunk_size": min(500, total_items // 10),
                    "max_chunk_size": min(1000, total_items // 5),
                    "min_chunk_size": max(50, total_items // 50)
                },
                "performance_tips": self._get_performance_tips(strategy, detail_level)
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error estimating load time: {e}")
        raise HTTPException(status_code=500, detail=f"Load time estimation failed: {str(e)}")


@router.post("/progressive/optimize-settings")
async def optimize_loading_settings(
    optimization_data: Dict[str, Any]
):
    """Get optimized loading settings for current conditions."""
    try:
        current_performance = optimization_data.get("current_performance", {})
        system_capabilities = optimization_data.get("system_capabilities", {})
        user_preferences = optimization_data.get("user_preferences", {})
        
        # Analyze current performance
        load_time = current_performance.get("average_load_time_ms", 2000)
        memory_usage = current_performance.get("memory_usage_mb", 500)
        network_usage = current_performance.get("network_usage_mbps", 10)
        
        # Get system constraints
        available_memory = system_capabilities.get("available_memory_mb", 4096)
        cpu_cores = system_capabilities.get("cpu_cores", 4)
        network_speed = system_capabilities.get("network_speed_mbps", 100)
        
        # Get user preferences
        preference_quality = user_preferences.get("quality_preference", "balanced")  # quality, balanced, performance
        preference_interactivity = user_preferences.get("interactivity_preference", "high")  # low, medium, high
        
        # Generate optimized settings
        optimizations = {}
        
        # Memory optimization
        if memory_usage > available_memory * 0.7:
            optimizations["memory"] = {
                "recommended_detail_level": "medium" if preference_quality == "balanced" else "low",
                "max_chunks_in_memory": min(5, available_memory // 200),
                "enable_streaming": True,
                "cache_ttl_seconds": 120
            }
        
        # Performance optimization
        if load_time > 3000:  # 3 seconds
            optimizations["performance"] = {
                "recommended_loading_strategy": "lod_based",
                "chunk_size": min(100, memory_usage // 10),
                "parallel_loading": cpu_cores >= 4,
                "preloading_enabled": preference_interactivity == "high"
            }
        
        # Network optimization
        if network_usage > network_speed * 0.8:
            optimizations["network"] = {
                "compression_enabled": True,
                "incremental_loading": True,
                "detail_adaptation": True,
                "preload_distance": 1.5
            }
        
        # Quality optimization based on preferences
        if preference_quality == "quality":
            optimizations["quality"] = {
                "recommended_detail_level": "high",
                "include_all_relationships": True,
                "high_resolution_positions": True,
                "smooth_animations": True
            }
        elif preference_quality == "performance":
            optimizations["quality"] = {
                "recommended_detail_level": "low",
                "include_minimal_relationships": True,
                "low_resolution_positions": True,
                "disable_animations": True
            }
        
        return {
            "success": True,
            "optimized_settings": optimizations,
            "analysis": {
                "current_performance": current_performance,
                "system_capabilities": system_capabilities,
                "user_preferences": user_preferences,
                "optimization_factors": self._get_optimization_factors(
                    current_performance, system_capabilities, user_preferences
                )
            },
            "recommended_strategy": self._get_recommended_strategy(
                optimizations, preference_quality
            ),
            "expected_improvements": self._calculate_expected_improvements(
                optimizations, current_performance
            )
        }
        
    except Exception as e:
        logger.error(f"Error optimizing loading settings: {e}")
        raise HTTPException(status_code=500, detail=f"Settings optimization failed: {str(e)}")


@router.get("/progressive/health")
async def get_progressive_loading_health():
    """Get health status of progressive loading service."""
    try:
        # This would check the health of the progressive loading service
        # For now, return mock health data
        
        active_tasks = len(progressive_loading_service.active_tasks)
        total_caches = len(progressive_loading_service.loading_caches)
        
        # Determine health status
        health_status = "healthy"
        issues = []
        
        if active_tasks > 20:
            health_status = "warning"
            issues.append("High number of active loading tasks")
        
        if total_caches > 100:
            health_status = "warning"
            issues.append("High number of loading caches")
        
        # Check performance metrics
        avg_load_time = progressive_loading_service.average_load_time
        if avg_load_time > 5000:  # 5 seconds
            if health_status == "healthy":
                health_status = "warning"
            issues.append("Slow average loading time")
        
        return {
            "success": True,
            "health_status": health_status,
            "issues": issues,
            "metrics": {
                "active_tasks": active_tasks,
                "total_caches": total_caches,
                "total_viewport_histories": sum(
                    len(vph) for vph in progressive_loading_service.viewport_history.values()
                ),
                "average_load_time_ms": avg_load_time,
                "total_loads": progressive_loading_service.total_loads,
                "background_thread_running": progressive_loading_service.background_thread is not None
            },
            "thresholds": {
                "max_active_tasks": 20,
                "max_caches": 100,
                "max_average_load_time_ms": 5000
            },
            "check_timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error checking progressive loading health: {e}")
        raise HTTPException(status_code=500, detail=f"Health check failed: {str(e)}")


# Private Helper Methods

def _get_strategy_description(strategy) -> str:
    """Get description for loading strategy."""
    descriptions = {
        LoadingStrategy.LOD_BASED: "Load data based on level of detail requirements",
        LoadingStrategy.DISTANCE_BASED: "Load data based on distance from viewport center",
        LoadingStrategy.IMPORTANCE_BASED: "Load data based on importance and priority",
        LoadingStrategy.CLUSTER_BASED: "Load data based on graph cluster structure",
        LoadingStrategy.TIME_BASED: "Load data based on time-based priorities",
        LoadingStrategy.HYBRID: "Combine multiple loading strategies for optimal performance"
    }
    return descriptions.get(strategy, "Unknown loading strategy")


def _get_strategy_use_cases(strategy) -> List[str]:
    """Get use cases for loading strategy."""
    use_cases = {
        LoadingStrategy.LOD_BASED: ["Large graphs", "Memory-constrained environments", "Dynamic zooming"],
        LoadingStrategy.DISTANCE_BASED: ["Geographic visualizations", "Map-like interfaces", "Spatial exploration"],
        LoadingStrategy.IMPORTANCE_BASED: ["Quality-focused applications", "Filtered views", "Prioritized content"],
        LoadingStrategy.CLUSTER_BASED: ["Network analysis", "Community visualization", "Hierarchical data"],
        LoadingStrategy.TIME_BASED: ["Temporal data", "Historical views", "Time-series visualization"],
        LoadingStrategy.HYBRID: ["Complex visualizations", "Adaptive interfaces", "Multi-dimensional data"]
    }
    return use_cases.get(strategy, ["General use"])


def _get_strategy_recommendations(strategy) -> str:
    """Get recommendations for loading strategy."""
    recommendations = {
        LoadingStrategy.LOD_BASED: "Best for applications with dynamic zoom and pan interactions",
        LoadingStrategy.DISTANCE_BASED: "Ideal for spatial or geographic data visualization",
        LoadingStrategy.IMPORTANCE_BASED: "Recommended when data quality and relevance vary",
        LoadingStrategy.CLUSTER_BASED: "Perfect for network graphs with clear community structure",
        LoadingStrategy.TIME_BASED: "Use when temporal aspects are critical",
        LoadingStrategy.HYBRID: "Choose when multiple factors influence loading decisions"
    }
    return recommendations.get(strategy, "General purpose strategy")


def _get_strategy_performance(strategy) -> Dict[str, Any]:
    """Get performance characteristics for loading strategy."""
    characteristics = {
        LoadingStrategy.LOD_BASED: {
            "speed": "medium",
            "memory_efficiency": "high",
            "cpu_usage": "low",
            "network_usage": "medium",
            "scalability": "high"
        },
        LoadingStrategy.DISTANCE_BASED: {
            "speed": "fast",
            "memory_efficiency": "high",
            "cpu_usage": "low",
            "network_usage": "low",
            "scalability": "high"
        },
        LoadingStrategy.IMPORTANCE_BASED: {
            "speed": "medium",
            "memory_efficiency": "medium",
            "cpu_usage": "medium",
            "network_usage": "high",
            "scalability": "medium"
        },
        LoadingStrategy.CLUSTER_BASED: {
            "speed": "medium",
            "memory_efficiency": "high",
            "cpu_usage": "medium",
            "network_usage": "medium",
            "scalability": "high"
        }
    }
    return characteristics.get(strategy, {
        "speed": "medium",
        "memory_efficiency": "medium",
        "cpu_usage": "medium",
        "network_usage": "medium",
        "scalability": "medium"
    })


def _get_detail_level_description(level) -> str:
    """Get description for detail level."""
    descriptions = {
        DetailLevel.MINIMAL: "Load only essential data structure",
        DetailLevel.LOW: "Load basic node information and minimal relationships",
        DetailLevel.MEDIUM: "Load detailed node information with key relationships",
        DetailLevel.HIGH: "Load comprehensive data with most relationships",
        DetailLevel.FULL: "Load all available data including all relationships and patterns"
    }
    return descriptions.get(level, "Unknown detail level")


def _get_detail_level_items(level) -> List[str]:
    """Get item types included in detail level."""
    items = {
        DetailLevel.MINIMAL: ["node_ids", "node_types", "basic_positions"],
        DetailLevel.LOW: ["node_names", "basic_properties", "core_relationships"],
        DetailLevel.MEDIUM: ["detailed_properties", "key_relationships", "patterns"],
        DetailLevel.HIGH: ["all_properties", "most_relationships", "all_patterns"],
        DetailLevel.FULL: ["complete_data", "all_relationships", "metadata", "history"]
    }
    return items.get(level, ["Basic items"])


def _get_detail_level_performance(level) -> str:
    """Get performance impact for detail level."""
    performance = {
        DetailLevel.MINIMAL: "Very low",
        DetailLevel.LOW: "Low",
        DetailLevel.MEDIUM: "Medium",
        DetailLevel.HIGH: "High",
        DetailLevel.FULL: "Very high"
    }
    return performance.get(level, "Medium")


def _get_detail_level_memory(level) -> str:
    """Get memory usage estimate for detail level."""
    memory = {
        DetailLevel.MINIMAL: "Minimal (50-200 MB)",
        DetailLevel.LOW: "Low (200-500 MB)",
        DetailLevel.MEDIUM: "Medium (500MB-1GB)",
        DetailLevel.HIGH: "High (1-2GB)",
        DetailLevel.FULL: "Very high (2-5GB+)"
    }
    return memory.get(level, "Medium (500MB-1GB)")


def _get_detail_level_conditions(level) -> List[str]:
    """Get recommended conditions for detail level."""
    conditions = {
        DetailLevel.MINIMAL: ["Very large graphs (>100K nodes)", "Low memory devices", "Fast loading required"],
        DetailLevel.LOW: ["Large graphs (50K-100K nodes)", "Medium memory devices", "Quick interactions"],
        DetailLevel.MEDIUM: ["Medium graphs (10K-50K nodes)", "Standard memory devices", "Balanced experience"],
        DetailLevel.HIGH: ["Small graphs (<10K nodes)", "High memory devices", "Rich interactions"],
        DetailLevel.FULL: ["Very small graphs (<1K nodes)", "High-performance devices", "Maximum detail needed"]
    }
    return conditions.get(level, ["General conditions"])


def _get_priority_description(priority) -> str:
    """Get description for loading priority."""
    descriptions = {
        LoadingPriority.CRITICAL: "Load immediately with highest system priority",
        LoadingPriority.HIGH: "Load with high priority and faster processing",
        LoadingPriority.MEDIUM: "Load with standard priority and balanced processing",
        LoadingPriority.LOW: "Load with low priority, may be delayed",
        LoadingPriority.BACKGROUND: "Load in background when system resources are available"
    }
    return descriptions.get(priority, "Unknown priority")


def _get_priority_use_cases(priority) -> List[str]:
    """Get use cases for loading priority."""
    use_cases = {
        LoadingPriority.CRITICAL: ["User-focused content", "Current viewport", "Essential interactions"],
        LoadingPriority.HIGH: ["Visible areas", "Frequently accessed content", "Important features"],
        LoadingPriority.MEDIUM: ["Adjacent areas", "Secondary features", "Standard content"],
        LoadingPriority.LOW: ["Peripheral areas", "Optional features", "Background content"],
        LoadingPriority.BACKGROUND: ["Off-screen areas", "Preloading", "Cache warming"]
    }
    return use_cases.get(priority, ["General use"])


def _get_priority_response_time(priority) -> str:
    """Get expected response time for loading priority."""
    response_times = {
        LoadingPriority.CRITICAL: "< 100ms",
        LoadingPriority.HIGH: "100-500ms",
        LoadingPriority.MEDIUM: "500ms-2s",
        LoadingPriority.LOW: "2-10s",
        LoadingPriority.BACKGROUND: "> 10s"
    }
    return response_times.get(priority, "500ms-2s")


def _get_priority_resources(priority) -> str:
    """Get resource allocation for loading priority."""
    resources = {
        LoadingPriority.CRITICAL: "Maximum resources (80% CPU, 70% memory)",
        LoadingPriority.HIGH: "High resources (60% CPU, 50% memory)",
        LoadingPriority.MEDIUM: "Standard resources (40% CPU, 30% memory)",
        LoadingPriority.LOW: "Low resources (20% CPU, 15% memory)",
        LoadingPriority.BACKGROUND: "Minimal resources (10% CPU, 5% memory)"
    }
    return resources.get(priority, "Standard resources (40% CPU, 30% memory)")


# Add missing imports
from datetime import datetime
