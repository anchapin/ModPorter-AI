#!/usr/bin/env python3
"""
Automated Benchmarking Script

This script runs automated benchmarks for performance monitoring
and regression detection.
"""

import asyncio
import json
import logging
import argparse
import sys
from datetime import datetime
from pathlib import Path

import aiohttp
import aiofiles

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("automated_benchmarking.log"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)


async def run_benchmark(benchmark_type: str) -> dict:
    """Run benchmark of specified type"""
    timestamp = datetime.now()
    logger.info(f"Starting {benchmark_type} benchmark at {timestamp}")

    try:
        if benchmark_type == "baseline":
            return await run_baseline_comparison()
        elif benchmark_type == "snapshot":
            return await run_performance_snapshot()
        elif benchmark_type == "full":
            return await run_full_benchmark_suite()
        elif benchmark_type == "health":
            return await run_health_check()
        else:
            raise ValueError(f"Unknown benchmark type: {benchmark_type}")

    except Exception as e:
        logger.error(f"❌ {benchmark_type} benchmark failed: {e}")
        return {
            "benchmark_type": benchmark_type,
            "timestamp": timestamp.isoformat(),
            "success": False,
            "error": str(e),
        }


async def run_baseline_comparison() -> dict:
    """Run baseline comparison benchmark"""
    logger.info("📊 Running baseline comparison benchmark")

    # Load latest baseline
    baseline_file = Path("latest_benchmark_results.json")
    if not baseline_file.exists():
        logger.warning("No baseline found, skipping comparison")
        return await run_performance_snapshot()

    with open(baseline_file, "r") as f:
        baseline = json.load(f)

    # Run current benchmark
    current_metrics = await collect_current_metrics()

    # Compare with baseline
    comparison = compare_with_baseline(current_metrics, baseline)

    # Check for regressions
    regressions = detect_regressions(comparison, current_metrics)

    # Save results
    result = {
        "benchmark_type": "baseline_comparison",
        "timestamp": datetime.now().isoformat(),
        "baseline": baseline,
        "current_metrics": current_metrics,
        "comparison": comparison,
        "regressions": regressions,
        "success": True,
    }

    # Save to results file
    results_file = Path(
        f"benchmark_results_baseline_comparison_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    )
    with open(results_file, "w") as f:
        json.dump(result, f, default=str, indent=2)

    # Check for alerts
    if regressions:
        await trigger_regression_alerts(regressions)

    logger.info("✅ Baseline comparison completed")
    return result


async def run_performance_snapshot() -> dict:
    """Run performance snapshot benchmark"""
    logger.info("📸 Taking performance snapshot")

    metrics = await collect_current_metrics()

    result = {
        "benchmark_type": "performance_snapshot",
        "timestamp": datetime.now().isoformat(),
        "metrics": metrics,
        "success": True,
    }

    # Save snapshot
    snapshot_file = Path(
        f"performance_snapshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    )
    with open(snapshot_file, "w") as f:
        json.dump(result, f, default=str, indent=2)

    logger.info("✅ Performance snapshot completed")
    return result


async def run_full_benchmark_suite() -> dict:
    """Run full comprehensive benchmark suite"""
    logger.info("🏃 Running full benchmark suite")

    # Import and run benchmark suite
    sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))
    from run_performance_benchmarks import PerformanceBenchmark

    benchmark = PerformanceBenchmark()
    results = await benchmark.run_all_benchmarks()

    # Add benchmark type info
    results["benchmark_type"] = "full_benchmark_suite"
    results["full_benchmark"] = True

    # Save results
    results_file = Path(
        f"full_benchmark_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    )
    with open(results_file, "w") as f:
        json.dump(results, f, default=str, indent=2)

    logger.info("✅ Full benchmark suite completed")
    return results


async def run_health_check() -> dict:
    """Run quick health check benchmark"""
    logger.info("🏥 Running health check benchmark")

    health_results = {
        "benchmark_type": "health_check",
        "timestamp": datetime.now().isoformat(),
        "checks": {},
    }

    # API health checks
    health_results["checks"]["api"] = await check_api_health()
    health_results["checks"]["database"] = await check_database_health()
    health_results["checks"]["cache"] = await check_cache_health()
    health_results["checks"]["system"] = await check_system_health()

    # Calculate overall health
    total_checks = len(health_results["checks"])
    passed_checks = sum(
        1
        for check in health_results["checks"].values()
        if check.get("available", False)
    )

    health_results["overall_health"] = (
        (passed_checks / total_checks) * 100 if total_checks > 0 else 0
    )
    health_results["success"] = True

    # Check for immediate issues
    critical_issues = []
    for check_name, check_result in health_results["checks"].items():
        if not check_result.get("available", True):
            critical_issues.append(f"{check_name} unavailable")

    if critical_issues:
        await trigger_health_alert(critical_issues)

    logger.info(
        f"✅ Health check completed - Overall health: {health_results['overall_health']:.1f}%"
    )
    return health_results


async def collect_current_metrics() -> dict:
    """Collect current system and application metrics"""
    try:
        # Use existing benchmark functionality
        sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))
        from run_performance_benchmarks import PerformanceBenchmark

        benchmark = PerformanceBenchmark()
        results = await benchmark.run_system_benchmarks()
        return results.get("system", {})
    except Exception as e:
        logger.error(f"Error collecting metrics: {e}")
        return {}


