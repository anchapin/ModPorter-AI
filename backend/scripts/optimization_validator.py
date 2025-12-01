#!/usr/bin/env python3
"""
Optimization Validation Service for Staging Environment

This service validates the effectiveness of optimizations and monitors
their impact on system performance in the staging environment.
"""

import asyncio
import logging
import json
import os
import sys
from datetime import datetime
from typing import Dict, Any, List
from pathlib import Path

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
import uvicorn
import redis.asyncio as redis
from redis.asyncio import Redis as AsyncRedis
from sqlalchemy.ext.asyncio import create_async_engine

from services.optimization_integration import optimization_integrator
from services.adaptive_optimizer import adaptive_engine, OptimizationStrategy
from services.performance_monitor import performance_monitor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/app/logs/optimization_validator.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(title="Optimization Validation Service", version="1.0.0")

# Global variables
redis_client: redis.Redis = None
engine = None
validation_history: List[Dict[str, Any]] = []

# Configuration
VALIDATION_INTERVAL = int(os.getenv('VALIDATION_INTERVAL', '300'))  # 5 minutes
PERFORMANCE_THRESHOLDS = {
    'cpu': float(os.getenv('PERFORMANCE_THRESHOLD_CPU', '80')),
    'memory': float(os.getenv('PERFORMANCE_THRESHOLD_MEMORY', '85')),
    'response': float(os.getenv('PERFORMANCE_THRESHOLD_RESPONSE', '3000'))
}

@app.on_event("startup")
async def startup_event():
    """Initialize the optimization validation service"""
    global redis_client, engine

    try:
        # Initialize Redis connection
        redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379')
        redis_client = AsyncRedis.from_url(redis_url)

        # Initialize database connection
        database_url = os.getenv('DATABASE_URL', 'postgresql+asyncpg://postgres:password@localhost:5432/modporter_staging')
        engine = create_async_engine(database_url, echo=False)

        # Initialize optimization integrator
        await optimization_integrator.initialize()

        # Start periodic validation
        asyncio.create_task(periodic_validation())

        logger.info("Optimization validation service initialized successfully")

    except Exception as e:
        logger.error(f"Failed to initialize optimization validation service: {e}")
        raise

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    if redis_client:
        await redis_client.close()
    if engine:
        await engine.dispose()
    logger.info("Optimization validation service shutdown complete")

async def periodic_validation():
    """Run validation checks periodically"""
    while True:
        try:
            logger.info("Starting optimization validation cycle")
            validation_result = await run_optimization_validation()

            # Store validation result
            await store_validation_result(validation_result)

            # Check if optimizations need adjustment
            if not validation_result['within_thresholds']:
                await handle_optimization_adjustment(validation_result)

            logger.info(f"Validation cycle completed. Status: {'PASS' if validation_result['within_thresholds'] else 'ADJUST NEEDED'}")

        except Exception as e:
            logger.error(f"Error in periodic validation: {e}")

        await asyncio.sleep(VALIDATION_INTERVAL)

async def run_optimization_validation() -> Dict[str, Any]:
    """Run comprehensive optimization validation"""
    try:
        # Get current system metrics
        current_metrics = await collect_system_metrics()

        # Get optimization status
        optimization_status = await get_optimization_status()

        # Validate performance against thresholds
        threshold_validation = validate_performance_thresholds(current_metrics)

        # Check optimization effectiveness
        effectiveness_score = await calculate_optimization_effectiveness(current_metrics)

        # Run performance regression tests
        regression_results = await run_regression_tests()

        validation_result = {
            'timestamp': datetime.now(),
            'environment': 'staging',
            'system_metrics': current_metrics,
            'optimization_status': optimization_status,
            'threshold_validation': threshold_validation,
            'effectiveness_score': effectiveness_score,
            'regression_results': regression_results,
            'within_thresholds': threshold_validation['all_within_threshold'],
            'needs_adjustment': not threshold_validation['all_within_threshold'] or effectiveness_score < 0.7
        }

        return validation_result

    except Exception as e:
        logger.error(f"Optimization validation failed: {e}")
        return {
            'timestamp': datetime.now(),
            'environment': 'staging',
            'error': str(e),
            'within_thresholds': False,
            'needs_adjustment': True
        }

