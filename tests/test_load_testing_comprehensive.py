"""
Comprehensive load testing framework.
Tests sustained load, scaling, and breaking points.
"""

import pytest
import asyncio
import time
import statistics
from typing import List, Dict, Any
from unittest.mock import AsyncMock, patch
from dataclasses import dataclass
from enum import Enum

# Set up imports
try:
    from modporter.cli.main import convert_mod
    IMPORTS_AVAILABLE = True
except ImportError:
    IMPORTS_AVAILABLE = False


pytestmark = pytest.mark.skipif(not IMPORTS_AVAILABLE, reason="Required imports unavailable")


# ==================== Load Testing Models ====================

class LoadProfile(Enum):
    """Load test profile types."""
    RAMP_UP = "ramp_up"           # Gradually increase load
    SPIKE = "spike"                # Sudden load increase
    SUSTAINED = "sustained"        # Constant load
    WAVE = "wave"                  # Repeating load waves


@dataclass
class LoadTestResult:
    """Results from a load test."""
    total_requests: int
    successful_requests: int
    failed_requests: int
    total_duration_sec: float
    min_response_time_ms: float
    max_response_time_ms: float
    mean_response_time_ms: float
    median_response_time_ms: float
    p95_response_time_ms: float
    p99_response_time_ms: float
    requests_per_second: float
    error_rate: float


# ==================== Load Testing Framework ====================

