"""
Performance Monitoring API Endpoints

This module provides REST API endpoints for accessing performance
monitoring data, triggering optimizations, and managing adaptive settings.
"""

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, Query
from typing import List, Optional, Any
from datetime import datetime, timedelta
from pydantic import BaseModel, Field
import logging

# Import with fallbacks for testing environments
try:
    from services.optimization_integration import (
        optimization_integrator,
        monitor_performance,
    )
except ImportError:

    class MockOptimizationIntegrator:
        def __init__(self):
            self.initialized = False
            self.service_integrations = []

        async def initialize(self):
            self.initialized = True

    optimization_integrator = MockOptimizationIntegrator()
    monitor_performance = None

try:
    from services.performance_monitor import performance_monitor, PerformanceThreshold
except ImportError:

    class MockPerformanceMonitor:
        def __init__(self):
            self.monitoring_active = False
            self.metrics_collector = MockMetricsCollector()
            self.optimizer = MockOptimizer()

    class MockMetricsCollector:
        def __init__(self):
            self.metrics = []

        def collect_system_metrics(self):
            return {}

    class MockOptimizer:
        def __init__(self):
            self.optimization_actions = []

    performance_monitor = MockPerformanceMonitor()
    PerformanceThreshold = None

try:
    from services.adaptive_optimizer import adaptive_engine, OptimizationStrategy
except ImportError:

    class MockAdaptiveEngine:
        def __init__(self):
            self.pattern_learner = MockPatternLearner()
            self.strategy = MockStrategy()

    class MockPatternLearner:
        def __init__(self):
            self.is_trained = False
            self.patterns = []

    class MockStrategy:
        def __init__(self):
            self.value = "basic"

    adaptive_engine = MockAdaptiveEngine()
    OptimizationStrategy = None

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/performance", tags=["performance"])


# Pydantic models for request/response
class PerformanceReportRequest(BaseModel):
    operation_type: Optional[str] = None
    window_minutes: int = Field(default=60, ge=1, le=1440)  # 1 minute to 24 hours


class OptimizationTriggerRequest(BaseModel):
    optimization_type: str = Field(..., description="Type of optimization to trigger")


class ThresholdUpdateRequest(BaseModel):
    metric_name: str = Field(..., description="Metric name")
    warning_threshold: float = Field(..., description="Warning threshold value")
    critical_threshold: float = Field(..., description="Critical threshold value")
    window_minutes: int = Field(default=5, ge=1, le=60)
    consecutive_violations: int = Field(default=3, ge=1, le=10)


class StrategyUpdateRequest(BaseModel):
    strategy: str = Field(..., description="Optimization strategy")


class AlertCallbackRequest(BaseModel):
    webhook_url: str = Field(..., description="Webhook URL for alerts")
    alert_types: List[str] = Field(
        default=["warning", "critical"], description="Types of alerts to send"
    )


# Dependency to ensure optimization integrator is initialized
async def get_optimization_integrator():
    if optimization_integrator is None:
        raise HTTPException(
            status_code=503, detail="Performance monitoring service not available"
        )

    if not optimization_integrator.initialized:
        try:
            await optimization_integrator.initialize()
        except Exception as e:
            logger.error(f"Failed to initialize optimization integrator: {e}")
            raise HTTPException(
                status_code=503, detail="Performance monitoring service unavailable"
            )
    return optimization_integrator


@router.get("/status")
async def get_performance_status(
    integrator: Any = Depends(get_optimization_integrator),
):
    """Get current performance monitoring status"""
    try:
        status = {
            "monitoring_active": performance_monitor.monitoring_active
            if performance_monitor
            else False,
            "adaptive_engine_initialized": adaptive_engine.pattern_learner.is_trained
            if adaptive_engine and hasattr(adaptive_engine, "pattern_learner")
            else False,
            "services_integrated": len(integrator.service_integrations)
            if hasattr(integrator, "service_integrations")
            else 0,
            "total_metrics": len(performance_monitor.metrics_collector.metrics)
            if performance_monitor and hasattr(performance_monitor, "metrics_collector")
            else 0,
            "optimization_actions": len(
                performance_monitor.optimizer.optimization_actions
            )
            if performance_monitor and hasattr(performance_monitor, "optimizer")
            else 0,
            "patterns_learned": len(adaptive_engine.pattern_learner.patterns)
            if adaptive_engine and hasattr(adaptive_engine, "pattern_learner")
            else 0,
            "current_strategy": adaptive_engine.strategy.value
            if adaptive_engine and hasattr(adaptive_engine, "strategy")
            else "unknown",
            "timestamp": datetime.now(),
        }

        # Add system metrics if available
        if performance_monitor and hasattr(performance_monitor, "metrics_collector"):
            try:
                system_metrics = (
                    performance_monitor.metrics_collector.collect_system_metrics()
                )
                status["current_system_metrics"] = system_metrics
            except Exception:
                status["current_system_metrics"] = {}

        return {
            "status_code": 200,
            "message": "Performance status retrieved",
            "data": status,
        }

    except Exception as e:
        logger.error(f"Error getting performance status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/report")