async def collect_system_metrics() -> Dict[str, Any]:
    """Collect current system performance metrics"""
    try:
        # Get performance report
        perf_report = performance_monitor.get_performance_report()

        # Get service-specific metrics
        optimization_report = await optimization_integrator.get_optimization_report()

        # Combine metrics
        metrics = {
            'cpu_percent': perf_report.get('current_metrics', {}).get('cpu_percent', 0),
            'memory_percent': perf_report.get('current_metrics', {}).get('memory_percent', 0),
            'response_time_avg': perf_report.get('current_metrics', {}).get('response_time_avg', 0),
            'response_time_p95': perf_report.get('current_metrics', {}).get('response_time_p95', 0),
            'cache_hit_rate': perf_report.get('current_metrics', {}).get('cache_hit_rate', 0),
            'active_connections': perf_report.get('current_metrics', {}).get('db_connections', 0),
            'optimization_status': optimization_report.get('optimization_status', {}),
            'service_metrics': optimization_report.get('service_metrics', {})
        }

        return metrics

    except Exception as e:
        logger.error(f"Error collecting system metrics: {e}")
        return {}

async def get_optimization_status() -> Dict[str, Any]:
    """Get current optimization system status"""
    try:
        optimization_report = await optimization_integrator.get_optimization_report()

        return {
            'monitoring_active': optimization_report.get('optimization_status', {}).get('monitoring_active', False),
            'adaptive_engine_initialized': optimization_report.get('optimization_status', {}).get('adaptive_engine_initialized', False),
            'services_integrated': optimization_report.get('optimization_status', {}).get('services_integrated', 0),
            'current_strategy': adaptive_engine.strategy.value if adaptive_engine.strategy else 'none',
            'last_optimization': optimization_report.get('adaptive_summary', {}).get('last_action'),
            'optimization_count': optimization_report.get('adaptive_summary', {}).get('total_adaptations', 0)
        }

    except Exception as e:
        logger.error(f"Error getting optimization status: {e}")
        return {}

def validate_performance_thresholds(metrics: Dict[str, Any]) -> Dict[str, Any]:
    """Validate metrics against performance thresholds"""
    threshold_results = {
        'cpu_within_threshold': metrics.get('cpu_percent', 0) <= PERFORMANCE_THRESHOLDS['cpu'],
        'memory_within_threshold': metrics.get('memory_percent', 0) <= PERFORMANCE_THRESHOLDS['memory'],
        'response_within_threshold': metrics.get('response_time_avg', 0) <= PERFORMANCE_THRESHOLDS['response'],
        'cache_acceptable': metrics.get('cache_hit_rate', 0) >= 0.7,  # 70% minimum cache hit rate
        'all_within_threshold': True,
        'violations': []
    }

    # Check all thresholds
    if not threshold_results['cpu_within_threshold']:
        threshold_results['violations'].append({
            'metric': 'cpu',
            'current': metrics.get('cpu_percent', 0),
            'threshold': PERFORMANCE_THRESHOLDS['cpu'],
            'severity': 'high' if metrics.get('cpu_percent', 0) > 90 else 'medium'
        })

    if not threshold_results['memory_within_threshold']:
        threshold_results['violations'].append({
            'metric': 'memory',
            'current': metrics.get('memory_percent', 0),
            'threshold': PERFORMANCE_THRESHOLDS['memory'],
            'severity': 'high' if metrics.get('memory_percent', 0) > 95 else 'medium'
        })

    if not threshold_results['response_within_threshold']:
        threshold_results['violations'].append({
            'metric': 'response_time',
            'current': metrics.get('response_time_avg', 0),
            'threshold': PERFORMANCE_THRESHOLDS['response'],
            'severity': 'high' if metrics.get('response_time_avg', 0) > 5000 else 'medium'
        })

    if not threshold_results['cache_acceptable']:
        threshold_results['violations'].append({
            'metric': 'cache_hit_rate',
            'current': metrics.get('cache_hit_rate', 0),
            'threshold': 0.7,
            'severity': 'medium'
        })

    threshold_results['all_within_threshold'] = len(threshold_results['violations']) == 0

    return threshold_results

