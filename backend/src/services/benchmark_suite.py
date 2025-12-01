"""
Comprehensive Benchmark Suite for Performance Validation

This module provides a complete benchmarking framework to validate
optimizations, measure performance improvements, and ensure system
reliability under various load conditions.
"""

import asyncio
import time
import statistics
import logging
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from collections import deque
from datetime import datetime
import numpy as np
import psutil
import random
import uuid


logger = logging.getLogger(__name__)


@dataclass
class BenchmarkConfiguration:
    """Configuration for benchmark execution"""

    name: str
    description: str
    warmup_iterations: int = 10
    measurement_iterations: int = 100
    concurrent_users: int = 1
    ramp_up_time: float = 5.0  # seconds
    duration: float = 60.0  # seconds
    think_time: float = 0.1  # seconds between operations
    timeout: float = 30.0  # seconds per operation
    enable_monitoring: bool = True
    collect_detailed_metrics: bool = True


@dataclass
class BenchmarkMetric:
    """Individual benchmark measurement"""

    iteration: int
    start_time: datetime
    end_time: datetime
    duration_ms: float
    success: bool
    error_message: Optional[str] = None
    cpu_before: float = 0.0
    cpu_after: float = 0.0
    memory_before: float = 0.0
    memory_after: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class BenchmarkResult:
    """Complete benchmark execution result"""

    configuration: BenchmarkConfiguration
    metrics: List[BenchmarkMetric]
    start_time: datetime
    end_time: datetime
    total_duration: float
    success_rate: float
    avg_response_time: float
    p50_response_time: float
    p95_response_time: float
    p99_response_time: float
    min_response_time: float
    max_response_time: float
    throughput: float  # operations per second
    error_rate: float
    cpu_usage_avg: float
    memory_usage_avg: float
    system_metrics: Dict[str, Any] = field(default_factory=dict)


class LoadGenerator:
    """Generates realistic load patterns for benchmarking"""

    def __init__(self):
        self.active_workers: List[asyncio.Task] = []
        self.completed_operations: deque = deque(maxlen=10000)
        self.error_count = 0

    async def generate_constant_load(
        self, operation_func: Callable, config: BenchmarkConfiguration
    ) -> List[BenchmarkMetric]:
        """Generate constant load pattern"""
        logger.info(
            f"Starting constant load with {config.concurrent_users} concurrent users"
        )

        tasks = []
        semaphore = asyncio.Semaphore(config.concurrent_users)

        async def worker(worker_id: int) -> List[BenchmarkMetric]:
            worker_metrics = []

            async with semaphore:
                # Ramp up delay
                ramp_delay = (config.ramp_up_time / config.concurrent_users) * worker_id
                await asyncio.sleep(ramp_delay)

                end_time = time.time() + config.duration

                iteration = 0
                while time.time() < end_time:
                    try:
                        metric = await self._execute_operation(
                            operation_func, iteration, worker_id, config
                        )
                        worker_metrics.append(metric)

                        if not metric.success:
                            self.error_count += 1

                        # Think time
                        if config.think_time > 0:
                            await asyncio.sleep(config.think_time)

                        iteration += 1

                    except Exception as e:
                        logger.error(f"Worker {worker_id} error: {e}")
                        break

            return worker_metrics

        # Start worker tasks
        for i in range(config.concurrent_users):
            task = asyncio.create_task(worker(i))
            tasks.append(task)

        # Wait for all tasks to complete
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Flatten results
        all_metrics = []
        for result in results:
            if isinstance(result, list):
                all_metrics.extend(result)
            else:
                logger.error(f"Worker failed: {result}")

        return all_metrics

    async def generate_spike_load(
        self,
        operation_func: Callable,
        config: BenchmarkConfiguration,
        spike_factor: float = 3.0,
        spike_duration: float = 10.0,
    ) -> List[BenchmarkMetric]:
        """Generate load with periodic spikes"""
        logger.info(f"Starting spike load with factor {spike_factor}")

        all_metrics = []

        # Normal load phase
        normal_duration = config.duration - spike_duration
        if normal_duration > 0:
            normal_config = BenchmarkConfiguration(
                **config.__dict__, duration=normal_duration
            )
            normal_metrics = await self.generate_constant_load(
                operation_func, normal_config
            )
            all_metrics.extend(normal_metrics)

        # Spike load phase
        if spike_duration > 0:
            spike_config = BenchmarkConfiguration(
                **config.__dict__,
                concurrent_users=int(config.concurrent_users * spike_factor),
                duration=spike_duration,
                ramp_up_time=2.0,
            )
            spike_metrics = await self.generate_constant_load(
                operation_func, spike_config
            )
            all_metrics.extend(spike_metrics)

        return all_metrics

    async def _execute_operation(
        self,
        operation_func: Callable,
        iteration: int,
        worker_id: int,
        config: BenchmarkConfiguration,
    ) -> BenchmarkMetric:
        """Execute a single operation and collect metrics"""
        start_time = datetime.now()

        # Collect system metrics before operation
        cpu_before = psutil.cpu_percent()
        memory_before = psutil.virtual_memory().used / 1024 / 1024  # MB

        success = True
        error_message = None

        try:
            # Execute operation with timeout
            async with asyncio.timeout(config.timeout):
                if asyncio.iscoroutinefunction(operation_func):
                    await operation_func(iteration, worker_id)
                else:
                    # Run sync function in thread pool
                    loop = asyncio.get_event_loop()
                    await loop.run_in_executor(
                        None, operation_func, iteration, worker_id
                    )

        except asyncio.TimeoutError:
            success = False
            error_message = "Operation timed out"
        except Exception as e:
            success = False
            error_message = str(e)

        end_time = datetime.now()

        # Collect system metrics after operation
        cpu_after = psutil.cpu_percent()
        memory_after = psutil.virtual_memory().used / 1024 / 1024  # MB

        duration_ms = (end_time - start_time).total_seconds() * 1000

        return BenchmarkMetric(
            iteration=iteration,
            start_time=start_time,
            end_time=end_time,
            duration_ms=duration_ms,
            success=success,
            error_message=error_message,
            cpu_before=cpu_before,
            cpu_after=cpu_after,
            memory_before=memory_before,
            memory_after=memory_after,
            metadata={"worker_id": worker_id},
        )


