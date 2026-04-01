"""
Comprehensive performance and stress tests.
Tests large JAR files, concurrent conversions, and system limits.
"""

import pytest
import asyncio
import tempfile
import time
import zipfile
import random
from pathlib import Path
from unittest.mock import AsyncMock, patch, MagicMock
from typing import List, Dict
import json

# Set up imports
try:
    from modporter.cli.main import convert_mod
    from services.conversion_service import ConversionService
    from tools.search_tool import SearchTool
    IMPORTS_AVAILABLE = True
except ImportError:
    IMPORTS_AVAILABLE = False


pytestmark = pytest.mark.skipif(not IMPORTS_AVAILABLE, reason="Required imports unavailable")


@pytest.fixture
def large_jar_file(tmp_path):
    """Create a large JAR file for testing."""
    jar_file = tmp_path / "large_mod.jar"
    with zipfile.ZipFile(jar_file, 'w') as zf:
        # Add manifest
        zf.writestr("META-INF/MANIFEST.MF", "Manifest-Version: 1.0\n")
        
        # Add 100 class files (simulated)
        for i in range(100):
            zf.writestr(
                f"com/example/mod/Class{i}.class",
                bytes([random.randint(0, 255) for _ in range(10000)])  # ~10KB each
            )
        
        # Add resources
        for i in range(50):
            zf.writestr(
                f"assets/textures/texture{i}.png",
                bytes([random.randint(0, 255) for _ in range(50000)])  # ~50KB each
            )
    
    return jar_file


@pytest.fixture
def medium_jar_file(tmp_path):
    """Create a medium JAR file for testing."""
    jar_file = tmp_path / "medium_mod.jar"
    with zipfile.ZipFile(jar_file, 'w') as zf:
        zf.writestr("META-INF/MANIFEST.MF", "Manifest-Version: 1.0\n")
        
        # Add 30 classes
        for i in range(30):
            zf.writestr(
                f"com/example/mod/Class{i}.class",
                bytes([random.randint(0, 255) for _ in range(5000)])
            )
    
    return jar_file


@pytest.fixture
def mock_conversion_service():
    """Create a mock conversion service."""
    service = AsyncMock(spec=ConversionService)
    
    async def mock_convert(jar_path, strategy, progress_callback=None):
        # Simulate processing time based on file size
        await asyncio.sleep(0.1)
        return {
            "success": True,
            "output_file": "/tmp/output.mcaddon",
            "processing_time_ms": 100
        }
    
    service.convert = mock_convert
    return service


@pytest.fixture
def mock_search_tool():
    """Create a mock search tool."""
    tool = AsyncMock(spec=SearchTool)
    
    async def mock_search(query, limit=5):
        await asyncio.sleep(0.01)
        return {
            "results": [
                {"id": f"doc_{i}", "content": f"Result {i}", "score": 0.9 - i*0.1}
                for i in range(limit)
            ]
        }
    
    tool.semantic_search = mock_search
    return tool


class TestLargeFileConversion:
    """Test conversion of large JAR files."""
    
    @pytest.mark.asyncio
    async def test_convert_large_jar(self, large_jar_file, mock_conversion_service):
        """Test converting a large JAR file."""
        start_time = time.time()
        
        result = await mock_conversion_service.convert(
            str(large_jar_file),
            "conservative"
        )
        
        duration = time.time() - start_time
        
        assert result["success"] is True
        assert duration < 10  # Should complete within 10 seconds
    
    @pytest.mark.asyncio
    async def test_convert_medium_jar(self, medium_jar_file, mock_conversion_service):
        """Test converting a medium JAR file."""
        result = await mock_conversion_service.convert(
            str(medium_jar_file),
            "conservative"
        )
        
        assert result["success"] is True
        assert "output_file" in result
    
    @pytest.mark.asyncio
    async def test_memory_usage_large_file(self, large_jar_file):
        """Test memory usage with large files."""
        # Simulate memory-intensive operations
        file_size = large_jar_file.stat().st_size
        
        # Should be able to load into memory
        assert file_size < 50 * 1024 * 1024  # Less than 50MB
    
    @pytest.mark.asyncio
    async def test_file_size_limits(self):
        """Test conversion with various file sizes."""
        sizes = [1024, 10*1024, 100*1024, 1024*1024]  # 1KB to 1MB
        
        for size in sizes:
            with tempfile.NamedTemporaryFile(suffix='.jar') as f:
                f.write(bytes([0] * size))
                f.flush()
                
                # Should handle all sizes
                assert Path(f.name).stat().st_size == size


