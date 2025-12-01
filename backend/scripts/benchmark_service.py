#!/usr/bin/env python3
"""
Benchmark Service for Staging Environment

This service runs automated benchmarks to establish performance baselines
and monitor performance regressions in the staging environment.
"""

import asyncio
import logging
import json
import os
import sys
from datetime import datetime
from typing import Dict, Any, List

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
import uvicorn
import redis.asyncio as redis
from redis.asyncio import Redis as AsyncRedis
from sqlalchemy.ext.asyncio import create_async_engine

from services.benchmark_suite import BenchmarkSuite
from services.performance_monitor import performance_monitor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/app/logs/benchmark_service.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(title="Benchmark Service", version="1.0.0")

# Global variables
benchmark_suite: BenchmarkSuite = None
redis_client: redis.Redis = None
engine = None

@app.on_event("startup")
async def startup_event():
    """Initialize the benchmark service"""
    global benchmark_suite, redis_client, engine

    try:
        # Initialize Redis connection
        redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379')
        redis_client = AsyncRedis.from_url(redis_url)

        # Initialize database connection
        database_url = os.getenv('DATABASE_URL', 'postgresql+asyncpg://postgres:password@localhost:5432/modporter_staging')
        engine = create_async_engine(database_url, echo=False)

        # Initialize benchmark suite
        benchmark_suite = BenchmarkSuite(redis_client=redis_client, engine=engine)

        # Start periodic benchmarking
        asyncio.create_task(periodic_benchmarking())

        logger.info("Benchmark service initialized successfully")

    except Exception as e:
        logger.error(f"Failed to initialize benchmark service: {e}")
        raise

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    if redis_client:
        await redis_client.close()
    if engine:
        await engine.dispose()
    logger.info("Benchmark service shutdown complete")

async def periodic_benchmarking():
    """Run benchmarks periodically"""
    interval = int(os.getenv('BENCHMARK_INTERVAL', '1800'))  # 30 minutes default

    while True:
        try:
            logger.info("Starting periodic benchmark run")
            results = await run_full_benchmark_suite()

            # Store results in Redis
            await redis_client.setex(
                'latest_benchmark_results',
                86400,  # 24 hours TTL
                json.dumps(results, default=str)
            )

            # Check for regressions
            regressions = await check_performance_regressions(results)
            if regressions:
                logger.warning(f"Performance regressions detected: {regressions}")
                await trigger_regression_alert(regressions)

            logger.info(f"Periodic benchmark completed. Results: {len(results)} metrics")

        except Exception as e:
            logger.error(f"Error in periodic benchmarking: {e}")

        await asyncio.sleep(interval)

async def run_full_benchmark_suite() -> Dict[str, Any]:
    """Run complete benchmark suite"""
    try:
        # Initialize performance monitoring
        await performance_monitor.start_monitoring()

        # Run benchmarks
        results = await benchmark_suite.run_comprehensive_benchmark()

        return {
            'timestamp': datetime.now(),
            'environment': 'staging',
            'results': results,
            'success': True
        }

    except Exception as e:
        logger.error(f"Benchmark suite failed: {e}")
        return {
            'timestamp': datetime.now(),
            'environment': 'staging',
            'error': str(e),
            'success': False
        }