class BenchmarkSuite:
    """Comprehensive benchmark suite for ModPorter optimization validation"""

    def __init__(self):
        self.load_generator = LoadGenerator()
        self.benchmark_results: List[BenchmarkResult] = []
        self.baseline_results: Dict[str, BenchmarkResult] = {}
        self.comparison_results: Dict[str, Dict[str, Any]] = {}

    async def run_conversion_benchmark(
        self, config: Optional[BenchmarkConfiguration] = None
    ) -> BenchmarkResult:
        """Benchmark conversion operation performance"""
        if config is None:
            config = BenchmarkConfiguration(
                name="conversion_performance",
                description="Benchmark conversion operation performance",
                concurrent_users=5,
                measurement_iterations=50,
                duration=30.0,
            )

        logger.info(f"Running conversion benchmark: {config.name}")

        async def conversion_operation(iteration: int, worker_id: int):
            """Mock conversion operation for benchmarking"""
            # Simulate conversion work
            await asyncio.sleep(0.1 + random.uniform(-0.05, 0.05))

            # Simulate some CPU work
            result = sum(i * i for i in range(1000))
            return result

        # Warmup phase
        if config.warmup_iterations > 0:
            logger.info(f"Warming up with {config.warmup_iterations} iterations")
            warmup_config = BenchmarkConfiguration(
                **config.__dict__,
                measurement_iterations=config.warmup_iterations,
                enable_monitoring=False,
            )
            await self._run_single_benchmark(conversion_operation, warmup_config)

        # Measurement phase
        logger.info(
            f"Running measurement phase with {config.measurement_iterations} iterations"
        )
        result = await self._run_single_benchmark(conversion_operation, config)

        self.benchmark_results.append(result)
        logger.info(
            f"Conversion benchmark completed: {result.avg_response_time:.2f}ms avg, {result.throughput:.2f} ops/sec"
        )

        return result

    async def run_cache_performance_benchmark(
        self, config: Optional[BenchmarkConfiguration] = None
    ) -> BenchmarkResult:
        """Benchmark cache performance under load"""
        if config is None:
            config = BenchmarkConfiguration(
                name="cache_performance",
                description="Benchmark cache operation performance",
                concurrent_users=10,
                measurement_iterations=1000,
                duration=60.0,
            )

        logger.info(f"Running cache benchmark: {config.name}")

        async def cache_operation(iteration: int, worker_id: int):
            """Mock cache operation for benchmarking"""
            f"benchmark_key_{iteration % 100}"  # Reuse keys to test cache hits
            value = {"data": f"value_{iteration}", "timestamp": time.time()}

            # Simulate cache get/set operations
            if iteration % 3 == 0:
                # Cache miss simulation
                await asyncio.sleep(0.001)  # Simulate cache miss latency
                return value
            else:
                # Cache hit simulation
                await asyncio.sleep(0.0001)  # Simulate cache hit latency
                return value

        result = await self._run_single_benchmark(cache_operation, config)
        self.benchmark_results.append(result)

        logger.info(
            f"Cache benchmark completed: {result.avg_response_time:.2f}ms avg, {result.throughput:.2f} ops/sec"
        )
        return result

    async def run_batch_processing_benchmark(
        self, config: Optional[BenchmarkConfiguration] = None
    ) -> BenchmarkResult:
        """Benchmark batch processing performance"""
        if config is None:
            config = BenchmarkConfiguration(
                name="batch_processing_performance",
                description="Benchmark batch processing performance",
                concurrent_users=3,
                measurement_iterations=30,
                duration=45.0,
            )

        logger.info(f"Running batch processing benchmark: {config.name}")

        async def batch_operation(iteration: int, worker_id: int):
            """Mock batch processing operation"""
            batch_size = 50 + random.randint(-10, 10)

            # Simulate batch processing work
            tasks = []
            for i in range(batch_size):

                async def process_item(item_id):
                    await asyncio.sleep(0.001)  # Simulate item processing
                    return f"processed_{item_id}"

                tasks.append(process_item(i))

            results = await asyncio.gather(*tasks)
            return len(results)

        result = await self._run_single_benchmark(batch_operation, config)
        self.benchmark_results.append(result)

        logger.info(
            f"Batch processing benchmark completed: {result.avg_response_time:.2f}ms avg, {result.throughput:.2f} ops/sec"
        )
        return result

    async def run_database_benchmark(
        self, config: Optional[BenchmarkConfiguration] = None
    ) -> BenchmarkResult:
        """Benchmark database operation performance"""
        if config is None:
            config = BenchmarkConfiguration(
                name="database_performance",
                description="Benchmark database operation performance",
                concurrent_users=8,
                measurement_iterations=200,
                duration=30.0,
            )

        logger.info(f"Running database benchmark: {config.name}")

        async def database_operation(iteration: int, worker_id: int):
            """Mock database operation"""
            # Simulate different types of database operations
            operation_type = iteration % 4

            if operation_type == 0:
                # SELECT query
                await asyncio.sleep(0.005)
                return {"id": iteration, "data": f"select_result_{iteration}"}
            elif operation_type == 1:
                # INSERT query
                await asyncio.sleep(0.01)
                return {"inserted_id": uuid.uuid4()}
            elif operation_type == 2:
                # UPDATE query
                await asyncio.sleep(0.008)
                return {"updated_rows": 1}
            else:
                # Complex query with JOINs
                await asyncio.sleep(0.02)
                return {"results": [{"id": i} for i in range(10)]}

        result = await self._run_single_benchmark(database_operation, config)
        self.benchmark_results.append(result)

        logger.info(
            f"Database benchmark completed: {result.avg_response_time:.2f}ms avg, {result.throughput:.2f} ops/sec"
        )
        return result

    async def run_mixed_workload_benchmark(
        self, config: Optional[BenchmarkConfiguration] = None
    ) -> BenchmarkResult:
        """Benchmark mixed realistic workload"""
        if config is None:
            config = BenchmarkConfiguration(
                name="mixed_workload_performance",
                description="Benchmark mixed realistic workload",
                concurrent_users=15,
                measurement_iterations=100,
                duration=90.0,
            )

        logger.info(f"Running mixed workload benchmark: {config.name}")

        async def mixed_operation(iteration: int, worker_id: int):
            """Mixed workload operation"""
            operation_weights = [0.4, 0.3, 0.2, 0.1]  # Conversion, Cache, Batch, DB
            operation_type = np.random.choice(4, p=operation_weights)

            if operation_type == 0:
                # Conversion operation (30%)
                await asyncio.sleep(0.1 + random.uniform(-0.02, 0.02))
                return {"conversion_id": iteration, "status": "completed"}
            elif operation_type == 1:
                # Cache operation (30%)
                await asyncio.sleep(0.001)
                return {"cache_hit": iteration % 2 == 0}
            elif operation_type == 2:
                # Batch operation (20%)
                batch_items = random.randint(10, 50)
                await asyncio.sleep(0.002 * batch_items)
                return {"batch_size": batch_items, "processed": batch_items}
            else:
                # Database operation (10%)
                await asyncio.sleep(0.008)
                return {"query_time": 0.008, "rows": random.randint(1, 100)}

        result = await self._run_single_benchmark(mixed_operation, config)
        self.benchmark_results.append(result)

        logger.info(
            f"Mixed workload benchmark completed: {result.avg_response_time:.2f}ms avg, {result.throughput:.2f} ops/sec"
        )
        return result

    async def run_stress_test(
        self, config: Optional[BenchmarkConfiguration] = None
    ) -> BenchmarkResult:
        """Run stress test with high load"""
        if config is None:
            config = BenchmarkConfiguration(
                name="stress_test",
                description="High-load stress test",
                concurrent_users=50,
                measurement_iterations=500,
                duration=120.0,
                ramp_up_time=30.0,
            )

        logger.info(f"Running stress test: {config.name}")

        async def stress_operation(iteration: int, worker_id: int):
            """Stress test operation with varying complexity"""
            # Vary operation complexity
            complexity = random.choice(["simple", "medium", "complex"])

            if complexity == "simple":
                await asyncio.sleep(0.01)
                return {"type": "simple", "result": iteration}
            elif complexity == "medium":
                await asyncio.sleep(0.05)
                # Some CPU work
                result = sum(i * i for i in range(1000))
                return {"type": "medium", "result": result}
            else:
                await asyncio.sleep(0.1)
                # More CPU work
                result = sum(i * i for i in range(5000))
                return {"type": "complex", "result": result}

        result = await self._run_single_benchmark(stress_operation, config)
        self.benchmark_results.append(result)

        logger.info(
            f"Stress test completed: {result.avg_response_time:.2f}ms avg, {result.throughput:.2f} ops/sec"
        )
        return result

    async def _run_single_benchmark(
        self, operation_func: Callable, config: BenchmarkConfiguration
    ) -> BenchmarkResult:
        """Run a single benchmark with the given configuration"""
        start_time = datetime.now()

        # Collect initial system metrics
        initial_metrics = self._collect_system_metrics()

        # Generate load based on configuration
        if config.concurrent_users == 1:
            # Single-threaded execution
            metrics = await self._run_single_threaded(operation_func, config)
        else:
            # Multi-threaded load generation
            metrics = await self.load_generator.generate_constant_load(
                operation_func, config
            )

        end_time = datetime.now()
        total_duration = (end_time - start_time).total_seconds()

        # Calculate result statistics
        successful_metrics = [m for m in metrics if m.success]
        response_times = [m.duration_ms for m in successful_metrics]

        if not response_times:
            # All operations failed
            return BenchmarkResult(
                configuration=config,
                metrics=metrics,
                start_time=start_time,
                end_time=end_time,
                total_duration=total_duration,
                success_rate=0.0,
                avg_response_time=0.0,
                p50_response_time=0.0,
                p95_response_time=0.0,
                p99_response_time=0.0,
                min_response_time=0.0,
                max_response_time=0.0,
                throughput=0.0,
                error_rate=1.0,
                cpu_usage_avg=0.0,
                memory_usage_avg=0.0,
                system_metrics=initial_metrics,
            )

        success_rate = len(successful_metrics) / len(metrics) if metrics else 0
        error_rate = 1.0 - success_rate
        throughput = (
            len(successful_metrics) / total_duration if total_duration > 0 else 0
        )

        # Calculate percentiles
        sorted_times = sorted(response_times)
        p50 = np.percentile(sorted_times, 50)
        p95 = np.percentile(sorted_times, 95)
        p99 = np.percentile(sorted_times, 99)

        # Calculate resource usage averages
        cpu_usage = [m.cpu_after for m in successful_metrics]
        memory_usage = [m.memory_after for m in successful_metrics]
        cpu_avg = statistics.mean(cpu_usage) if cpu_usage else 0
        memory_avg = statistics.mean(memory_usage) if memory_usage else 0

        # Collect final system metrics
        final_metrics = self._collect_system_metrics()

        return BenchmarkResult(
            configuration=config,
            metrics=metrics,
            start_time=start_time,
            end_time=end_time,
            total_duration=total_duration,
            success_rate=success_rate,
            avg_response_time=statistics.mean(response_times),
            p50_response_time=p50,
            p95_response_time=p95,
            p99_response_time=p99,
            min_response_time=min(response_times),
            max_response_time=max(response_times),
            throughput=throughput,
            error_rate=error_rate,
            cpu_usage_avg=cpu_avg,
            memory_usage_avg=memory_avg,
            system_metrics={**initial_metrics, **final_metrics},
        )

    async def _run_single_threaded(
        self, operation_func: Callable, config: BenchmarkConfiguration
    ) -> List[BenchmarkMetric]:
        """Run benchmark in single thread"""
        metrics = []

        for i in range(config.measurement_iterations):
            try:
                metric = await self.load_generator._execute_operation(
                    operation_func, i, 0, config
                )
                metrics.append(metric)

                # Think time
                if config.think_time > 0:
                    await asyncio.sleep(config.think_time)

            except Exception as e:
                logger.error(f"Single-threaded iteration {i} failed: {e}")

        return metrics

    def _collect_system_metrics(self) -> Dict[str, Any]:
        """Collect comprehensive system metrics"""
        return {
            "cpu_percent": psutil.cpu_percent(),
            "memory_percent": psutil.virtual_memory().percent,
            "memory_mb": psutil.virtual_memory().used / 1024 / 1024,
            "disk_usage": psutil.disk_usage("/").percent
            if hasattr(psutil, "disk_usage")
            else 0,
            "process_count": len(psutil.pids()),
            "timestamp": time.time(),
        }

    def establish_baseline(self, benchmark_name: str, result: BenchmarkResult) -> None:
        """Establish baseline result for comparison"""
        self.baseline_results[benchmark_name] = result
        logger.info(f"Baseline established for {benchmark_name}")

    def compare_with_baseline(self, current_result: BenchmarkResult) -> Dict[str, Any]:
        """Compare current result with established baseline"""
        benchmark_name = current_result.configuration.name

        if benchmark_name not in self.baseline_results:
            return {
                "status": "no_baseline",
                "message": f"No baseline found for {benchmark_name}",
            }

        baseline = self.baseline_results[benchmark_name]

        # Calculate improvements
        response_time_improvement = (
            (
                (baseline.avg_response_time - current_result.avg_response_time)
                / baseline.avg_response_time
                * 100
            )
            if baseline.avg_response_time > 0
            else 0
        )

        throughput_improvement = (
            (
                (current_result.throughput - baseline.throughput)
                / baseline.throughput
                * 100
            )
            if baseline.throughput > 0
            else 0
        )

        success_rate_change = current_result.success_rate - baseline.success_rate
        error_rate_change = current_result.error_rate - baseline.error_rate

        comparison = {
            "benchmark_name": benchmark_name,
            "status": "compared",
            "baseline_avg_response_time": baseline.avg_response_time,
            "current_avg_response_time": current_result.avg_response_time,
            "response_time_improvement_percent": response_time_improvement,
            "baseline_throughput": baseline.throughput,
            "current_throughput": current_result.throughput,
            "throughput_improvement_percent": throughput_improvement,
            "baseline_success_rate": baseline.success_rate,
            "current_success_rate": current_result.success_rate,
            "success_rate_change": success_rate_change,
            "baseline_error_rate": baseline.error_rate,
            "current_error_rate": current_result.error_rate,
            "error_rate_change": error_rate_change,
            "is_improvement": response_time_improvement > 0
            or throughput_improvement > 0
            or success_rate_change > 0,
        }

        self.comparison_results[benchmark_name] = comparison
        return comparison

    def generate_benchmark_report(self) -> Dict[str, Any]:
        """Generate comprehensive benchmark report"""
        report = {
            "generated_at": datetime.now(),
            "summary": {
                "total_benchmarks": len(self.benchmark_results),
                "successful_benchmarks": len(
                    [r for r in self.benchmark_results if r.success_rate > 0.9]
                ),
                "baseline_established": len(self.baseline_results),
                "comparisons_made": len(self.comparison_results),
            },
            "benchmarks": [],
            "comparisons": self.comparison_results,
            "recommendations": [],
        }

        # Add benchmark details
        for result in self.benchmark_results:
            benchmark_data = {
                "name": result.configuration.name,
                "description": result.configuration.description,
                "success_rate": result.success_rate,
                "avg_response_time": result.avg_response_time,
                "p95_response_time": result.p95_response_time,
                "throughput": result.throughput,
                "error_rate": result.error_rate,
                "total_operations": len(result.metrics),
                "duration": result.total_duration,
            }
            report["benchmarks"].append(benchmark_data)

        # Generate recommendations
        recommendations = []
        for result in self.benchmark_results:
            if result.success_rate < 0.95:
                recommendations.append(
                    {
                        "benchmark": result.configuration.name,
                        "type": "reliability",
                        "priority": "high",
                        "message": f"Low success rate ({result.success_rate:.1%}) - investigate error patterns",
                    }
                )

            if result.avg_response_time > 1000:  # > 1 second
                recommendations.append(
                    {
                        "benchmark": result.configuration.name,
                        "type": "performance",
                        "priority": "medium",
                        "message": f"High average response time ({result.avg_response_time:.1f}ms) - consider optimization",
                    }
                )

            if result.error_rate > 0.05:  # > 5% error rate
                recommendations.append(
                    {
                        "benchmark": result.configuration.name,
                        "type": "stability",
                        "priority": "high",
                        "message": f"High error rate ({result.error_rate:.1%}) - review error handling",
                    }
                )

        report["recommendations"] = recommendations

        return report

    async def run_full_benchmark_suite(
        self, establish_baselines: bool = False
    ) -> Dict[str, Any]:
        """Run the complete benchmark suite"""
        logger.info("Starting comprehensive benchmark suite")

        # Define benchmark configurations
        benchmarks = [
            (self.run_conversion_benchmark, "Conversion Performance"),
            (self.run_cache_performance_benchmark, "Cache Performance"),
            (self.run_batch_processing_benchmark, "Batch Processing"),
            (self.run_database_benchmark, "Database Performance"),
            (self.run_mixed_workload_benchmark, "Mixed Workload"),
            (self.run_stress_test, "Stress Test"),
        ]

        results = {}

        for benchmark_func, description in benchmarks:
            try:
                logger.info(f"Running {description}")
                result = await benchmark_func()
                results[result.configuration.name] = result

                if establish_baselines:
                    self.establish_baseline(result.configuration.name, result)

                # Brief pause between benchmarks
                await asyncio.sleep(2)

            except Exception as e:
                logger.error(f"Benchmark {description} failed: {e}")
                results[description] = {"error": str(e)}

        # Generate comprehensive report
        report = self.generate_benchmark_report()

        logger.info("Benchmark suite completed")
        return {"results": results, "report": report, "timestamp": datetime.now()}


# Global benchmark suite instance
benchmark_suite = BenchmarkSuite()