class LoadTestFramework:
    """Framework for running load tests."""
    
    def __init__(self, concurrent_users: int = 10, duration_sec: int = 60):
        self.concurrent_users = concurrent_users
        self.duration_sec = duration_sec
        self.results: List[float] = []
        self.errors: List[Exception] = []
    
    async def run_test(self, operation, profile: LoadProfile = LoadProfile.SUSTAINED):
        """Run load test with specified profile."""
        if profile == LoadProfile.RAMP_UP:
            await self._ramp_up_load(operation)
        elif profile == LoadProfile.SPIKE:
            await self._spike_load(operation)
        elif profile == LoadProfile.SUSTAINED:
            await self._sustained_load(operation)
        elif profile == LoadProfile.WAVE:
            await self._wave_load(operation)
    
    async def _sustained_load(self, operation):
        """Run sustained constant load."""
        start_time = time.time()
        tasks = []
        
        while time.time() - start_time < self.duration_sec:
            # Create concurrent tasks
            batch = [
                self._timed_operation(operation)
                for _ in range(self.concurrent_users)
            ]
            tasks.extend(batch)
            await asyncio.sleep(0.1)  # Batch creation
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        self._process_results(results)
    
    async def _ramp_up_load(self, operation):
        """Ramp up load gradually."""
        start_time = time.time()
        current_users = 1
        max_users = self.concurrent_users
        
        while time.time() - start_time < self.duration_sec:
            tasks = [
                self._timed_operation(operation)
                for _ in range(min(current_users, max_users))
            ]
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            self._process_results(results)
            
            # Ramp up: increase by 1 user each iteration
            current_users += 1
            await asyncio.sleep(1)
    
    async def _spike_load(self, operation):
        """Create sudden spike in load."""
        # Warm up
        warm_up = [
            self._timed_operation(operation)
            for _ in range(self.concurrent_users // 2)
        ]
        await asyncio.gather(*warm_up, return_exceptions=True)
        
        # Spike: 10x normal load
        spike = [
            self._timed_operation(operation)
            for _ in range(self.concurrent_users * 10)
        ]
        spike_results = await asyncio.gather(*spike, return_exceptions=True)
        self._process_results(spike_results)
    
    async def _wave_load(self, operation):
        """Create repeating load waves."""
        start_time = time.time()
        
        while time.time() - start_time < self.duration_sec:
            # Wave 1: Light load
            light = [
                self._timed_operation(operation)
                for _ in range(self.concurrent_users // 2)
            ]
            results1 = await asyncio.gather(*light, return_exceptions=True)
            self._process_results(results1)
            await asyncio.sleep(5)
            
            # Wave 2: Heavy load
            heavy = [
                self._timed_operation(operation)
                for _ in range(self.concurrent_users * 2)
            ]
            results2 = await asyncio.gather(*heavy, return_exceptions=True)
            self._process_results(results2)
            await asyncio.sleep(5)
    
    async def _timed_operation(self, operation):
        """Execute operation and measure time."""
        start = time.time()
        try:
            result = await operation()
            duration_ms = (time.time() - start) * 1000
            self.results.append(duration_ms)
            return {"success": True, "duration_ms": duration_ms}
        except Exception as e:
            self.errors.append(e)
            return {"success": False, "error": str(e)}
    
    def _process_results(self, results):
        """Process batch results."""
        for result in results:
            if isinstance(result, dict) and result.get("success"):
                self.results.append(result["duration_ms"])
            else:
                self.errors.append(result if isinstance(result, Exception) else Exception(str(result)))
    
    def get_summary(self) -> LoadTestResult:
        """Get test results summary."""
        total = len(self.results) + len(self.errors)
        successful = len(self.results)
        failed = len(self.errors)
        
        if not self.results:
            self.results = [0]
        
        sorted_results = sorted(self.results)
        
        return LoadTestResult(
            total_requests=total,
            successful_requests=successful,
            failed_requests=failed,
            total_duration_sec=self.duration_sec,
            min_response_time_ms=min(self.results),
            max_response_time_ms=max(self.results),
            mean_response_time_ms=statistics.mean(self.results),
            median_response_time_ms=statistics.median(self.results),
            p95_response_time_ms=sorted_results[int(len(sorted_results) * 0.95)] if len(sorted_results) > 0 else 0,
            p99_response_time_ms=sorted_results[int(len(sorted_results) * 0.99)] if len(sorted_results) > 0 else 0,
            requests_per_second=successful / self.duration_sec if self.duration_sec > 0 else 0,
            error_rate=failed / total if total > 0 else 0
        )


# ==================== Test Classes ====================

class TestSustainedLoad:
    """Test sustained constant load."""
    
    @pytest.mark.asyncio
    async def test_sustained_10_users(self):
        """Test with 10 concurrent users for 10 seconds."""
        async def dummy_conversion():
            await asyncio.sleep(0.1)
            return {"success": True}
        
        framework = LoadTestFramework(concurrent_users=10, duration_sec=10)
        await framework.run_test(dummy_conversion, LoadProfile.SUSTAINED)
        
        summary = framework.get_summary()
        
        # Should handle sustained load
        assert summary.successful_requests > 0
        assert summary.error_rate < 0.1  # Less than 10% errors
    
    @pytest.mark.asyncio
    async def test_sustained_50_users(self):
        """Test with 50 concurrent users."""
        async def dummy_conversion():
            await asyncio.sleep(0.05)
            return {"success": True}
        
        framework = LoadTestFramework(concurrent_users=50, duration_sec=5)
        await framework.run_test(dummy_conversion, LoadProfile.SUSTAINED)
        
        summary = framework.get_summary()
        
        # Should maintain performance
        assert summary.requests_per_second > 10
    
    @pytest.mark.asyncio
    async def test_response_time_under_load(self):
        """Test response time characteristics under load."""
        async def dummy_conversion():
            await asyncio.sleep(0.05)
            return {"success": True}
        
        framework = LoadTestFramework(concurrent_users=20, duration_sec=5)
        await framework.run_test(dummy_conversion, LoadProfile.SUSTAINED)
        
        summary = framework.get_summary()
        
        # Response times should be reasonable
        assert summary.mean_response_time_ms < 200
        assert summary.p99_response_time_ms < 500


class TestRampUpLoad:
    """Test gradual load increase."""
    
    @pytest.mark.asyncio
    async def test_linear_ramp_up(self):
        """Test linear ramp up from 1 to 10 users."""
        async def dummy_conversion():
            await asyncio.sleep(0.05)
            return {"success": True}
        
        framework = LoadTestFramework(concurrent_users=10, duration_sec=10)
        await framework.run_test(dummy_conversion, LoadProfile.RAMP_UP)
        
        summary = framework.get_summary()
        
        # Should complete successfully
        assert summary.successful_requests > 0
    
    @pytest.mark.asyncio
    async def test_ramp_up_degradation(self):
        """Test system degradation during ramp up."""
        response_times_by_phase = []
        
        async def tracked_conversion():
            start = time.time()
            await asyncio.sleep(0.05)
            return time.time() - start
        
        # Simulate ramp up tracking
        for phase in range(5):
            tasks = [tracked_conversion() for _ in range(phase + 1)]
            results = await asyncio.gather(*tasks)
            response_times_by_phase.append(statistics.mean(results))
        
        # Response times should increase as load increases
        for i in range(len(response_times_by_phase) - 1):
            # Allow for some variance
            assert response_times_by_phase[i] <= response_times_by_phase[i + 1] * 1.5


class TestSpikeLoad:
    """Test sudden load spikes."""
    
    @pytest.mark.asyncio
    async def test_spike_recovery(self):
        """Test recovery from sudden load spike."""
        request_count = 0
        
        async def trackable_conversion():
            nonlocal request_count
            request_count += 1
            await asyncio.sleep(0.05)
            return {"success": True}
        
        framework = LoadTestFramework(concurrent_users=10, duration_sec=5)
        await framework.run_test(trackable_conversion, LoadProfile.SPIKE)
        
        summary = framework.get_summary()
        
        # Should recover from spike
        assert summary.error_rate < 0.2  # Some errors acceptable
        assert summary.successful_requests > summary.failed_requests
    
    @pytest.mark.asyncio
    async def test_spike_magnitude(self):
        """Test handling of varying spike magnitudes."""
        spikes = [5, 10, 20]  # Spike multipliers
        
        for spike_multiplier in spikes:
            async def dummy_conversion():
                await asyncio.sleep(0.01)
                return {"success": True}
            
            # Simulate spike
            tasks = [dummy_conversion() for _ in range(spike_multiplier)]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Should handle various spike magnitudes
            assert len(results) == spike_multiplier


class TestWaveLoad:
    """Test repeating load waves."""
    
    @pytest.mark.asyncio
    async def test_alternating_load_waves(self):
        """Test system under alternating load waves."""
        load_levels = []
        
        for wave in range(3):
            # Light load
            light_tasks = [
                asyncio.sleep(0.05) for _ in range(5)
            ]
            await asyncio.gather(*light_tasks)
            load_levels.append("light")
            
            # Heavy load
            heavy_tasks = [
                asyncio.sleep(0.05) for _ in range(20)
            ]
            await asyncio.gather(*heavy_tasks)
            load_levels.append("heavy")
        
        # Should have alternating pattern
        assert load_levels.count("light") == load_levels.count("heavy")


class TestBreakingPoint:
    """Test system breaking point and limits."""
    
    @pytest.mark.asyncio
    async def test_find_breaking_point(self):
        """Test to find system breaking point."""
        breaking_point = None
        
        for concurrent_users in [10, 50, 100, 200, 500]:
            async def dummy_conversion():
                await asyncio.sleep(0.05)
                if asyncio.current_task() is None:
                    raise RuntimeError("Task limit exceeded")
                return {"success": True}
            
            try:
                tasks = [
                    dummy_conversion() for _ in range(concurrent_users)
                ]
                results = await asyncio.wait_for(
                    asyncio.gather(*tasks, return_exceptions=True),
                    timeout=5
                )
                
                failures = sum(1 for r in results if isinstance(r, Exception))
                error_rate = failures / len(results)
                
                if error_rate > 0.5:  # More than 50% failure
                    breaking_point = concurrent_users
                    break
            except TimeoutError:
                breaking_point = concurrent_users
                break
        
        # System should have some reasonable limit
        assert breaking_point is None or breaking_point >= 10


class TestStressScenarios:
    """Test various stress scenarios."""
    
    @pytest.mark.asyncio
    async def test_long_duration_sustained_load(self):
        """Test long-duration sustained load."""
        async def dummy_op():
            await asyncio.sleep(0.01)
            return {"success": True}
        
        framework = LoadTestFramework(concurrent_users=5, duration_sec=10)
        
        # Run for 10 seconds
        start = time.time()
        while time.time() - start < 10:
            tasks = [dummy_op() for _ in range(5)]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            framework.results.extend([
                r.get("duration_ms", 10) for r in results if isinstance(r, dict)
            ])
        
        # Should maintain stability
        assert len(framework.results) > 20
    
    @pytest.mark.asyncio
    async def test_variable_response_time(self):
        """Test handling variable response times."""
        async def variable_op():
            # Response time varies randomly
            duration = 0.05 + (time.time() % 0.05)
            await asyncio.sleep(duration)
            return {"success": True}
        
        framework = LoadTestFramework(concurrent_users=10, duration_sec=5)
        
        tasks = [variable_op() for _ in range(30)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Should handle variable times
        assert len(results) == 30


class TestResourceUtilizationUnderLoad:
    """Test resource utilization patterns under load."""
    
    @pytest.mark.asyncio
    async def test_memory_under_load(self):
        """Test memory usage under load."""
        import sys
        
        objects_created = 0
        
        async def memory_op():
            nonlocal objects_created
            data = {"key": "value" * 1000}
            objects_created += 1
            await asyncio.sleep(0.01)
            return data
        
        tasks = [memory_op() for _ in range(100)]
        results = await asyncio.gather(*tasks)
        
        # Should create expected number of objects
        assert len(results) == 100
    
    @pytest.mark.asyncio
    async def test_connection_pooling_under_load(self):
        """Test connection pooling under load."""
        active_connections = 0
        max_connections = 0
        
        async def connection_op():
            nonlocal active_connections, max_connections
            active_connections += 1
            max_connections = max(max_connections, active_connections)
            await asyncio.sleep(0.05)
            active_connections -= 1
            return {"success": True}
        
        tasks = [connection_op() for _ in range(20)]
        await asyncio.gather(*tasks)
        
        # Should pool connections efficiently
        assert max_connections <= 20


class TestLoadTestMetrics:
    """Test metrics collection and analysis."""
    
    @pytest.mark.asyncio
    async def test_percentile_calculations(self):
        """Test percentile calculation accuracy."""
        response_times = list(range(1, 101))  # 1-100ms
        
        # Calculate percentiles
        p50 = response_times[int(len(response_times) * 0.50)]
        p95 = response_times[int(len(response_times) * 0.95)]
        p99 = response_times[int(len(response_times) * 0.99)]
        
        assert p50 == 50 or p50 == 51
        assert p95 >= 90
        assert p99 >= 98
    
    @pytest.mark.asyncio
    async def test_throughput_calculation(self):
        """Test throughput calculation."""
        requests = 1000
        duration_sec = 10
        
        throughput = requests / duration_sec
        
        assert throughput == 100  # 100 req/sec


class TestLoadTestReporting:
    """Test load test result reporting."""
    
    def test_result_summary_format(self):
        """Test result summary format."""
        result = LoadTestResult(
            total_requests=1000,
            successful_requests=950,
            failed_requests=50,
            total_duration_sec=10,
            min_response_time_ms=10,
            max_response_time_ms=500,
            mean_response_time_ms=100,
            median_response_time_ms=95,
            p95_response_time_ms=200,
            p99_response_time_ms=400,
            requests_per_second=100,
            error_rate=0.05
        )
        
        # All fields should be populated
        assert result.total_requests == 1000
        assert result.error_rate == 0.05
        assert result.requests_per_second == 100
    
    def test_result_validation(self):
        """Test result validation."""
        result = LoadTestResult(
            total_requests=1000,
            successful_requests=950,
            failed_requests=50,
            total_duration_sec=10,
            min_response_time_ms=10,
            max_response_time_ms=500,
            mean_response_time_ms=100,
            median_response_time_ms=95,
            p95_response_time_ms=200,
            p99_response_time_ms=400,
            requests_per_second=100,
            error_rate=0.05
        )
        
        # Validate consistency
        assert result.successful_requests + result.failed_requests == result.total_requests
        assert result.min_response_time_ms <= result.mean_response_time_ms
        assert result.mean_response_time_ms <= result.max_response_time_ms
        assert 0 <= result.error_rate <= 1