def compare_with_baseline(current_metrics: dict, baseline: dict) -> dict:
    """Compare current metrics with baseline"""
    comparison = {}

    if "system" in baseline:
        baseline_system = baseline["system"]
        current_system = current_metrics

        for metric_type in ["cpu", "memory", "disk"]:
            if metric_type in baseline_system and metric_type in current_system:
                if metric_type == "cpu":
                    baseline_value = baseline_system[metric_type].get(
                        "current_cpu_percent", 0
                    )
                    current_value = current_system[metric_type].get(
                        "current_cpu_percent", 0
                    )
                elif metric_type == "memory":
                    baseline_value = baseline_system[metric_type].get(
                        "current_memory_percent", 0
                    )
                    current_value = current_system[metric_type].get(
                        "current_memory_percent", 0
                    )
                elif metric_type == "disk":
                    baseline_value = baseline_system[metric_type].get(
                        "disk_usage_percent", 0
                    )
                    current_value = current_system[metric_type].get(
                        "disk_usage_percent", 0
                    )

                if baseline_value > 0:
                    change_percent = (
                        (current_value - baseline_value) / baseline_value
                    ) * 100
                    comparison[metric_type] = {
                        "baseline": baseline_value,
                        "current": current_value,
                        "change_percent": change_percent,
                        "change_direction": (
                            "increased" if change_percent > 0 else "decreased"
                        ),
                    }

    return comparison


def detect_regressions(comparison: dict, current_metrics: dict) -> list:
    """Detect performance regressions based on comparison"""
    regressions = []

    thresholds = {
        "cpu": 15,  # 15% increase
        "memory": 20,  # 20% increase
        "disk": 30,  # 30% increase
    }

    for metric_type, metric_data in comparison.items():
        if metric_type in thresholds:
            change_percent = metric_data.get("change_percent", 0)
            if change_percent > thresholds[metric_type]:
                regressions.append(
                    {
                        "metric": metric_type,
                        "change_percent": change_percent,
                        "current_value": metric_data.get("current", 0),
                        "baseline_value": metric_data.get("baseline", 0),
                        "severity": (
                            "high"
                            if change_percent > thresholds[metric_type] * 1.5
                            else "medium"
                        ),
                        "detected_at": datetime.now().isoformat(),
                    }
                )

    return regressions