async def check_performance_regressions(current_results: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Check for performance regressions compared to baseline"""
    regressions = []

    try:
        # Get previous results for comparison
        previous_results_json = await redis_client.get('baseline_benchmark_results')
        if not previous_results_json:
            logger.info("No baseline results found, setting current as baseline")
            await redis_client.setex(
                'baseline_benchmark_results',
                86400 * 7,  # 7 days TTL
                json.dumps(current_results, default=str)
            )
            return regressions

        previous_results = json.loads(previous_results_json)

        # Compare key metrics
        current_metrics = current_results.get('results', {})
        previous_metrics = previous_results.get('results', {})

        key_metrics = [
            'conversion_avg_ms',
            'cache_hit_rate',
            'cpu_percent',
            'memory_percent',
            'response_time_p95'
        ]

        for metric in key_metrics:
            current_value = current_metrics.get(metric)
            previous_value = previous_metrics.get(metric)

            if current_value is None or previous_value is None:
                continue

            # Calculate percentage change
            if previous_value != 0:
                change_percent = ((current_value - previous_value) / previous_value) * 100

                # Define regression thresholds
                if metric in ['conversion_avg_ms', 'cpu_percent', 'memory_percent', 'response_time_p95']:
                    # Higher values are worse
                    if change_percent > 15:  # 15% degradation threshold
                        regressions.append({
                            'metric': metric,
                            'previous_value': previous_value,
                            'current_value': current_value,
                            'change_percent': change_percent,
                            'severity': 'high' if change_percent > 30 else 'medium'
                        })
                elif metric == 'cache_hit_rate':
                    # Lower values are worse
                    if change_percent < -10:  # 10% degradation threshold
                        regressions.append({
                            'metric': metric,
                            'previous_value': previous_value,
                            'current_value': current_value,
                            'change_percent': change_percent,
                            'severity': 'high' if change_percent < -20 else 'medium'
                        })

        return regressions

    except Exception as e:
        logger.error(f"Error checking performance regressions: {e}")
        return []

async def trigger_regression_alert(regressions: List[Dict[str, Any]]):
    """Trigger alert for performance regressions"""
    try:
        alert_data = {
            'alert_type': 'performance_regression',
            'timestamp': datetime.now(),
            'environment': 'staging',
            'regressions': regressions,
            'severity': 'high' if any(r['severity'] == 'high' for r in regressions) else 'medium'
        }

        # Store alert in Redis
        await redis_client.lpush('performance_alerts', json.dumps(alert_data, default=str))
        await redis_client.expire('performance_alerts', 86400)  # 24 hours TTL

        # Log alert
        logger.warning(f"Performance regression alert triggered: {alert_data}")

    except Exception as e:
        logger.error(f"Error triggering regression alert: {e}")

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        # Check Redis connection
        await redis_client.ping()

        # Check database connection
        async with engine.begin() as conn:
            await conn.execute("SELECT 1")

        return {
            "status": "healthy",
            "timestamp": datetime.now(),
            "service": "benchmark-service"
        }

    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail=f"Service unhealthy: {e}")

@app.get("/metrics")
async def get_metrics():
    """Get benchmark metrics"""
    try:
        # Get latest benchmark results
        latest_results_json = await redis_client.get('latest_benchmark_results')
        if latest_results_json:
            latest_results = json.loads(latest_results_json)
        else:
            latest_results = {"message": "No benchmark results available"}

        # Get baseline results
        baseline_results_json = await redis_client.get('baseline_benchmark_results')
        if baseline_results_json:
            baseline_results = json.loads(baseline_results_json)
        else:
            baseline_results = {"message": "No baseline results available"}

        return {
            "latest_results": latest_results,
            "baseline_results": baseline_results,
            "service_status": "running"
        }

    except Exception as e:
        logger.error(f"Error getting metrics: {e}")
        raise HTTPException(status_code=500, detail=f"Error retrieving metrics: {e}")

@app.post("/run-benchmark")
async def trigger_benchmark():
    """Manually trigger a benchmark run"""
    try:
        logger.info("Manual benchmark triggered via API")
        results = await run_full_benchmark_suite()

        # Store results
        await redis_client.setex(
            'latest_benchmark_results',
            86400,
            json.dumps(results, default=str)
        )

        return JSONResponse(content=results)

    except Exception as e:
        logger.error(f"Manual benchmark failed: {e}")
        raise HTTPException(status_code=500, detail=f"Benchmark failed: {e}")

@app.post("/set-baseline")
async def set_baseline():
    """Set current results as baseline"""
    try:
        latest_results_json = await redis_client.get('latest_benchmark_results')
        if not latest_results_json:
            raise HTTPException(status_code=404, detail="No benchmark results available")

        await redis_client.setex(
            'baseline_benchmark_results',
            86400 * 7,  # 7 days TTL
            latest_results_json
        )

        logger.info("Baseline updated successfully")
        return {"message": "Baseline updated successfully"}

    except Exception as e:
        logger.error(f"Error setting baseline: {e}")
        raise HTTPException(status_code=500, detail=f"Error setting baseline: {e}")

@app.get("/alerts")
async def get_alerts():
    """Get performance alerts"""
    try:
        alerts = []
        alert_list = await redis_client.lrange('performance_alerts', 0, -1)

        for alert_json in alert_list:
            alerts.append(json.loads(alert_json))

        return {
            "alerts": alerts,
            "count": len(alerts)
        }

    except Exception as e:
        logger.error(f"Error getting alerts: {e}")
        raise HTTPException(status_code=500, detail=f"Error retrieving alerts: {e}")

if __name__ == "__main__":
    uvicorn.run(
        "benchmark_service:app",
        host="0.0.0.0",
        port=8090,
        reload=False,
        log_level="info"
    )