"""
Comprehensive tests for Benchmark Suite
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

from src.services.benchmark_suite import (
    BenchmarkConfiguration,
    BenchmarkMetric,
    BenchmarkResult,
    LoadGenerator,
    BenchmarkSuite,
    benchmark_suite,
)


class TestBenchmarkConfiguration:
    """Test BenchmarkConfiguration dataclass"""

    def test_benchmark_configuration_creation(self):
        """Test creating a BenchmarkConfiguration"""
        config = BenchmarkConfiguration(
            name="test_benchmark",
            description="Test benchmark configuration",
            warmup_iterations=5,
            measurement_iterations=50,
            concurrent_users=3,
            ramp_up_time=2.0,
            duration=30.0,
            think_time=0.2,
            timeout=15.0,
            enable_monitoring=True,
            collect_detailed_metrics=False,
        )

        assert config.name == "test_benchmark"
        assert config.description == "Test benchmark configuration"
        assert config.warmup_iterations == 5
        assert config.measurement_iterations == 50
        assert config.concurrent_users == 3
        assert config.ramp_up_time == 2.0
        assert config.duration == 30.0
        assert config.think_time == 0.2
        assert config.timeout == 15.0
        assert config.enable_monitoring is True
        assert config.collect_detailed_metrics is False

    def test_benchmark_configuration_defaults(self):
        """Test BenchmarkConfiguration with default values"""
        config = BenchmarkConfiguration(name="test", description="Test configuration")

        assert config.warmup_iterations == 10
        assert config.measurement_iterations == 100
        assert config.concurrent_users == 1
        assert config.ramp_up_time == 5.0
        assert config.duration == 60.0
        assert config.think_time == 0.1
        assert config.timeout == 30.0
        assert config.enable_monitoring is True
        assert config.collect_detailed_metrics is True


class TestBenchmarkMetric:
    """Test BenchmarkMetric dataclass"""

    def test_benchmark_metric_creation(self):
        """Test creating a BenchmarkMetric"""
        start_time = datetime.now()
        end_time = start_time + timedelta(milliseconds=150)

        metric = BenchmarkMetric(
            iteration=5,
            start_time=start_time,
            end_time=end_time,
            duration_ms=150.0,
            success=True,
            error_message=None,
            cpu_before=45.2,
            cpu_after=48.1,
            memory_before=512.0,
            memory_after=520.0,
            metadata={"worker_id": 1},
        )

        assert metric.iteration == 5
        assert metric.start_time == start_time
        assert metric.end_time == end_time
        assert metric.duration_ms == 150.0
        assert metric.success is True
        assert metric.error_message is None
        assert metric.cpu_before == 45.2
        assert metric.cpu_after == 48.1
        assert metric.memory_before == 512.0
        assert metric.memory_after == 520.0
        assert metric.metadata == {"worker_id": 1}

    def test_benchmark_metric_failure(self):
        """Test creating a BenchmarkMetric for failed operation"""
        start_time = datetime.now()
        end_time = start_time + timedelta(milliseconds=50)

        metric = BenchmarkMetric(
            iteration=3,
            start_time=start_time,
            end_time=end_time,
            duration_ms=50.0,
            success=False,
            error_message="Operation timeout",
        )

        assert metric.success is False
        assert metric.error_message == "Operation timeout"
        assert metric.duration_ms == 50.0


class TestLoadGenerator:
    """Test LoadGenerator class"""

    @pytest.fixture
    def load_generator(self):
        """Create a LoadGenerator instance for testing"""
        return LoadGenerator()

    @pytest.mark.asyncio
    async def test_single_operation_execution(self, load_generator):
        """Test executing a single operation"""
        call_count = 0

        async def test_operation(iteration: int, worker_id: int):
            nonlocal call_count
            call_count += 1
            await asyncio.sleep(0.01)  # Simulate some work
            return iteration * worker_id

        config = BenchmarkConfiguration(
            name="test", description="Test configuration", timeout=5.0
        )

        metric = await load_generator._execute_operation(test_operation, 1, 0, config)

        assert metric.iteration == 1
        assert metric.success is True
        assert metric.duration_ms > 0
        assert metric.metadata["worker_id"] == 0
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_operation_execution_timeout(self, load_generator):
        """Test operation execution with timeout"""

        async def slow_operation(iteration: int, worker_id: int):
            await asyncio.sleep(10)  # Sleep longer than timeout
            return "should not reach here"

        config = BenchmarkConfiguration(
            name="test",
            description="Test configuration",
            timeout=0.1,  # Very short timeout
        )

        metric = await load_generator._execute_operation(slow_operation, 1, 0, config)

        assert metric.success is False
        assert "timed out" in metric.error_message.lower()
        assert metric.duration_ms > 100  # Should be around the timeout duration

    @pytest.mark.asyncio
    async def test_operation_execution_exception(self, load_generator):
        """Test operation execution with exception"""

        async def failing_operation(iteration: int, worker_id: int):
            raise ValueError("Test error")

        config = BenchmarkConfiguration(
            name="test", description="Test configuration", timeout=5.0
        )

        metric = await load_generator._execute_operation(
            failing_operation, 1, 0, config
        )

        assert metric.success is False
        assert "Test error" in metric.error_message

    @pytest.mark.asyncio
    async def test_constant_load_generation(self, load_generator):
        """Test constant load generation"""
        operation_count = 0

        async def test_operation(iteration: int, worker_id: int):
            nonlocal operation_count
            operation_count += 1
            await asyncio.sleep(0.001)  # Very fast operation
            return iteration

        config = BenchmarkConfiguration(
            name="test",
            description="Test configuration",
            concurrent_users=3,
            duration=0.1,  # Very short duration for testing
            ramp_up_time=0.01,
            think_time=0.0,
        )

        metrics = await load_generator.generate_constant_load(test_operation, config)

        assert len(metrics) > 0
        assert all(m.success for m in metrics)  # All should succeed
        assert len(set(m.metadata["worker_id"] for m in metrics)) <= 3  # Max 3 workers

    @pytest.mark.asyncio
    async def test_spike_load_generation(self, load_generator):
        """Test spike load generation"""
        operation_count = 0

        async def test_operation(iteration: int, worker_id: int):
            nonlocal operation_count
            operation_count += 1
            await asyncio.sleep(0.001)
            return iteration

        config = BenchmarkConfiguration(
            name="test",
            description="Test configuration",
            concurrent_users=2,
            duration=0.05,  # Very short for testing
            ramp_up_time=0.01,
        )

        metrics = await load_generator.generate_spike_load(
            test_operation, config, spike_factor=2.0, spike_duration=0.05
        )

        assert len(metrics) > 0
        # Should have metrics from both normal and spike phases
        assert all(m.success for m in metrics)


class TestBenchmarkSuite:
    """Test BenchmarkSuite class"""

    @pytest.fixture
    def benchmark_suite_instance(self):
        """Create a BenchmarkSuite instance for testing"""
        return BenchmarkSuite()

    @pytest.mark.asyncio
    async def test_run_single_threaded_benchmark(self, benchmark_suite_instance):
        """Test running a single-threaded benchmark"""
        call_count = 0

        async def test_operation(iteration: int, worker_id: int):
            nonlocal call_count
            call_count += 1
            await asyncio.sleep(0.01)
            return iteration * 2

        config = BenchmarkConfiguration(
            name="test_benchmark",
            description="Test benchmark",
            measurement_iterations=5,
            think_time=0.0,
        )

        metrics = await benchmark_suite_instance._run_single_threaded(
            test_operation, config
        )

        assert len(metrics) == 5
        assert call_count == 5
        assert all(m.success for m in metrics)
        assert all(m.iteration < 5 for m in metrics)

    def test_collect_system_metrics(self, benchmark_suite_instance):
        """Test system metrics collection"""
        with patch("src.services.benchmark_suite.psutil") as mock_psutil:
            mock_psutil.cpu_percent.return_value = 45.5
            mock_psutil.virtual_memory.return_value = Mock(
                percent=60.2, used=1073741824
            )
            mock_psutil.disk_usage.return_value = Mock(percent=75.0)
            mock_psutil.pids.return_value = [1, 2, 3, 4, 5]

            metrics = benchmark_suite_instance._collect_system_metrics()

            assert metrics["cpu_percent"] == 45.5
            assert metrics["memory_percent"] == 60.2
            assert metrics["memory_mb"] == 1024.0  # 1GB in MB
            assert metrics["disk_usage"] == 75.0
            assert metrics["process_count"] == 5
            assert "timestamp" in metrics

    @pytest.mark.asyncio
    async def test_run_single_benchmark_success(self, benchmark_suite_instance):
        """Test successful benchmark execution"""

        async def test_operation(iteration: int, worker_id: int):
            await asyncio.sleep(0.01)
            return iteration

        config = BenchmarkConfiguration(
            name="success_test",
            description="Test successful benchmark",
            measurement_iterations=3,
            think_time=0.0,
        )

        result = await benchmark_suite_instance._run_single_benchmark(
            test_operation, config
        )

        assert isinstance(result, BenchmarkResult)
        assert result.configuration == config
        assert result.success_rate == 1.0  # All should succeed
        assert result.error_rate == 0.0
        assert result.throughput > 0
        assert result.avg_response_time > 0
        assert len(result.metrics) == 3

    @pytest.mark.asyncio
    async def test_run_single_benchmark_failures(self, benchmark_suite_instance):
        """Test benchmark execution with some failures"""

        async def failing_operation(iteration: int, worker_id: int):
            if iteration % 2 == 0:
                raise ValueError("Simulated failure")
            await asyncio.sleep(0.01)
            return iteration

        config = BenchmarkConfiguration(
            name="failure_test",
            description="Test benchmark with failures",
            measurement_iterations=4,
            think_time=0.0,
        )

        result = await benchmark_suite_instance._run_single_benchmark(
            failing_operation, config
        )

        assert result.success_rate == 0.5  # Half should succeed
        assert result.error_rate == 0.5
        assert result.throughput > 0
        assert len(result.metrics) == 4

    def test_establish_baseline(self, benchmark_suite_instance):
        """Test establishing a baseline"""
        # Create a mock result
        config = BenchmarkConfiguration(name="test", description="Test")
        metrics = [
            BenchmarkMetric(
                iteration=1,
                start_time=datetime.now(),
                end_time=datetime.now(),
                duration_ms=100.0,
                success=True,
            )
        ]
        result = BenchmarkResult(
            configuration=config,
            metrics=metrics,
            start_time=datetime.now(),
            end_time=datetime.now(),
            total_duration=1.0,
            success_rate=1.0,
            avg_response_time=100.0,
            p50_response_time=100.0,
            p95_response_time=100.0,
            p99_response_time=100.0,
            min_response_time=100.0,
            max_response_time=100.0,
            throughput=10.0,
            error_rate=0.0,
            cpu_usage_avg=50.0,
            memory_usage_avg=512.0,
        )

        benchmark_suite_instance.establish_baseline("test", result)

        assert "test" in benchmark_suite_instance.baseline_results
        assert benchmark_suite_instance.baseline_results["test"] == result

    def test_compare_with_baseline(self, benchmark_suite_instance):
        """Test comparing with baseline"""
        # Create baseline result
        baseline_config = BenchmarkConfiguration(name="test", description="Test")
        baseline_metrics = [
            BenchmarkMetric(
                iteration=1,
                start_time=datetime.now(),
                end_time=datetime.now(),
                duration_ms=200.0,
                success=True,
            )
        ]
        baseline_result = BenchmarkResult(
            configuration=baseline_config,
            metrics=baseline_metrics,
            start_time=datetime.now(),
            end_time=datetime.now(),
            total_duration=1.0,
            success_rate=1.0,
            avg_response_time=200.0,
            p50_response_time=200.0,
            p95_response_time=200.0,
            p99_response_time=200.0,
            min_response_time=200.0,
            max_response_time=200.0,
            throughput=5.0,
            error_rate=0.0,
            cpu_usage_avg=50.0,
            memory_usage_avg=512.0,
        )

        # Establish baseline
        benchmark_suite_instance.establish_baseline("test", baseline_result)

        # Create current result (better performance)
        current_config = BenchmarkConfiguration(name="test", description="Test")
        current_metrics = [
            BenchmarkMetric(
                iteration=1,
                start_time=datetime.now(),
                end_time=datetime.now(),
                duration_ms=100.0,  # Faster than baseline
                success=True,
            )
        ]
        current_result = BenchmarkResult(
            configuration=current_config,
            metrics=current_metrics,
            start_time=datetime.now(),
            end_time=datetime.now(),
            total_duration=1.0,
            success_rate=1.0,
            avg_response_time=100.0,  # 50% improvement
            p50_response_time=100.0,
            p95_response_time=100.0,
            p99_response_time=100.0,
            min_response_time=100.0,
            max_response_time=100.0,
            throughput=10.0,  # 100% improvement
            error_rate=0.0,
            cpu_usage_avg=45.0,
            memory_usage_avg=500.0,
        )

        comparison = benchmark_suite_instance.compare_with_baseline(current_result)

        assert comparison["benchmark_name"] == "test"
        assert comparison["response_time_improvement_percent"] == 50.0
        assert comparison["throughput_improvement_percent"] == 100.0
        assert comparison["is_improvement"] is True

    def test_compare_with_no_baseline(self, benchmark_suite_instance):
        """Test comparing when no baseline exists"""
        config = BenchmarkConfiguration(name="nonexistent", description="Test")
        metrics = [
            BenchmarkMetric(
                iteration=1,
                start_time=datetime.now(),
                end_time=datetime.now(),
                duration_ms=100.0,
                success=True,
            )
        ]
        result = BenchmarkResult(
            configuration=config,
            metrics=metrics,
            start_time=datetime.now(),
            end_time=datetime.now(),
            total_duration=1.0,
            success_rate=1.0,
            avg_response_time=100.0,
            p50_response_time=100.0,
            p95_response_time=100.0,
            p99_response_time=100.0,
            min_response_time=100.0,
            max_response_time=100.0,
            throughput=10.0,
            error_rate=0.0,
            cpu_usage_avg=50.0,
            memory_usage_avg=512.0,
        )

        comparison = benchmark_suite_instance.compare_with_baseline(result)

        assert comparison["status"] == "no_baseline"
        assert "no baseline" in comparison["message"]

    def test_generate_benchmark_report(self, benchmark_suite_instance):
        """Test generating comprehensive benchmark report"""
        # Add some test results
        config1 = BenchmarkConfiguration(name="test1", description="Test 1")
        config2 = BenchmarkConfiguration(name="test2", description="Test 2")

        metrics = [
            BenchmarkMetric(
                iteration=1,
                start_time=datetime.now(),
                end_time=datetime.now(),
                duration_ms=100.0,
                success=True,
            )
        ]

        # Create successful result
        success_result = BenchmarkResult(
            configuration=config1,
            metrics=metrics,
            start_time=datetime.now(),
            end_time=datetime.now(),
            total_duration=1.0,
            success_rate=1.0,
            avg_response_time=100.0,
            p50_response_time=100.0,
            p95_response_time=100.0,
            p99_response_time=100.0,
            min_response_time=100.0,
            max_response_time=100.0,
            throughput=10.0,
            error_rate=0.0,
            cpu_usage_avg=50.0,
            memory_usage_avg=512.0,
        )

        # Create problematic result
        problematic_result = BenchmarkResult(
            configuration=config2,
            metrics=metrics,
            start_time=datetime.now(),
            end_time=datetime.now(),
            total_duration=1.0,
            success_rate=0.85,  # Low success rate
            avg_response_time=1500.0,  # High response time
            p50_response_time=1500.0,
            p95_response_time=1500.0,
            p99_response_time=1500.0,
            min_response_time=1500.0,
            max_response_time=1500.0,
            throughput=5.0,
            error_rate=0.15,  # High error rate
            cpu_usage_avg=50.0,
            memory_usage_avg=512.0,
        )

        benchmark_suite_instance.benchmark_results = [
            success_result,
            problematic_result,
        ]

        report = benchmark_suite_instance.generate_benchmark_report()

        assert "generated_at" in report
        assert report["summary"]["total_benchmarks"] == 2
        assert report["summary"]["successful_benchmarks"] == 1
        assert len(report["benchmarks"]) == 2
        assert (
            len(report["recommendations"]) >= 2
        )  # Should have recommendations for problematic result

        # Check recommendations
        recommendations = report["recommendations"]
        reliability_recs = [r for r in recommendations if r["type"] == "reliability"]
        performance_recs = [r for r in recommendations if r["type"] == "performance"]
        stability_recs = [r for r in recommendations if r["type"] == "stability"]

        assert len(reliability_recs) > 0  # Low success rate
        assert len(performance_recs) > 0  # High response time
        assert len(stability_recs) > 0  # High error rate

    @pytest.mark.asyncio
    async def test_run_conversion_benchmark(self, benchmark_suite_instance):
        """Test running conversion benchmark"""
        result = await benchmark_suite_instance.run_conversion_benchmark()

        assert isinstance(result, BenchmarkResult)
        assert result.configuration.name == "conversion_performance"
        assert result.success_rate > 0
        assert result.throughput > 0
        assert len(benchmark_suite_instance.benchmark_results) == 1

    @pytest.mark.asyncio
    async def test_run_cache_performance_benchmark(self, benchmark_suite_instance):
        """Test running cache performance benchmark"""
        result = await benchmark_suite_instance.run_cache_performance_benchmark()

        assert isinstance(result, BenchmarkResult)
        assert result.configuration.name == "cache_performance"
        assert result.success_rate > 0
        assert result.throughput > 0

    @pytest.mark.asyncio
    async def test_run_batch_processing_benchmark(self, benchmark_suite_instance):
        """Test running batch processing benchmark"""
        result = await benchmark_suite_instance.run_batch_processing_benchmark()

        assert isinstance(result, BenchmarkResult)
        assert result.configuration.name == "batch_processing_performance"
        assert result.success_rate > 0

    @pytest.mark.asyncio
    async def test_run_database_benchmark(self, benchmark_suite_instance):
        """Test running database benchmark"""
        result = await benchmark_suite_instance.run_database_benchmark()

        assert isinstance(result, BenchmarkResult)
        assert result.configuration.name == "database_performance"
        assert result.success_rate > 0

    @pytest.mark.asyncio
    async def test_run_mixed_workload_benchmark(self, benchmark_suite_instance):
        """Test running mixed workload benchmark"""
        result = await benchmark_suite_instance.run_mixed_workload_benchmark()

        assert isinstance(result, BenchmarkResult)
        assert result.configuration.name == "mixed_workload_performance"
        assert result.success_rate > 0

    @pytest.mark.asyncio
    async def test_run_stress_test(self, benchmark_suite_instance):
        """Test running stress test"""
        # Use a minimal configuration for testing
        config = BenchmarkConfiguration(
            name="stress_test",
            description="High-load stress test",
            concurrent_users=2,  # Reduced for testing
            measurement_iterations=5,  # Reduced for testing
            duration=1.0,  # Very short for testing
            ramp_up_time=0.1,
        )

        result = await benchmark_suite_instance.run_stress_test(config)

        assert isinstance(result, BenchmarkResult)
        assert result.success_rate >= 0  # Can be less than 1 under stress
        assert len(result.metrics) > 0

    @pytest.mark.asyncio
    async def test_run_full_benchmark_suite(self, benchmark_suite_instance):
        """Test running the complete benchmark suite"""
        # This is a longer test, so use minimal configurations
        with (
            patch.object(
                benchmark_suite_instance, "run_conversion_benchmark"
            ) as mock_conversion,
            patch.object(
                benchmark_suite_instance, "run_cache_performance_benchmark"
            ) as mock_cache,
            patch.object(
                benchmark_suite_instance, "run_batch_processing_benchmark"
            ) as mock_batch,
            patch.object(benchmark_suite_instance, "run_database_benchmark") as mock_db,
            patch.object(
                benchmark_suite_instance, "run_mixed_workload_benchmark"
            ) as mock_mixed,
            patch.object(benchmark_suite_instance, "run_stress_test") as mock_stress,
        ):
            # Mock all benchmark functions to return quickly
            for mock_func in [
                mock_conversion,
                mock_cache,
                mock_batch,
                mock_db,
                mock_mixed,
                mock_stress,
            ]:
                mock_result = Mock()
                mock_result.configuration.name = "mock_benchmark"
                mock_result.end_time = datetime.now()
                mock_func.return_value = mock_result

            results = await benchmark_suite_instance.run_full_benchmark_suite()

            assert "results" in results
            assert "report" in results
            assert "timestamp" in results

            # Verify all benchmarks were called
            mock_conversion.assert_called_once()
            mock_cache.assert_called_once()
            mock_batch.assert_called_once()
            mock_db.assert_called_once()
            mock_mixed.assert_called_once()
            mock_stress.assert_called_once()


class TestGlobalBenchmarkSuite:
    """Test global benchmark_suite instance"""

    def test_global_benchmark_suite_exists(self):
        """Test that global benchmark_suite instance exists"""
        assert benchmark_suite is not None
        assert isinstance(benchmark_suite, BenchmarkSuite)


@pytest.mark.integration
class TestBenchmarkSuiteIntegration:
    """Integration tests for benchmark suite"""

    @pytest.mark.asyncio
    async def test_end_to_end_benchmark_workflow(self):
        """Test complete benchmark workflow"""
        # Create a temporary benchmark suite
        suite = BenchmarkSuite()

        # Run a simple benchmark
        config = BenchmarkConfiguration(
            name="integration_test",
            description="Integration test benchmark",
            measurement_iterations=3,
            think_time=0.0,
        )

        async def test_operation(iteration: int, worker_id: int):
            await asyncio.sleep(0.01)
            return iteration * 2

        result = await suite._run_single_benchmark(test_operation, config)

        # Establish baseline
        suite.establish_baseline("integration_test", result)

        # Run another benchmark (simulated improvement)
        improved_config = BenchmarkConfiguration(
            name="integration_test",
            description="Integration test benchmark",
            measurement_iterations=3,
            think_time=0.0,
        )

        async def improved_operation(iteration: int, worker_id: int):
            await asyncio.sleep(0.005)  # Faster than before
            return iteration * 2

        improved_result = await suite._run_single_benchmark(
            improved_operation, improved_config
        )

        # Compare with baseline
        comparison = suite.compare_with_baseline(improved_result)

        # Generate report
        report = suite.generate_benchmark_report()

        # Verify workflow completed successfully
        assert result.success_rate == 1.0
        assert improved_result.success_rate == 1.0
        assert comparison["status"] == "compared"
        assert (
            comparison["response_time_improvement_percent"] > 0
        )  # Should show improvement
        assert report["summary"]["total_benchmarks"] == 2
        assert len(report["benchmarks"]) == 2