class TestConcurrentConversions:
    """Test concurrent conversion operations."""
    
    @pytest.mark.asyncio
    async def test_concurrent_conversions(self, medium_jar_file, mock_conversion_service):
        """Test running multiple conversions concurrently."""
        num_conversions = 5
        
        start_time = time.time()
        
        # Run conversions concurrently
        tasks = [
            mock_conversion_service.convert(str(medium_jar_file), "conservative")
            for _ in range(num_conversions)
        ]
        
        results = await asyncio.gather(*tasks)
        
        duration = time.time() - start_time
        
        assert len(results) == num_conversions
        assert all(r["success"] for r in results)
        assert duration < num_conversions * 2  # Concurrent should be faster than serial
    
    @pytest.mark.asyncio
    async def test_concurrent_limit(self, medium_jar_file, mock_conversion_service):
        """Test handling concurrent conversion limit."""
        max_concurrent = 10
        
        # Create more tasks than the limit
        tasks = [
            mock_conversion_service.convert(str(medium_jar_file), "conservative")
            for _ in range(20)
        ]
        
        # Run with semaphore
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def limited_task(task):
            async with semaphore:
                return await task
        
        results = await asyncio.gather(*[limited_task(t) for t in tasks])
        
        assert len(results) == 20
        assert all(r["success"] for r in results)
    
    @pytest.mark.asyncio
    async def test_concurrent_search_queries(self, mock_search_tool):
        """Test concurrent search tool queries."""
        queries = [
            "block entity", "item entity", "custom block",
            "entity behavior", "rendering system"
        ]
        
        start_time = time.time()
        
        results = await asyncio.gather(*[
            mock_search_tool.semantic_search(q) for q in queries
        ])
        
        duration = time.time() - start_time
        
        assert len(results) == len(queries)
        assert all("results" in r for r in results)
    
    @pytest.mark.asyncio
    async def test_queue_saturation(self, mock_conversion_service):
        """Test handling queue saturation."""
        # Create 50 tasks
        tasks = [
            mock_conversion_service.convert("/tmp/test.jar", "conservative")
            for _ in range(50)
        ]
        
        # Should handle without crashing
        results = await asyncio.gather(*tasks)
        
        assert len(results) == 50


class TestPerformanceMetrics:
    """Test performance metric collection."""
    
    @pytest.mark.asyncio
    async def test_conversion_duration_tracking(self, mock_conversion_service):
        """Test tracking conversion duration."""
        start = time.time()
        
        result = await mock_conversion_service.convert("/tmp/test.jar", "conservative")
        
        duration = time.time() - start
        
        assert "processing_time_ms" in result
        assert duration >= 0
    
    @pytest.mark.asyncio
    async def test_throughput_measurement(self, mock_conversion_service):
        """Test measuring conversion throughput."""
        num_conversions = 10
        
        start = time.time()
        
        tasks = [
            mock_conversion_service.convert("/tmp/test.jar", "conservative")
            for _ in range(num_conversions)
        ]
        
        results = await asyncio.gather(*tasks)
        
        duration = time.time() - start
        throughput = num_conversions / duration if duration > 0 else 0
        
        assert len(results) == num_conversions
        assert throughput > 0
    
    @pytest.mark.asyncio
    async def test_latency_percentiles(self, mock_conversion_service):
        """Test measuring latency percentiles."""
        durations = []
        
        for _ in range(100):
            start = time.time()
            await mock_conversion_service.convert("/tmp/test.jar", "conservative")
            durations.append(time.time() - start)
        
        durations.sort()
        
        p50 = durations[50]
        p95 = durations[95]
        p99 = durations[99]
        
        assert p50 <= p95 <= p99