async def get_performance_report(
    request: PerformanceReportRequest,
    integrator: Any = Depends(get_optimization_integrator),
):
    """Generate comprehensive performance report"""
    try:
        report = await integrator.get_optimization_report()

        # Apply filters if specified
        if request.operation_type:
            if (
                "performance_report" in report
                and "operation_stats" in report["performance_report"]
            ):
                filtered_stats = {}
                if (
                    request.operation_type
                    in report["performance_report"]["operation_stats"]
                ):
                    filtered_stats[request.operation_type] = report[
                        "performance_report"
                    ]["operation_stats"][request.operation_type]
                report["performance_report"]["operation_stats"] = filtered_stats

        # Apply time window
        if request.window_minutes != 60:
            # This would need to be implemented in the report generation
            pass

        return {
            "status_code": 200,
            "message": "Performance report generated",
            "data": report,
        }

    except Exception as e:
        logger.error(f"Error generating performance report: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/metrics/operation/{operation_type}")
async def get_operation_metrics(
    operation_type: str,
    window_minutes: int = 60,
    integrator: Any = Depends(get_optimization_integrator),
):
    """Get metrics for a specific operation type"""
    try:
        stats = performance_monitor.metrics_collector.get_operation_stats(
            operation_type, window_minutes
        )
        trend = performance_monitor.metrics_collector.get_trend_analysis(
            operation_type, window_minutes
        )

        return {
            "status_code": 200,
            "message": f"Metrics retrieved for {operation_type}",
            "data": {
                "operation_type": operation_type,
                "window_minutes": window_minutes,
                "statistics": stats,
                "trend_analysis": trend,
                "timestamp": datetime.now(),
            },
        }

    except Exception as e:
        logger.error(f"Error getting operation metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/metrics/system")
async def get_system_metrics(
    samples: int = 100, integrator: Any = Depends(get_optimization_integrator)
):
    """Get system performance metrics"""
    try:
        current_metrics = performance_monitor.metrics_collector.collect_system_metrics()

        # Get historical metrics
        historical_metrics = list(performance_monitor.metrics_collector.system_metrics)[
            -samples:
        ]

        # Calculate aggregates
        if historical_metrics:
            avg_cpu = sum(m["cpu_percent"] for m in historical_metrics) / len(
                historical_metrics
            )
            avg_memory = sum(m["memory_percent"] for m in historical_metrics) / len(
                historical_metrics
            )
            max_memory_mb = max(m["memory_mb"] for m in historical_metrics)
        else:
            avg_cpu = avg_memory = max_memory_mb = 0

        return {
            "status_code": 200,
            "message": "System metrics retrieved",
            "data": {
                "current": current_metrics,
                "historical_samples": len(historical_metrics),
                "averages": {
                    "cpu_percent": avg_cpu,
                    "memory_percent": avg_memory,
                    "memory_mb": max_memory_mb,
                },
                "timestamp": datetime.now(),
            },
        }

    except Exception as e:
        logger.error(f"Error getting system metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/optimization/trigger")
async def trigger_optimization(
    request: OptimizationTriggerRequest,
    background_tasks: BackgroundTasks,
    integrator: Any = Depends(get_optimization_integrator),
):
    """Manually trigger an optimization action"""
    try:
        # Run optimization in background
        background_tasks.add_task(
            integrator.manual_optimization_trigger, request.optimization_type
        )

        return {
            "status_code": 202,
            "message": f"Optimization {request.optimization_type} triggered",
            "data": {
                "optimization_type": request.optimization_type,
                "status": "started",
                "timestamp": datetime.now(),
            },
        }

    except Exception as e:
        logger.error(f"Error triggering optimization: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/optimization/opportunities")
