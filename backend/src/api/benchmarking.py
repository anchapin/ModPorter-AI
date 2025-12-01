"""
Benchmarking API Endpoints

This module provides REST API endpoints for running benchmarks,
accessing benchmark results, and managing performance validation.
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks, Query
from typing import List, Optional
from datetime import datetime, timedelta
from pydantic import BaseModel, Field
import logging

from services.benchmark_suite import benchmark_suite, BenchmarkConfiguration

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/benchmark", tags=["benchmarking"])


# Pydantic models for request/response
class BenchmarkConfigRequest(BaseModel):
    name: str = Field(..., description="Benchmark name")
    description: str = Field(..., description="Benchmark description")
    warmup_iterations: int = Field(default=10, ge=0, le=100)
    measurement_iterations: int = Field(default=100, ge=1, le=10000)
    concurrent_users: int = Field(default=1, ge=1, le=1000)
    ramp_up_time: float = Field(default=5.0, ge=0.0, le=300.0)
    duration: float = Field(default=60.0, ge=1.0, le=3600.0)
    think_time: float = Field(default=0.1, ge=0.0, le=10.0)
    timeout: float = Field(default=30.0, ge=1.0, le=300.0)
    enable_monitoring: bool = Field(default=True)
    collect_detailed_metrics: bool = Field(default=True)


class BenchmarkRunRequest(BaseModel):
    benchmark_type: str = Field(..., description="Type of benchmark to run")
    config: Optional[BenchmarkConfigRequest] = None
    establish_baseline: bool = Field(default=False)


class SuiteRunRequest(BaseModel):
    establish_baselines: bool = Field(default=False)
    benchmark_types: Optional[List[str]] = Field(
        default=None, description="Specific benchmarks to run"
    )


class BaselineRequest(BaseModel):
    benchmark_name: str = Field(..., description="Benchmark name to use as baseline")


@router.get("/status")
async def get_benchmark_status():
    """Get current benchmark suite status"""
    try:
        status = {
            "total_benchmarks": len(benchmark_suite.benchmark_results),
            "baselines_established": len(benchmark_suite.baseline_results),
            "comparisons_available": len(benchmark_suite.comparison_results),
            "last_run": None,
            "timestamp": datetime.now(),
        }

        # Find most recent benchmark
        if benchmark_suite.benchmark_results:
            latest_result = max(
                benchmark_suite.benchmark_results, key=lambda r: r.end_time
            )
            status["last_run"] = {
                "benchmark_name": latest_result.configuration.name,
                "end_time": latest_result.end_time,
                "success_rate": latest_result.success_rate,
                "avg_response_time": latest_result.avg_response_time,
                "throughput": latest_result.throughput,
            }

        return {
            "status_code": 200,
            "message": "Benchmark status retrieved",
            "data": status,
        }

    except Exception as e:
        logger.error(f"Error getting benchmark status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/run")
async def run_single_benchmark(
    request: BenchmarkRunRequest, background_tasks: BackgroundTasks
):
    """Run a single benchmark"""
    try:
        # Validate benchmark type
        valid_types = [
            "conversion",
            "cache",
            "batch_processing",
            "database",
            "mixed_workload",
            "stress_test",
        ]

        if request.benchmark_type not in valid_types:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid benchmark type. Valid types: {', '.join(valid_types)}",
            )

        # Prepare configuration
        config = None
        if request.config:
            config = BenchmarkConfiguration(
                name=request.config.name,
                description=request.config.description,
                warmup_iterations=request.config.warmup_iterations,
                measurement_iterations=request.config.measurement_iterations,
                concurrent_users=request.config.concurrent_users,
                ramp_up_time=request.config.ramp_up_time,
                duration=request.config.duration,
                think_time=request.config.think_time,
                timeout=request.config.timeout,
                enable_monitoring=request.config.enable_monitoring,
                collect_detailed_metrics=request.config.collect_detailed_metrics,
            )

        # Run benchmark in background
        background_tasks.add_task(
            _run_benchmark_background,
            request.benchmark_type,
            config,
            request.establish_baseline,
        )

        return {
            "status_code": 202,
            "message": f"Benchmark {request.benchmark_type} started",
            "data": {
                "benchmark_type": request.benchmark_type,
                "status": "started",
                "establish_baseline": request.establish_baseline,
                "timestamp": datetime.now(),
            },
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error starting benchmark: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/suite/run")
async def run_benchmark_suite(
    request: SuiteRunRequest, background_tasks: BackgroundTasks
):
    """Run the complete benchmark suite"""
    try:
        # Run in background to avoid blocking
        background_tasks.add_task(
            _run_suite_background, request.establish_baselines, request.benchmark_types
        )

        return {
            "status_code": 202,
            "message": "Benchmark suite started",
            "data": {
                "status": "started",
                "establish_baselines": request.establish_baselines,
                "specific_benchmarks": request.benchmark_types or ["all"],
                "timestamp": datetime.now(),
            },
        }

    except Exception as e:
        logger.error(f"Error starting benchmark suite: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/results")
async def get_benchmark_results(
    benchmark_name: Optional[str] = None,
    limit: int = Query(default=10, ge=1, le=100),
    include_details: bool = Query(default=False),
):
    """Get benchmark results"""
    try:
        if benchmark_name:
            # Get specific benchmark results
            results = [
                r
                for r in benchmark_suite.benchmark_results
                if r.configuration.name == benchmark_name
            ]

            if not results:
                raise HTTPException(
                    status_code=404,
                    detail=f"No results found for benchmark: {benchmark_name}",
                )

            results = results[-limit:]  # Get most recent results
        else:
            # Get all benchmark results
            results = sorted(
                benchmark_suite.benchmark_results,
                key=lambda r: r.end_time,
                reverse=True,
            )[:limit]

        # Format results
        formatted_results = []
        for result in results:
            result_data = {
                "name": result.configuration.name,
                "description": result.configuration.description,
                "start_time": result.start_time,
                "end_time": result.end_time,
                "duration": result.total_duration,
                "success_rate": result.success_rate,
                "avg_response_time": result.avg_response_time,
                "p95_response_time": result.p95_response_time,
                "throughput": result.throughput,
                "error_rate": result.error_rate,
                "total_operations": len(result.metrics),
                "configuration": {
                    "concurrent_users": result.configuration.concurrent_users,
                    "measurement_iterations": result.configuration.measurement_iterations,
                    "duration": result.configuration.duration,
                },
            }

            if include_details:
                result_data.update(
                    {
                        "p50_response_time": result.p50_response_time,
                        "p99_response_time": result.p99_response_time,
                        "min_response_time": result.min_response_time,
                        "max_response_time": result.max_response_time,
                        "cpu_usage_avg": result.cpu_usage_avg,
                        "memory_usage_avg": result.memory_usage_avg,
                        "system_metrics": result.system_metrics,
                    }
                )

                # Include detailed metrics if requested (with limit to avoid large responses)
                if len(result.metrics) <= 100:
                    result_data["detailed_metrics"] = [
                        {
                            "iteration": m.iteration,
                            "duration_ms": m.duration_ms,
                            "success": m.success,
                            "error_message": m.error_message,
                        }
                        for m in result.metrics
                    ]

            formatted_results.append(result_data)

        return {
            "status_code": 200,
            "message": "Benchmark results retrieved",
            "data": {
                "results": formatted_results,
                "total_count": len(formatted_results),
                "benchmark_name_filter": benchmark_name,
            },
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting benchmark results: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/results/{result_id}")
async def get_benchmark_result_details(result_id: str):
    """Get detailed information about a specific benchmark result"""
    try:
        # Find result by timestamp (using result_id as timestamp string)
        try:
            target_time = datetime.fromisoformat(result_id)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail="Invalid result_id format. Expected ISO datetime string.",
            )

        # Find matching result
        result = None
        for r in benchmark_suite.benchmark_results:
            if abs((r.end_time - target_time).total_seconds()) < 1:  # Within 1 second
                result = r
                break

        if not result:
            raise HTTPException(
                status_code=404, detail=f"Benchmark result not found: {result_id}"
            )

        # Format detailed result
        detailed_result = {
            "name": result.configuration.name,
            "description": result.configuration.description,
            "start_time": result.start_time,
            "end_time": result.end_time,
            "duration": result.total_duration,
            "configuration": {
                "warmup_iterations": result.configuration.warmup_iterations,
                "measurement_iterations": result.configuration.measurement_iterations,
                "concurrent_users": result.configuration.concurrent_users,
                "ramp_up_time": result.configuration.ramp_up_time,
                "duration": result.configuration.duration,
                "think_time": result.configuration.think_time,
                "timeout": result.configuration.timeout,
                "enable_monitoring": result.configuration.enable_monitoring,
                "collect_detailed_metrics": result.configuration.collect_detailed_metrics,
            },
            "statistics": {
                "success_rate": result.success_rate,
                "error_rate": result.error_rate,
                "avg_response_time": result.avg_response_time,
                "p50_response_time": result.p50_response_time,
                "p95_response_time": result.p95_response_time,
                "p99_response_time": result.p99_response_time,
                "min_response_time": result.min_response_time,
                "max_response_time": result.max_response_time,
                "throughput": result.throughput,
                "total_operations": len(result.metrics),
                "successful_operations": len([m for m in result.metrics if m.success]),
                "failed_operations": len([m for m in result.metrics if not m.success]),
            },
            "resource_usage": {
                "cpu_usage_avg": result.cpu_usage_avg,
                "memory_usage_avg": result.memory_usage_avg,
                "system_metrics": result.system_metrics,
            },
            "detailed_metrics": [
                {
                    "iteration": m.iteration,
                    "start_time": m.start_time,
                    "end_time": m.end_time,
                    "duration_ms": m.duration_ms,
                    "success": m.success,
                    "error_message": m.error_message,
                    "cpu_before": m.cpu_before,
                    "cpu_after": m.cpu_after,
                    "memory_before": m.memory_before,
                    "memory_after": m.memory_after,
                    "metadata": m.metadata,
                }
                for m in result.metrics
            ],
        }

        return {
            "status_code": 200,
            "message": "Benchmark result details retrieved",
            "data": detailed_result,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting benchmark result details: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/baselines")
async def get_benchmarks_baselines():
    """Get established benchmark baselines"""
    try:
        baselines = {}
        for name, result in benchmark_suite.baseline_results.items():
            baselines[name] = {
                "name": name,
                "description": result.configuration.description,
                "established_at": result.end_time,
                "success_rate": result.success_rate,
                "avg_response_time": result.avg_response_time,
                "p95_response_time": result.p95_response_time,
                "throughput": result.throughput,
                "error_rate": result.error_rate,
                "configuration": {
                    "concurrent_users": result.configuration.concurrent_users,
                    "measurement_iterations": result.configuration.measurement_iterations,
                    "duration": result.configuration.duration,
                },
            }

        return {
            "status_code": 200,
            "message": "Benchmark baselines retrieved",
            "data": {"baselines": baselines, "total_count": len(baselines)},
        }

    except Exception as e:
        logger.error(f"Error getting benchmark baselines: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/baselines")
async def establish_baseline(request: BaselineRequest):
    """Establish a baseline from the most recent benchmark result"""
    try:
        # Find most recent result for the specified benchmark
        results = [
            r
            for r in benchmark_suite.benchmark_results
            if r.configuration.name == request.benchmark_name
        ]

        if not results:
            raise HTTPException(
                status_code=404,
                detail=f"No results found for benchmark: {request.benchmark_name}",
            )

        # Use the most recent result
        latest_result = max(results, key=lambda r: r.end_time)
        benchmark_suite.establish_baseline(request.benchmark_name, latest_result)

        return {
            "status_code": 201,
            "message": f"Baseline established for {request.benchmark_name}",
            "data": {
                "benchmark_name": request.benchmark_name,
                "baseline_avg_response_time": latest_result.avg_response_time,
                "baseline_throughput": latest_result.throughput,
                "baseline_success_rate": latest_result.success_rate,
                "established_at": datetime.now(),
            },
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error establishing baseline: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/comparisons")
async def get_benchmark_comparisons():
    """Get benchmark comparisons with baselines"""
    try:
        return {
            "status_code": 200,
            "message": "Benchmark comparisons retrieved",
            "data": {
                "comparisons": benchmark_suite.comparison_results,
                "total_comparisons": len(benchmark_suite.comparison_results),
            },
        }

    except Exception as e:
        logger.error(f"Error getting benchmark comparisons: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/compare/{benchmark_name}")
async def compare_with_baseline(benchmark_name: str):
    """Compare the most recent benchmark result with its baseline"""
    try:
        # Find most recent result for the specified benchmark
        results = [
            r
            for r in benchmark_suite.benchmark_results
            if r.configuration.name == benchmark_name
        ]

        if not results:
            raise HTTPException(
                status_code=404,
                detail=f"No results found for benchmark: {benchmark_name}",
            )

        latest_result = max(results, key=lambda r: r.end_time)
        comparison = benchmark_suite.compare_with_baseline(latest_result)

        if comparison["status"] == "no_baseline":
            raise HTTPException(status_code=404, detail=comparison["message"])

        return {
            "status_code": 200,
            "message": f"Comparison generated for {benchmark_name}",
            "data": comparison,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error comparing with baseline: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/report")
async def get_benchmark_report():
    """Get comprehensive benchmark report"""
    try:
        report = benchmark_suite.generate_benchmark_report()

        return {
            "status_code": 200,
            "message": "Benchmark report generated",
            "data": report,
        }

    except Exception as e:
        logger.error(f"Error generating benchmark report: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/results")
async def clear_benchmark_results(
    benchmark_name: Optional[str] = None, older_than_days: Optional[int] = None
):
    """Clear benchmark results"""
    try:
        initial_count = len(benchmark_suite.benchmark_results)

        if benchmark_name:
            # Clear results for specific benchmark
            benchmark_suite.benchmark_results = [
                r
                for r in benchmark_suite.benchmark_results
                if r.configuration.name != benchmark_name
            ]
            cleared_count = initial_count - len(benchmark_suite.benchmark_results)
            message = f"Cleared {cleared_count} results for benchmark: {benchmark_name}"

        elif older_than_days:
            # Clear results older than specified days
            cutoff_date = datetime.now() - timedelta(days=older_than_days)
            benchmark_suite.benchmark_results = [
                r
                for r in benchmark_suite.benchmark_results
                if r.end_time >= cutoff_date
            ]
            cleared_count = initial_count - len(benchmark_suite.benchmark_results)
            message = (
                f"Cleared {cleared_count} results older than {older_than_days} days"
            )

        else:
            # Clear all results
            benchmark_suite.benchmark_results.clear()
            cleared_count = initial_count
            message = f"Cleared all {cleared_count} benchmark results"

        return {
            "status_code": 200,
            "message": message,
            "data": {
                "cleared_count": cleared_count,
                "remaining_count": len(benchmark_suite.benchmark_results),
            },
        }

    except Exception as e:
        logger.error(f"Error clearing benchmark results: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/baselines/{benchmark_name}")
async def delete_baseline(benchmark_name: str):
    """Delete a specific baseline"""
    try:
        if benchmark_name not in benchmark_suite.baseline_results:
            raise HTTPException(
                status_code=404, detail=f"Baseline not found: {benchmark_name}"
            )

        del benchmark_suite.baseline_results[benchmark_name]

        # Remove any related comparisons
        if benchmark_name in benchmark_suite.comparison_results:
            del benchmark_suite.comparison_results[benchmark_name]

        return {
            "status_code": 200,
            "message": f"Baseline deleted: {benchmark_name}",
            "data": {"benchmark_name": benchmark_name, "deleted_at": datetime.now()},
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting baseline: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Health check endpoint
@router.get("/health")
async def benchmark_health_check():
    """Health check for benchmarking service"""
    try:
        health_status = {
            "status": "healthy",
            "total_results": len(benchmark_suite.benchmark_results),
            "baselines_count": len(benchmark_suite.baseline_results),
            "comparisons_count": len(benchmark_suite.comparison_results),
            "timestamp": datetime.now(),
        }

        return {
            "status_code": 200,
            "message": "Benchmarking service is healthy",
            "data": health_status,
        }

    except Exception as e:
        logger.error(f"Benchmarking health check failed: {e}")
        return {
            "status_code": 503,
            "message": "Benchmarking service unavailable",
            "data": {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.now(),
            },
        }


# Background task functions
async def _run_benchmark_background(
    benchmark_type: str,
    config: Optional[BenchmarkConfiguration],
    establish_baseline: bool,
):
    """Background task to run a single benchmark"""
    try:
        # Map benchmark types to functions
        benchmark_functions = {
            "conversion": benchmark_suite.run_conversion_benchmark,
            "cache": benchmark_suite.run_cache_performance_benchmark,
            "batch_processing": benchmark_suite.run_batch_processing_benchmark,
            "database": benchmark_suite.run_database_benchmark,
            "mixed_workload": benchmark_suite.run_mixed_workload_benchmark,
            "stress_test": benchmark_suite.run_stress_test,
        }

        if benchmark_type not in benchmark_functions:
            logger.error(f"Unknown benchmark type: {benchmark_type}")
            return

        # Run the benchmark
        result = await benchmark_functions[benchmark_type](config)

        if establish_baseline:
            benchmark_suite.establish_baseline(result.configuration.name, result)

        logger.info(
            f"Benchmark {benchmark_type} completed: {result.avg_response_time:.2f}ms avg"
        )

    except Exception as e:
        logger.error(f"Background benchmark {benchmark_type} failed: {e}")


async def _run_suite_background(
    establish_baselines: bool, benchmark_types: Optional[List[str]]
):
    """Background task to run the benchmark suite"""
    try:
        if benchmark_types:
            # Run specific benchmarks only
            # This would require extending the benchmark suite to support selective execution
            logger.info(f"Running specific benchmarks: {benchmark_types}")

        # Run the full suite
        results = await benchmark_suite.run_full_benchmark_suite(establish_baselines)

        logger.info(
            f"Benchmark suite completed: {len(results['results'])} benchmarks run"
        )

    except Exception as e:
        logger.error(f"Background benchmark suite failed: {e}")