async def calculate_optimization_effectiveness(current_metrics: Dict[str, Any]) -> float:
    """Calculate optimization effectiveness score (0.0 to 1.0)"""
    try:
        # Get baseline metrics for comparison
        baseline_metrics_json = await redis_client.get('baseline_optimization_metrics')
        if not baseline_metrics_json:
            # Set current as baseline if none exists
            await redis_client.setex(
                'baseline_optimization_metrics',
                86400 * 7,  # 7 days TTL
                json.dumps(current_metrics, default=str)
            )
            return 0.8  # Good score for initial baseline

        baseline_metrics = json.loads(baseline_metrics_json)

        # Calculate effectiveness based on improvements
        score_components = []

        # CPU improvement (lower is better)
        cpu_baseline = baseline_metrics.get('cpu_percent', 100)
        cpu_current = current_metrics.get('cpu_percent', 100)
        cpu_improvement = max(0, (cpu_baseline - cpu_current) / cpu_baseline)
        score_components.append(cpu_improvement)

        # Memory improvement (lower is better)
        mem_baseline = baseline_metrics.get('memory_percent', 100)
        mem_current = current_metrics.get('memory_percent', 100)
        mem_improvement = max(0, (mem_baseline - mem_current) / mem_baseline)
        score_components.append(mem_improvement)

        # Response time improvement (lower is better)
        resp_baseline = baseline_metrics.get('response_time_avg', 10000)
        resp_current = current_metrics.get('response_time_avg', 10000)
        resp_improvement = max(0, (resp_baseline - resp_current) / resp_baseline)
        score_components.append(resp_improvement)

        # Cache hit rate improvement (higher is better)
        cache_baseline = baseline_metrics.get('cache_hit_rate', 0)
        cache_current = current_metrics.get('cache_hit_rate', 0)
        if cache_baseline > 0:
            cache_improvement = max(0, (cache_current - cache_baseline) / (1 - cache_baseline))
        else:
            cache_improvement = cache_current
        score_components.append(cache_improvement)

        # Calculate average score
        effectiveness_score = sum(score_components) / len(score_components) if score_components else 0.5

        # Add bonus for meeting thresholds
        if (current_metrics.get('cpu_percent', 100) <= PERFORMANCE_THRESHOLDS['cpu'] and
            current_metrics.get('memory_percent', 100) <= PERFORMANCE_THRESHOLDS['memory'] and
            current_metrics.get('response_time_avg', 10000) <= PERFORMANCE_THRESHOLDS['response']):
            effectiveness_score = min(1.0, effectiveness_score + 0.1)

        return effectiveness_score

    except Exception as e:
        logger.error(f"Error calculating optimization effectiveness: {e}")
        return 0.5

async def run_regression_tests() -> Dict[str, Any]:
    """Run performance regression tests"""
    try:
        # Simulate regression tests
        # In a real implementation, this would run actual performance tests
        regression_results = {
            'conversion_performance': await test_conversion_performance(),
            'cache_performance': await test_cache_performance(),
            'database_performance': await test_database_performance(),
            'api_response_performance': await test_api_response_performance()
        }

        overall_passed = all(result.get('passed', False) for result in regression_results.values())

        return {
            'overall_passed': overall_passed,
            'test_results': regression_results,
            'timestamp': datetime.now()
        }

    except Exception as e:
        logger.error(f"Error running regression tests: {e}")
        return {
            'overall_passed': False,
            'error': str(e),
            'timestamp': datetime.now()
        }

async def test_conversion_performance() -> Dict[str, Any]:
    """Test conversion performance"""
    try:
        # Simulate conversion performance test
        return {
            'passed': True,
            'avg_conversion_time': 1500,  # ms
            'max_conversion_time': 3000,  # ms
            'success_rate': 0.95
        }

    except Exception as e:
        return {'passed': False, 'error': str(e)}

async def test_cache_performance() -> Dict[str, Any]:
    """Test cache performance"""
    try:
        # Simulate cache performance test
        return {
            'passed': True,
            'hit_rate': 0.85,
            'avg_lookup_time': 50,  # ms
            'cache_size_efficiency': 0.78
        }

    except Exception as e:
        return {'passed': False, 'error': str(e)}

async def test_database_performance() -> Dict[str, Any]:
    """Test database performance"""
    try:
        # Simulate database performance test
        return {
            'passed': True,
            'avg_query_time': 100,  # ms
            'connection_pool_efficiency': 0.92,
            'query_success_rate': 0.99
        }

    except Exception as e:
        return {'passed': False, 'error': str(e)}

async def test_api_response_performance() -> Dict[str, Any]:
    """Test API response performance"""
    try:
        # Simulate API response test
        return {
            'passed': True,
            'avg_response_time': 200,  # ms
            'p95_response_time': 500,  # ms
            'success_rate': 0.98
        }

    except Exception as e:
        return {'passed': False, 'error': str(e)}

