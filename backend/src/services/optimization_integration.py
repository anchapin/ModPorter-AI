"""
Optimization Integration Layer

This module integrates the performance monitoring and adaptive optimization
systems with the existing ModPorter services and APIs.
"""

import asyncio
import logging
from typing import Dict, Any, Callable
from datetime import datetime
from contextlib import asynccontextmanager

from .performance_monitor import performance_monitor, PerformanceThreshold
from .adaptive_optimizer import adaptive_engine, OptimizationStrategy
from .cache_manager import cache_manager
from .batch_processing import batch_processor

logger = logging.getLogger(__name__)


class OptimizationIntegrator:
    """Integrates optimization systems with existing services"""

    def __init__(self):
        self.service_integrations: Dict[str, Any] = {}
        self.initialized = False

    async def initialize(self) -> None:
        """Initialize optimization integration"""
        if self.initialized:
            return

        try:
            # Start performance monitoring
            performance_monitor.start_monitoring()

            # Setup performance thresholds
            self._setup_performance_thresholds()

            # Register alert callbacks
            self._register_alert_callbacks()

            # Integrate with existing services
            await self._integrate_services()

            # Start adaptive analysis loop
            asyncio.create_task(self._adaptive_analysis_loop())

            self.initialized = True
            logger.info("Optimization integration initialized successfully")

        except Exception as e:
            logger.error(f"Error initializing optimization integration: {e}")
            raise

    def _setup_performance_thresholds(self) -> None:
        """Setup performance monitoring thresholds"""
        thresholds = [
            PerformanceThreshold(
                metric_name="conversion_avg_ms",
                warning_threshold=2000.0,
                critical_threshold=5000.0,
                window_minutes=5,
                consecutive_violations=3,
            ),
            PerformanceThreshold(
                metric_name="cache_hit_rate",
                warning_threshold=0.7,
                critical_threshold=0.5,
                window_minutes=10,
                consecutive_violations=2,
            ),
            PerformanceThreshold(
                metric_name="cpu_percent",
                warning_threshold=75.0,
                critical_threshold=90.0,
                window_minutes=3,
                consecutive_violations=2,
            ),
            PerformanceThreshold(
                metric_name="memory_percent",
                warning_threshold=80.0,
                critical_threshold=95.0,
                window_minutes=5,
                consecutive_violations=3,
            ),
        ]

        for threshold in thresholds:
            performance_monitor.register_threshold(threshold)

    def _register_alert_callbacks(self) -> None:
        """Register alert callback functions"""

        async def performance_alert_callback(alert_data: Dict[str, Any]) -> None:
            """Handle performance alerts"""
            severity = alert_data.get("severity", "warning")
            threshold = alert_data.get("threshold", "unknown")

            if severity == "critical":
                logger.error(f"CRITICAL PERFORMANCE ALERT: {threshold}")
                # Trigger immediate optimization actions
                await self._handle_critical_alert(alert_data)
            else:
                logger.warning(f"Performance alert: {threshold}")

        performance_monitor.register_alert_callback(performance_alert_callback)

    async def _handle_critical_alert(self, alert_data: Dict[str, Any]) -> None:
        """Handle critical performance alerts"""
        threshold = alert_data.get("threshold", "")

        # Emergency optimization actions based on threshold type
        if "cpu" in threshold.lower():
            # High CPU usage - reduce concurrent operations
            await self._emergency_cpu_optimization()
        elif "memory" in threshold.lower():
            # High memory usage - trigger cleanup
            await self._emergency_memory_cleanup()
        elif "conversion" in threshold.lower():
            # Slow conversions - optimize processing
            await self._emergency_conversion_optimization()

    async def _emergency_cpu_optimization(self) -> None:
        """Emergency CPU optimization"""
        logger.info("Executing emergency CPU optimization")

        # Reduce batch sizes
        if hasattr(batch_processor, "emergency_reduce_batch_size"):
            await batch_processor.emergency_reduce_batch_size()

        # Increase cache hit rate
        if hasattr(cache_manager, "emergency_increase_cache_size"):
            await cache_manager.emergency_increase_cache_size()

    async def _emergency_memory_cleanup(self) -> None:
        """Emergency memory cleanup"""
        logger.info("Executing emergency memory cleanup")

        # Force cache cleanup
        if hasattr(cache_manager, "emergency_cleanup"):
            await cache_manager.emergency_cleanup()

        # Force garbage collection
        import gc

        collected = gc.collect()
        logger.info(f"Emergency GC collected {collected} objects")

    async def _emergency_conversion_optimization(self) -> None:
        """Emergency conversion optimization"""
        logger.info("Executing emergency conversion optimization")

        # This would integrate with the conversion engine to optimize processing
        pass

    async def _integrate_services(self) -> None:
        """Integrate with existing services"""
        # Integration with cache manager
        if cache_manager:
            self.service_integrations["cache_manager"] = cache_manager
            self._setup_cache_monitoring()

        # Integration with batch processor
        if batch_processor:
            self.service_integrations["batch_processor"] = batch_processor
            self._setup_batch_monitoring()

        # Integration with database services would go here
        # This is a placeholder for database integration
        self._setup_database_monitoring()

    def _setup_cache_monitoring(self) -> None:
        """Setup cache performance monitoring"""

        async def cache_monitoring_wrapper():
            """Monitor cache performance metrics"""
            try:
                cache_stats = await cache_manager.get_cache_stats()

                # Update performance metrics
                if cache_stats:
                    from .performance_monitor import PerformanceMetric

                    metric = PerformanceMetric(
                        timestamp=datetime.now(),
                        operation_type="cache_access",
                        operation_id="cache_monitoring",
                        duration_ms=0,  # Not applicable for monitoring
                        cpu_percent=0,
                        memory_mb=0,
                        db_connections=0,
                        cache_hit_rate=cache_stats.get("hit_rate", 0.0),
                    )
                    performance_monitor.metrics_collector.record_metric(metric)

            except Exception as e:
                logger.error(f"Error in cache monitoring: {e}")

        # Schedule cache monitoring every 30 seconds
        asyncio.create_task(self._periodic_monitoring(cache_monitoring_wrapper, 30))

    def _setup_batch_monitoring(self) -> None:
        """Setup batch processing monitoring"""

        async def batch_monitoring_wrapper():
            """Monitor batch processing performance"""
            try:
                batch_stats = await batch_processor.get_batch_stats()

                # Update performance metrics
                if batch_stats:
                    from .performance_monitor import PerformanceMetric

                    metric = PerformanceMetric(
                        timestamp=datetime.now(),
                        operation_type="batch_processing",
                        operation_id="batch_monitoring",
                        duration_ms=0,
                        cpu_percent=0,
                        memory_mb=0,
                        db_connections=0,
                        cache_hit_rate=0,
                        queue_length=batch_stats.get("active_jobs", 0),
                    )
                    performance_monitor.metrics_collector.record_metric(metric)

            except Exception as e:
                logger.error(f"Error in batch monitoring: {e}")

        # Schedule batch monitoring every 15 seconds
        asyncio.create_task(self._periodic_monitoring(batch_monitoring_wrapper, 15))

    def _setup_database_monitoring(self) -> None:
        """Setup database monitoring"""

        async def db_monitoring_wrapper():
            """Monitor database performance"""
            try:
                # This would integrate with actual database connection pool
                # For now, we'll simulate with placeholder data
                db_connections = 10  # Placeholder
                db_cpu_usage = 5.0  # Placeholder

                from .performance_monitor import PerformanceMetric

                metric = PerformanceMetric(
                    timestamp=datetime.now(),
                    operation_type="database_access",
                    operation_id="db_monitoring",
                    duration_ms=0,
                    cpu_percent=db_cpu_usage,
                    memory_mb=0,
                    db_connections=db_connections,
                    cache_hit_rate=0,
                )
                performance_monitor.metrics_collector.record_metric(metric)

            except Exception as e:
                logger.error(f"Error in database monitoring: {e}")

        # Schedule database monitoring every 10 seconds
        asyncio.create_task(self._periodic_monitoring(db_monitoring_wrapper, 10))

    async def _periodic_monitoring(
        self, monitoring_func: Callable, interval_seconds: int
    ) -> None:
        """Run a monitoring function periodically"""
        while True:
            try:
                await monitoring_func()
            except Exception as e:
                logger.error(f"Error in periodic monitoring: {e}")

            await asyncio.sleep(interval_seconds)

    async def _adaptive_analysis_loop(self) -> None:
        """Main adaptive analysis loop"""
        while True:
            try:
                # Run adaptive analysis
                analysis_result = await adaptive_engine.analyze_and_adapt()

                # Log significant findings
                if analysis_result.get("is_anomalous"):
                    logger.warning(
                        f"Anomalous system state detected: {analysis_result.get('system_state', {})}"
                    )

                if analysis_result.get("predicted_action"):
                    logger.info(
                        f"Predicted optimal action: {analysis_result['predicted_action']}"
                    )

                # Store analysis results
                self._store_analysis_result(analysis_result)

            except Exception as e:
                logger.error(f"Error in adaptive analysis loop: {e}")

            # Run every 2 minutes
            await asyncio.sleep(120)

    def _store_analysis_result(self, result: Dict[str, Any]) -> None:
        """Store adaptive analysis results"""
        # This could store results in a database for later analysis
        # For now, we'll just log key metrics
        timestamp = result.get("timestamp", datetime.now())
        system_state = result.get("system_state", {})

        logger.debug(
            f"Analysis at {timestamp}: "
            f"CPU={system_state.get('cpu_percent', 0):.1f}%, "
            f"Memory={system_state.get('memory_percent', 0):.1f}%, "
            f"Anomalous={result.get('is_anomalous', False)}"
        )

    @asynccontextmanager
    async def monitor_conversion_operation(self, conversion_id: str):
        """Context manager for monitoring conversion operations"""
        async with performance_monitor.monitor_operation("conversion", conversion_id):
            try:
                yield
            except Exception:
                # Record failure for learning
                system_state = (
                    performance_monitor.metrics_collector.collect_system_metrics()
                )
                adaptive_engine.pattern_learner.add_training_sample(
                    system_state=system_state,
                    action_taken="conversion_failed",
                    performance_before=0,
                    performance_after=0,
                )
                raise

    @asynccontextmanager
    async def monitor_batch_operation(self, batch_id: str):
        """Context manager for monitoring batch operations"""
        async with performance_monitor.monitor_operation("batch_processing", batch_id):
            yield

    @asynccontextmanager
    async def monitor_cache_operation(self, operation_type: str):
        """Context manager for monitoring cache operations"""
        async with performance_monitor.monitor_operation(
            "cache_access", operation_type
        ):
            yield

    async def get_optimization_report(self) -> Dict[str, Any]:
        """Get comprehensive optimization report"""
        # Get performance monitoring report
        perf_report = performance_monitor.get_performance_report()

        # Get adaptive engine summary
        adaptive_summary = adaptive_engine.get_adaptation_summary()

        # Get service-specific metrics
        service_metrics = await self._get_service_metrics()

        return {
            "generated_at": datetime.now(),
            "performance_report": perf_report,
            "adaptive_summary": adaptive_summary,
            "service_metrics": service_metrics,
            "optimization_status": {
                "monitoring_active": performance_monitor.monitoring_active,
                "adaptive_engine_initialized": adaptive_engine.pattern_learner.is_trained,
                "services_integrated": len(self.service_integrations),
            },
        }

    async def _get_service_metrics(self) -> Dict[str, Any]:
        """Get metrics from integrated services"""
        metrics = {}

        try:
            # Cache metrics
            if "cache_manager" in self.service_integrations:
                cache_stats = await cache_manager.get_cache_stats()
                metrics["cache"] = cache_stats

            # Batch processing metrics
            if "batch_processor" in self.service_integrations:
                batch_stats = await batch_processor.get_batch_stats()
                metrics["batch_processing"] = batch_stats

        except Exception as e:
            logger.error(f"Error getting service metrics: {e}")
            metrics["error"] = str(e)

        return metrics

    async def manual_optimization_trigger(
        self, optimization_type: str
    ) -> Dict[str, Any]:
        """Manually trigger an optimization action"""
        try:
            if optimization_type == "cache_optimization":
                result = await adaptive_engine._optimize_cache_size()
            elif optimization_type == "db_optimization":
                result = await adaptive_engine._optimize_db_connections()
            elif optimization_type == "batch_optimization":
                result = await adaptive_engine._optimize_batch_size()
            elif optimization_type == "memory_cleanup":
                result = await adaptive_engine._cleanup_memory()
            else:
                raise ValueError(f"Unknown optimization type: {optimization_type}")

            logger.info(f"Manual optimization triggered: {optimization_type}")
            return {
                "success": True,
                "optimization_type": optimization_type,
                "result": result,
                "timestamp": datetime.now(),
            }

        except Exception as e:
            logger.error(f"Error in manual optimization: {e}")
            return {
                "success": False,
                "optimization_type": optimization_type,
                "error": str(e),
                "timestamp": datetime.now(),
            }

    def set_optimization_strategy(self, strategy: OptimizationStrategy) -> None:
        """Set the optimization strategy"""
        adaptive_engine.strategy = strategy
        logger.info(f"Optimization strategy changed to: {strategy.value}")


# Global optimization integrator instance
optimization_integrator = OptimizationIntegrator()