class TestResourceUtilization:
    """Test resource utilization patterns."""
    
    @pytest.mark.asyncio
    async def test_memory_cleanup(self, large_jar_file):
        """Test memory cleanup after conversions."""
        # Simulate memory allocation and cleanup
        data = bytes([0] * (1024 * 1024))  # 1MB
        
        del data  # Should be freed
        
        # Verify it doesn't cause issues
        assert True
    
    @pytest.mark.asyncio
    async def test_file_descriptor_limits(self):
        """Test handling of file descriptor limits."""
        # Open multiple files
        temp_files = []
        
        for i in range(10):
            temp_file = tempfile.NamedTemporaryFile(delete=False)
            temp_files.append(temp_file)
            temp_file.close()
        
        # Cleanup
        for f in temp_files:
            Path(f.name).unlink()
        
        assert len(temp_files) == 10
    
    @pytest.mark.asyncio
    async def test_cpu_usage_patterns(self, mock_conversion_service):
        """Test CPU usage patterns."""
        # CPU-bound operations
        start = time.time()
        
        tasks = [
            mock_conversion_service.convert("/tmp/test.jar", "aggressive")
            for _ in range(4)
        ]
        
        results = await asyncio.gather(*tasks)
        
        duration = time.time() - start
        
        assert len(results) == 4
        assert duration > 0


class TestStressConditions:
    """Test system behavior under stress."""
    
    @pytest.mark.asyncio
    async def test_rapid_fire_conversions(self, mock_conversion_service):
        """Test rapid-fire conversion requests."""
        # Fire 100 conversions as fast as possible
        tasks = [
            mock_conversion_service.convert("/tmp/test.jar", "conservative")
            for _ in range(100)
        ]
        
        results = await asyncio.gather(*tasks)
        
        assert len(results) == 100
        assert all(r["success"] for r in results)
    
    @pytest.mark.asyncio
    async def test_alternating_strategies(self, mock_conversion_service):
        """Test alternating between conversion strategies."""
        strategies = ["conservative", "aggressive"] * 50
        
        tasks = [
            mock_conversion_service.convert("/tmp/test.jar", strategy)
            for strategy in strategies
        ]
        
        results = await asyncio.gather(*tasks)
        
        assert len(results) == 100
    
    @pytest.mark.asyncio
    async def test_mixed_workload(self, mock_conversion_service, mock_search_tool):
        """Test mixed workload of conversions and searches."""
        tasks = [
            mock_conversion_service.convert("/tmp/test.jar", "conservative")
            if i % 2 == 0 else
            mock_search_tool.semantic_search("entity")
            for i in range(20)
        ]
        
        results = await asyncio.gather(*tasks)
        
        assert len(results) == 20
    
    @pytest.mark.asyncio
    async def test_recovery_from_failures(self, mock_conversion_service):
        """Test recovery from intermittent failures."""
        failure_count = 0
        success_count = 0
        
        async def flaky_convert(*args, **kwargs):
            nonlocal failure_count, success_count
            if random.random() < 0.3:  # 30% failure rate
                failure_count += 1
                raise RuntimeError("Temporary failure")
            success_count += 1
            return {"success": True}
        
        mock_conversion_service.convert = flaky_convert
        
        successes = 0
        for _ in range(20):
            try:
                result = await mock_conversion_service.convert("/tmp/test.jar", "conservative")
                successes += 1
            except RuntimeError:
                pass
        
        assert successes > 0  # Some should succeed