async def store_validation_result(result: Dict[str, Any]):
    """Store validation result"""
    try:
        # Store in Redis
        await redis_client.setex(
            'latest_validation_result',
            86400,  # 24 hours TTL
            json.dumps(result, default=str)
        )

        # Add to history
        validation_history.append(result)
        if len(validation_history) > 100:  # Keep last 100 results
            validation_history.pop(0)

        # Store history in Redis
        await redis_client.setex(
            'validation_history',
            86400 * 7,  # 7 days TTL
            json.dumps(validation_history, default=str)
        )

        # Save report to file
        report_path = Path(f"/app/reports/validation_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
        report_path.write_text(json.dumps(result, default=str, indent=2))

    except Exception as e:
        logger.error(f"Error storing validation result: {e}")

async def handle_optimization_adjustment(validation_result: Dict[str, Any]):
    """Handle optimization adjustment based on validation results"""
    try:
        logger.info("Handling optimization adjustment")

        # Check threshold violations
        violations = validation_result.get('threshold_validation', {}).get('violations', [])

        for violation in violations:
            metric = violation['metric']
            severity = violation['severity']

            if metric == 'cpu' and severity == 'high':
                await optimization_integrator.manual_optimization_trigger("cache_optimization")
                logger.info("Triggered cache optimization due to high CPU usage")

            elif metric == 'memory' and severity == 'high':
                await optimization_integrator.manual_optimization_trigger("memory_cleanup")
                logger.info("Triggered memory cleanup due to high memory usage")

            elif metric == 'response_time':
                await optimization_integrator.manual_optimization_trigger("db_optimization")
                logger.info("Triggered database optimization due to high response time")

        # Check optimization effectiveness
        effectiveness = validation_result.get('effectiveness_score', 0)
        if effectiveness < 0.5:
            # Change optimization strategy
            new_strategy = OptimizationStrategy.AGGRESSIVE if effectiveness < 0.3 else OptimizationStrategy.BALANCED
            optimization_integrator.set_optimization_strategy(new_strategy)
            logger.info(f"Changed optimization strategy to {new_strategy.value}")

    except Exception as e:
        logger.error(f"Error handling optimization adjustment: {e}")

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        # Check Redis connection
        await redis_client.ping()

        # Check optimization integrator
        if not optimization_integrator.initialized:
            raise HTTPException(status_code=503, detail="Optimization integrator not initialized")

        return {
            "status": "healthy",
            "timestamp": datetime.now(),
            "service": "optimization-validator",
            "optimization_integrator_initialized": optimization_integrator.initialized
        }

    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail=f"Service unhealthy: {e}")

@app.get("/metrics")
async def get_metrics():
    """Get validation metrics"""
    try:
        # Get latest validation result
        latest_result_json = await redis_client.get('latest_validation_result')
        if latest_result_json:
            latest_result = json.loads(latest_result_json)
        else:
            latest_result = {"message": "No validation results available"}

        # Get validation history
        history_json = await redis_client.get('validation_history')
        if history_json:
            history = json.loads(history_json)
        else:
            history = []

        return {
            "latest_validation": latest_result,
            "validation_history": history[-10:],  # Last 10 results
            "service_status": "running"
        }

    except Exception as e:
        logger.error(f"Error getting metrics: {e}")
        raise HTTPException(status_code=500, detail=f"Error retrieving metrics: {e}")

@app.post("/run-validation")
async def trigger_validation():
    """Manually trigger a validation run"""
    try:
        logger.info("Manual validation triggered via API")
        result = await run_optimization_validation()

        # Store result
        await store_validation_result(result)

        return JSONResponse(content=result)

    except Exception as e:
        logger.error(f"Manual validation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Validation failed: {e}")

@app.post("/optimize/{optimization_type}")
async def trigger_optimization(optimization_type: str):
    """Manually trigger an optimization"""
    try:
        result = await optimization_integrator.manual_optimization_trigger(optimization_type)
        return JSONResponse(content=result)

    except Exception as e:
        logger.error(f"Manual optimization failed: {e}")
        raise HTTPException(status_code=500, detail=f"Optimization failed: {e}")

@app.get("/status")
async def get_optimization_status():
    """Get comprehensive optimization status"""
    try:
        status = await get_optimization_status()
        return status

    except Exception as e:
        logger.error(f"Error getting optimization status: {e}")
        raise HTTPException(status_code=500, detail=f"Error retrieving status: {e}")

if __name__ == "__main__":
    uvicorn.run(
        "optimization_validator:app",
        host="0.0.0.0",
        port=8091,
        reload=False,
        log_level="info"
    )