async def trigger_regression_alerts(regressions: list):
    """Trigger alerts for detected regressions"""
    logger.warning(
        f"🚨 Triggering regression alerts for {len(regressions)} regressions"
    )

    for regression in regressions:
        alert_data = {
            "alert_type": "performance_regression",
            "severity": regression["severity"],
            "metric": regression["metric"],
            "change_percent": regression["change_percent"],
            "current_value": regression["current_value"],
            "baseline_value": regression["baseline_value"],
            "timestamp": regression["detected_at"],
            "environment": "production",
        }

        # Store alert
        await store_alert(alert_data)

        # Send notification (would integrate with actual notification system)
        logger.warning(
            f"Performance regression detected: {regression['metric']} increased by {regression['change_percent']:.1f}%"
        )


async def trigger_health_alert(issues: list):
    """Trigger alerts for health issues"""
    logger.error(f"🚨 Triggering health alerts for {len(issues)} issues")

    for issue in issues:
        alert_data = {
            "alert_type": "health_check_failure",
            "severity": "critical",
            "issue": issue,
            "timestamp": datetime.now().isoformat(),
            "environment": "production",
        }

        await store_alert(alert_data)
        logger.error(f"Health check failed: {issue}")


async def store_alert(alert_data: dict):
    """Store alert in alerts file"""
    try:
        alerts_file = Path("performance_alerts.json")
        alerts = []

        if alerts_file.exists():
            with open(alerts_file, "r") as f:
                alerts = json.load(f)

        alerts.append(alert_data)

        # Keep only last 1000 alerts
        if len(alerts) > 1000:
            alerts = alerts[-1000:]

        with open(alerts_file, "w") as f:
            json.dump(alerts, f, default=str, indent=2)

    except Exception as e:
        logger.error(f"Error storing alert: {e}")


# Health check functions
async def check_api_health() -> dict:
    """Check API health"""
    try:
        proc = await asyncio.create_subprocess_shell(
            "curl -f -s -w %{http_code} http://localhost:8000/api/v1/health",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
        return_code = int(stdout.strip()) if stdout.strip().isdigit() else 500

        return {
            "available": return_code == 200,
            "status_code": return_code,
            "response_time_ms": 0,  # Would measure actual time
        }
    except Exception as e:
        return {"available": False, "error": str(e)}


async def check_database_health() -> dict:
    """Check database health"""
    try:
        proc = await asyncio.create_subprocess_shell(
            "docker exec modporter-ai-postgres-1 pg_isready -U postgres -d modporter_staging",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
        return_code = proc.returncode

        return {"available": return_code == 0, "status_code": return_code}
    except Exception as e:
        return {"available": False, "error": str(e)}


async def check_cache_health() -> dict:
    """Check cache health"""
    try:
        proc = await asyncio.create_subprocess_shell(
            "docker exec modporter-ai-redis-1 redis-cli ping",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()

        return {
            "available": stdout.strip() == "PONG",
            "status_code": 0 if stdout.strip() == "PONG" else 1,
        }
    except Exception as e:
        return {"available": False, "error": str(e)}


async def check_system_health() -> dict:
    """Check basic system health"""
    import psutil

    try:
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage("/")

        return {
            "available": True,
            "cpu_percent": cpu_percent,
            "memory_percent": memory.percent,
            "disk_percent": (disk.used / disk.total) * 100,
        }
    except Exception as e:
        return {"available": False, "error": str(e)}


async def main():
    """Main function"""
    parser = argparse.ArgumentParser(
        description="Automated benchmarking script"
    )
    parser.add_argument(
        "--type",
        required=True,
        choices=["baseline", "snapshot", "full", "health"],
        help="Type of benchmark to run",
    )
    args = parser.parse_args()

    try:
        result = await run_benchmark(args.type)
        print(f"✅ {args.type} benchmark completed successfully")
        if "regressions" in result and result["regressions"]:
            print(f"🚨 {len(result['regressions'])} regressions detected")
        print(f"📄 Results saved with timestamp: {result['timestamp']}")
        return 0
    except Exception as e:
        print(f"❌ Benchmark failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