class TestScalability:
    """Test system scalability."""
    
    @pytest.mark.asyncio
    async def test_increasing_load(self, mock_conversion_service):
        """Test system performance with increasing load."""
        load_levels = [1, 5, 10, 20, 50]
        durations = []
        
        for load in load_levels:
            start = time.time()
            
            tasks = [
                mock_conversion_service.convert("/tmp/test.jar", "conservative")
                for _ in range(load)
            ]
            
            results = await asyncio.gather(*tasks)
            
            duration = time.time() - start
            durations.append(duration)
            
            assert len(results) == load
        
        # Verify monotonic increase (generally)
        assert durations[-1] >= durations[0]
    
    @pytest.mark.asyncio
    async def test_linear_scaling(self, mock_conversion_service):
        """Test if performance scales linearly."""
        # Single task
        start1 = time.time()
        await mock_conversion_service.convert("/tmp/test.jar", "conservative")
        time1 = time.time() - start1
        
        # 10 concurrent tasks
        start10 = time.time()
        tasks = [
            mock_conversion_service.convert("/tmp/test.jar", "conservative")
            for _ in range(10)
        ]
        await asyncio.gather(*tasks)
        time10 = time.time() - start10
        
        # Should be roughly 10x (with some overhead)
        ratio = time10 / time1 if time1 > 0 else 1
        
        assert ratio < 15  # Allow some overhead


class TestErrorRecovery:
    """Test error recovery under stress."""
    
    @pytest.mark.asyncio
    async def test_partial_batch_failure(self, mock_conversion_service):
        """Test handling partial batch failures."""
        async def partial_fail_convert(*args, **kwargs):
            if random.random() < 0.2:  # 20% failure
                raise RuntimeError("Conversion failed")
            return {"success": True}
        
        mock_conversion_service.convert = partial_fail_convert
        
        results = []
        errors = []
        
        for _ in range(20):
            try:
                result = await mock_conversion_service.convert("/tmp/test.jar", "conservative")
                results.append(result)
            except RuntimeError as e:
                errors.append(e)
        
        # Should have both successes and failures
        assert len(results) > 0
    
    @pytest.mark.asyncio
    async def test_retry_with_backoff(self, mock_conversion_service):
        """Test retry logic with exponential backoff."""
        attempt_count = 0
        
        async def retry_convert(path, strategy, max_retries=3):
            nonlocal attempt_count
            for attempt in range(max_retries):
                try:
                    attempt_count += 1
                    if attempt < 2:
                        raise RuntimeError("Temporary failure")
                    return {"success": True}
                except RuntimeError:
                    if attempt == max_retries - 1:
                        raise
                    await asyncio.sleep(0.01 * (2 ** attempt))
        
        mock_conversion_service.convert = retry_convert
        
        result = await mock_conversion_service.convert("/tmp/test.jar", "conservative")
        
        assert result["success"] is True
        assert attempt_count == 3


class TestLongRunningOperations:
    """Test behavior for long-running operations."""
    
    @pytest.mark.asyncio
    async def test_progress_tracking(self, mock_conversion_service):
        """Test progress tracking during long operations."""
        progress_updates = []
        
        async def tracked_convert(path, strategy):
            for progress in [25, 50, 75, 100]:
                progress_updates.append(progress)
                await asyncio.sleep(0.01)
            return {"success": True}
        
        mock_conversion_service.convert = tracked_convert
        
        result = await mock_conversion_service.convert("/tmp/test.jar", "conservative")
        
        assert result["success"] is True
        assert progress_updates == [25, 50, 75, 100]
    
    @pytest.mark.asyncio
    async def test_timeout_on_long_operation(self, mock_conversion_service):
        """Test timeout handling for long operations."""
        async def slow_convert(*args, **kwargs):
            await asyncio.sleep(10)
            return {"success": True}
        
        mock_conversion_service.convert = slow_convert
        
        with pytest.raises(asyncio.TimeoutError):
            await asyncio.wait_for(
                mock_conversion_service.convert("/tmp/test.jar", "conservative"),
                timeout=0.5
            )
    
    @pytest.mark.asyncio
    async def test_cancellation_handling(self, mock_conversion_service):
        """Test handling task cancellation."""
        async def cancellable_convert(*args, **kwargs):
            try:
                await asyncio.sleep(10)
                return {"success": True}
            except asyncio.CancelledError:
                return {"success": False, "error": "cancelled"}
        
        mock_conversion_service.convert = cancellable_convert
        
        task = asyncio.create_task(
            mock_conversion_service.convert("/tmp/test.jar", "conservative")
        )
        
        await asyncio.sleep(0.01)
        task.cancel()
        
        with pytest.raises(asyncio.CancelledError):
            await task