async def get_optimization_opportunities(
    integrator: Any = Depends(get_optimization_integrator),
):
    """Get current optimization opportunities"""
    try:
        opportunities = (
            performance_monitor.optimizer.evaluate_optimization_opportunities()
        )

        opportunities_data = []
        for opp in opportunities:
            opportunities_data.append(
                {
                    "action_type": opp.action_type,
                    "description": opp.description,
                    "priority": opp.priority,
                    "condition": opp.condition,
                    "cooldown_minutes": opp.cooldown_minutes,
                }
            )

        return {
            "status_code": 200,
            "message": "Optimization opportunities retrieved",
            "data": {
                "opportunities": opportunities_data,
                "total_count": len(opportunities_data),
                "timestamp": datetime.now(),
            },
        }

    except Exception as e:
        logger.error(f"Error getting optimization opportunities: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/adaptive/summary")
async def get_adaptive_summary(integrator: Any = Depends(get_optimization_integrator)):
    """Get adaptive optimization summary"""
    try:
        summary = adaptive_engine.get_adaptation_summary()

        return {
            "status_code": 200,
            "message": "Adaptive summary retrieved",
            "data": summary,
        }

    except Exception as e:
        logger.error(f"Error getting adaptive summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/adaptive/strategy")
async def update_optimization_strategy(
    request: StrategyUpdateRequest,
    integrator: Any = Depends(get_optimization_integrator),
):
    """Update optimization strategy"""
    try:
        strategy_map = {
            "conservative": OptimizationStrategy.CONSERVATIVE,
            "balanced": OptimizationStrategy.BALANCED,
            "aggressive": OptimizationStrategy.AGGRESSIVE,
            "adaptive": OptimizationStrategy.ADAPTIVE,
        }

        if request.strategy.lower() not in strategy_map:
            raise HTTPException(
                status_code=400, detail=f"Invalid strategy: {request.strategy}"
            )

        strategy = strategy_map[request.strategy.lower()]
        integrator.set_optimization_strategy(strategy)

        return {
            "status_code": 200,
            "message": f"Optimization strategy updated to {request.strategy}",
            "data": {"strategy": strategy.value, "timestamp": datetime.now()},
        }

    except Exception as e:
        logger.error(f"Error updating optimization strategy: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/thresholds")
async def get_performance_thresholds(
    integrator: Any = Depends(get_optimization_integrator),
):
    """Get current performance thresholds"""
    try:
        thresholds_data = []
        for threshold in performance_monitor.thresholds:
            thresholds_data.append(
                {
                    "metric_name": threshold.metric_name,
                    "warning_threshold": threshold.warning_threshold,
                    "critical_threshold": threshold.critical_threshold,
                    "window_minutes": threshold.window_minutes,
                    "consecutive_violations": threshold.consecutive_violations,
                }
            )

        return {
            "status_code": 200,
            "message": "Performance thresholds retrieved",
            "data": {
                "thresholds": thresholds_data,
                "total_count": len(thresholds_data),
            },
        }

    except Exception as e:
        logger.error(f"Error getting performance thresholds: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/thresholds")
async def create_performance_threshold(
    request: ThresholdUpdateRequest,
    integrator: Any = Depends(get_optimization_integrator),
):
    """Create or update a performance threshold"""
    try:
        threshold = PerformanceThreshold(
            metric_name=request.metric_name,
            warning_threshold=request.warning_threshold,
            critical_threshold=request.critical_threshold,
            window_minutes=request.window_minutes,
            consecutive_violations=request.consecutive_violations,
        )

        # Check if threshold already exists and update it
        existing_index = None
        for i, existing_threshold in enumerate(performance_monitor.thresholds):
            if existing_threshold.metric_name == request.metric_name:
                existing_index = i
                break

        if existing_index is not None:
            performance_monitor.thresholds[existing_index] = threshold
            action = "updated"
        else:
            performance_monitor.register_threshold(threshold)
            action = "created"

        return {
            "status_code": 201 if action == "created" else 200,
            "message": f"Performance threshold {action}",
            "data": {
                "metric_name": threshold.metric_name,
                "action": action,
                "threshold": {
                    "warning_threshold": threshold.warning_threshold,
                    "critical_threshold": threshold.critical_threshold,
                    "window_minutes": threshold.window_minutes,
                    "consecutive_violations": threshold.consecutive_violations,
                },
                "timestamp": datetime.now(),
            },
        }

    except Exception as e:
        logger.error(f"Error creating performance threshold: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/thresholds/{metric_name}")
async def delete_performance_threshold(
    metric_name: str, integrator: Any = Depends(get_optimization_integrator)
):
    """Delete a performance threshold"""
    try:
        initial_count = len(performance_monitor.thresholds)

        # Remove the threshold
        performance_monitor.thresholds = [
            t for t in performance_monitor.thresholds if t.metric_name != metric_name
        ]

        if len(performance_monitor.thresholds) == initial_count:
            raise HTTPException(
                status_code=404, detail=f"Threshold not found: {metric_name}"
            )

        return {
            "status_code": 200,
            "message": f"Performance threshold deleted: {metric_name}",
            "data": {"metric_name": metric_name, "timestamp": datetime.now()},
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting performance threshold: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/alerts/history")
async def get_alert_history(
    limit: int = Query(default=100, ge=1, le=1000),
    hours: int = Query(default=24, ge=1, le=168),  # 1 hour to 1 week
    integrator: Any = Depends(get_optimization_integrator),
):
    """Get alert history"""
    try:
        # Get recent alerts from optimization history
        cutoff_time = datetime.now() - timedelta(hours=hours)

        alert_history = []
        for record in performance_monitor.optimizer.action_history:
            if record.get("timestamp") and record["timestamp"] > cutoff_time:
                alert_history.append(
                    {
                        "timestamp": record["timestamp"],
                        "action_type": record.get("action_type"),
                        "success": record.get("success", False),
                        "duration_ms": record.get("duration_ms"),
                        "error": record.get("error"),
                    }
                )

        # Sort by timestamp (newest first)
        alert_history.sort(key=lambda x: x["timestamp"], reverse=True)

        return {
            "status_code": 200,
            "message": "Alert history retrieved",
            "data": {
                "alerts": alert_history[:limit],
                "total_count": len(alert_history),
                "filtered_hours": hours,
                "limit": limit,
            },
        }

    except Exception as e:
        logger.error(f"Error getting alert history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/monitoring/start")
async def start_monitoring(integrator: Any = Depends(get_optimization_integrator)):
    """Start performance monitoring"""
    try:
        if performance_monitor.monitoring_active:
            return {
                "status_code": 200,
                "message": "Performance monitoring is already active",
            }

        await integrator.initialize()

        return {
            "status_code": 200,
            "message": "Performance monitoring started",
            "data": {
                "started_at": datetime.now(),
                "services_integrated": len(integrator.service_integrations),
            },
        }

    except Exception as e:
        logger.error(f"Error starting monitoring: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/monitoring/stop")
async def stop_monitoring(integrator: Any = Depends(get_optimization_integrator)):
    """Stop performance monitoring"""
    try:
        if not performance_monitor.monitoring_active:
            return {
                "status_code": 200,
                "message": "Performance monitoring is not active",
            }

        performance_monitor.stop_monitoring()

        return {
            "status_code": 200,
            "message": "Performance monitoring stopped",
            "data": {"stopped_at": datetime.now()},
        }

    except Exception as e:
        logger.error(f"Error stopping monitoring: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Health check endpoint
@router.get("/health")
async def performance_health_check():
    """Health check for performance monitoring service"""
    try:
        health_status = {
            "status": "healthy",
            "monitoring_active": performance_monitor.monitoring_active,
            "metrics_count": len(performance_monitor.metrics_collector.metrics),
            "adaptive_engine_ready": adaptive_engine.pattern_learner.is_trained,
            "timestamp": datetime.now(),
        }

        return {
            "status_code": 200,
            "message": "Performance monitoring service is healthy",
            "data": health_status,
        }

    except Exception as e:
        logger.error(f"Performance health check failed: {e}")
        return {
            "status_code": 503,
            "message": "Performance monitoring service unavailable",
            "data": {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.now(),
            },
        }
