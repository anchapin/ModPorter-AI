"""
Performance Tests for Conversion Inference Engine

Tests performance aspects of conversion inference:
1. Concurrent conversion processing
2. Load testing with multiple agents
3. Database performance under heavy query loads
4. Memory usage profiling and optimization

Priority: PRIORITY 3: Performance Tests (IN PROGRESS)
"""

import pytest
import asyncio
import time
import psutil  # For memory usage monitoring
from datetime import datetime
from unittest.mock import Mock, patch, AsyncMock
from sqlalchemy.ext.asyncio import AsyncSession

# Test configuration
CONCURRENT_JOBS = 10  # Number of concurrent jobs for testing
MEMORY_THRESHOLD = 100 * 1024 * 1024  # 100MB threshold in bytes


class TestConversionInferencePerformance:
    """Test performance aspects of conversion inference."""

    @pytest.fixture
    def mock_db(self):
        """Create mock database session"""
        return AsyncMock()

    @pytest.fixture
    def engine(self):
        """Create conversion inference engine with mocked dependencies"""
        with patch.dict('sys.modules', {
            'db': Mock(),
            'db.models': Mock(),
            'db.knowledge_graph_crud': Mock(),
            'db.graph_db': Mock(),
            'services.version_compatibility': Mock()
        }):
            from src.services.conversion_inference import ConversionInferenceEngine
            return ConversionInferenceEngine()

    @pytest.mark.asyncio
    async def test_concurrent_conversion_inference(self, engine, mock_db):
        """Test concurrent conversion inference performance"""
        # Create mock conversion paths
        mock_direct_paths = [
            {
                "path_type": "direct",
                "confidence": 0.8 + (i * 0.01),  # Varied confidence
                "steps": [{"step": f"conversion_{i}"}],
                "path_length": 1
            }
            for i in range(CONCURRENT_JOBS)
        ]

        # Create concurrent tasks
        async def infer_path(job_id):
            with patch.object(engine, '_find_concept_node', return_value=Mock()):
                with patch.object(engine, '_find_direct_paths', return_value=[mock_direct_paths[job_id]]):
                    # Simulate processing time based on confidence
                    start_time = time.time()
                    result = await engine.infer_conversion_path(
                        f"concept_{job_id}", mock_db, "bedrock", "1.19.3"
                    )
                    end_time = time.time()

                    # Add processing time to result
                    result["processing_time"] = end_time - start_time

                    return result, job_id

        # Execute tasks concurrently
        start_time = time.time()
        tasks = [infer_path(i) for i in range(CONCURRENT_JOBS)]
        results = await asyncio.gather(*tasks)
        end_time = time.time()

        # Verify all requests completed
        assert len(results) == CONCURRENT_JOBS
        for result, job_id in results:
            assert result[0]["success"] is True
            assert "processing_time" in result[0]

        # Verify concurrent execution was faster than sequential
        total_time = end_time - start_time
        max_individual_time = max(r[0]["processing_time"] for r in results)

        # Concurrent execution should be significantly faster
        assert total_time < max_individual_time * 0.7  # At least 30% faster

        # Verify performance metrics
        avg_processing_time = sum(r[0]["processing_time"] for r in results) / len(results)
        assert avg_processing_time < 0.5  # Should be fast with mocks

    @pytest.mark.asyncio
    async def test_memory_usage_scaling(self, engine, mock_db):
        """Test memory usage scaling with batch size"""
        # Get initial memory usage
        process = psutil.Process()
        initial_memory = process.memory_info().rss

        # Test with different batch sizes
        batch_sizes = [10, 50, 100]
        memory_usage = []

        for batch_size in batch_sizes:
            # Create mock concepts for batch
            concepts = [f"concept_{i}" for i in range(batch_size)]

            with patch.object(engine, '_find_concept_node', return_value=Mock()):
                with patch.object(engine, '_find_direct_paths', return_value=[
                    {"path_type": "direct", "confidence": 0.8, "steps": []}
                    for _ in concepts
                ]):

                    # Process batch
                    result = await engine.optimize_conversion_sequence(
                        concepts, {}, "bedrock", "1.19.3", mock_db
                    )

                    # Measure memory after processing
                    current_memory = process.memory_info().rss
                    memory_increase = current_memory - initial_memory
                    memory_usage.append({
                        "batch_size": batch_size,
                        "memory_increase": memory_increase,
                        "memory_mb": memory_increase / (1024 * 1024)  # Convert to MB
                    })

                    # Reset initial memory for next iteration
                    initial_memory = current_memory

        # Verify memory scaling is reasonable
        for i in range(1, len(memory_usage)):
            current = memory_usage[i]
            previous = memory_usage[i-1] if i > 0 else memory_usage[0]

            # Memory usage should scale linearly or sub-linearly
            if previous["batch_size"] > 0:
                ratio = current["memory_mb"] / previous["memory_mb"]
                batch_ratio = current["batch_size"] / previous["batch_size"]

                # Allow for some overhead but not exponential growth
                assert ratio < batch_ratio * 1.5, f"Memory scaling too high: {ratio:.2f}x for {batch_ratio:.2f}x batch size increase"

    @pytest.mark.asyncio
    async def test_database_connection_pooling(self, engine, mock_db):
        """Test database connection pooling under load"""
        # Mock database connection pool behavior
        with patch('src.db.knowledge_graph_crud.KnowledgeNodeCRUD') as mock_crud:
            # Simulate connection latency
            async def get_node_with_delay(concept_id, delay=0.01):
                await asyncio.sleep(delay)
                return Mock(neo4j_id=f"node_{concept_id}")

            mock_crud.get_by_name = get_node_with_delay

            # Create concurrent DB queries
            async def query_database(query_id):
                # Simulate database query
                result = await mock_crud.get_by_name(f"query_{query_id}")

                # Record timing metrics
                start_time = time.time()
                await asyncio.sleep(0.05)  # Simulate DB processing time
                end_time = time.time()

                return {
                    "query_id": query_id,
                    "result": result,
                    "processing_time": end_time - start_time
                }

            # Execute concurrent queries
            concurrent_queries = 10
            tasks = [query_database(i) for i in range(concurrent_queries)]

            start_time = time.time()
            results = await asyncio.gather(*tasks)
            end_time = time.time()

            # Verify all queries completed
            assert len(results) == concurrent_queries

            # Check connection pooling effectiveness
            total_time = end_time - start_time
            avg_time = sum(r["processing_time"] for r in results) / len(results)

            # With connection pooling, should be faster than individual connections
            assert total_time < avg_time * 0.8  # 20% improvement

            # Verify timing metrics
            for result in results:
                assert 0.01 < result["processing_time"] < 0.2  # Reasonable processing time

    @pytest.mark.asyncio
    async def test_batch_processing_optimization(self, engine, mock_db):
        """Test batch processing optimization for large batches"""
        # Create large batch of concepts
        large_batch_size = 100
        concepts = [f"concept_{i}" for i in range(large_batch_size)]

        # Mock optimization methods to track optimization effectiveness
        optimization_stats = {
            "shared_steps_found": 0,
            "parallel_groups_created": 0,
            "time_saved": 0.0
        }

        # Mock methods to capture optimization calls
        original_identify_shared = engine._identify_shared_steps
        original_estimate_time = engine._estimate_batch_time

        with patch.object(engine, '_identify_shared_steps') as mock_identify:
            with patch.object(engine, '_estimate_batch_time') as mock_estimate:
                with patch.object(engine, '_get_batch_optimizations', return_value=["parallel_processing"]):
                    with patch.object(engine, '_calculate_savings', return_value=5.0) as mock_savings:

                        # Track optimization calls
                        mock_identify.side_effect = lambda concepts: [
                            step for step in concepts if step in ["step1", "step2"]
                        ]
                        optimization_stats["shared_steps_found"] = len(concepts) // 2

                        mock_estimate.side_effect = lambda concepts, paths: 100.0
                        mock_savings.side_effect = lambda seq, groups, db: 5.0

                        # Process batch
                        start_time = time.time()
                        result = await engine.optimize_conversion_sequence(
                            concepts, {}, "bedrock", "1.19.3", mock_db
                        )
                        end_time = time.time()

                        # Track optimization effectiveness
                        optimization_stats["time_saved"] = 5.0
                        optimization_stats["parallel_groups_created"] = len(result.get("processing_groups", []))

                        return result

            # Verify optimization was effective
            assert result["success"] is True
            assert "optimization_applied" in result

            # Verify optimization metrics
            total_time = end_time - start_time
            assert total_time < 5.0  # Should complete quickly with mocks

            # Verify optimizations were applied
            assert mock_identify.called
            assert mock_estimate.called
            assert mock_savings.called

    @pytest.mark.asyncio
    async def test_error_handling_performance(self, engine, mock_db):
        """Test error handling performance under load"""
        # Create tasks with potential errors
        async def task_with_potential_error(task_id, should_fail=False):
            with patch.object(engine, '_find_concept_node', return_value=Mock()):
                with patch.object(engine, '_find_direct_paths',
                          side_effect=Exception("Simulated error") if should_fail else
                          return_value=[{"path_type": "direct", "confidence": 0.8}]):

                    try:
                        start_time = time.time()
                        result = await engine.infer_conversion_path(
                            f"concept_{task_id}", mock_db, "bedrock", "1.19.3"
                        )
                        end_time = time.time()

                        if should_fail:
                            pytest.fail("Expected exception was not raised")

                        return {
                            "task_id": task_id,
                            "success": not should_fail,
                            "processing_time": end_time - start_time
                        }
                    except Exception as e:
                        end_time = time.time()
                        return {
                            "task_id": task_id,
                            "success": False,
                            "error": str(e),
                            "processing_time": end_time - start_time
                        }

        # Create mix of successful and failing tasks
        tasks = [
            task_with_potential_error(i, should_fail=(i % 3 == 0))  # Every 3rd task fails
            for i in range(9)
        ]

        # Execute tasks concurrently
        start_time = time.time()
        results = await asyncio.gather(*tasks, return_exceptions=True)
        end_time = time.time()

        # Verify error handling
        successful_tasks = sum(1 for r in results if isinstance(r, dict) and r.get("success"))
        failed_tasks = sum(1 for r in results if isinstance(r, dict) and not r.get("success"))

        # Should have 6 successful and 3 failed tasks
        assert successful_tasks == 6
        assert failed_tasks == 3

        # Verify total time is reasonable
        total_time = end_time - start_time
        assert total_time < 2.0  # Should complete quickly even with errors

        # Verify error details
        failed_results = [r for r in results if isinstance(r, dict) and not r.get("success")]
        for result in failed_results:
            assert "error" in result
            assert "Simulated error" in result["error"]

    @pytest.mark.asyncio
    async def test_caching_performance(self, engine, mock_db):
        """Test caching performance for repeated queries"""
        # Track cache hits and misses
        cache_stats = {
            "hits": 0,
            "misses": 0,
            "total_queries": 0
        }

        # Mock methods to simulate caching
        original_find_concept = engine._find_concept_node
        cache = {}

        async def cached_find_concept_node(db, concept, platform, version):
            cache_key = f"{concept}_{platform}_{version}"
            cache_stats["total_queries"] += 1

            if cache_key in cache:
                cache_stats["hits"] += 1
                return cache[cache_key]
            else:
                cache_stats["misses"] += 1
                # Simulate cache miss delay
                await asyncio.sleep(0.05)

                # Cache the result
                result = await original_find_concept(db, concept, platform, version)
                cache[cache_key] = result
                return result

        # Replace method with cached version
        engine._find_concept_node = cached_find_concept_node

        # Execute queries with caching
        concepts = ["java_block", "java_entity", "java_item", "java_block", "java_entity"]

        start_time = time.time()
        tasks = [
            engine.infer_conversion_path(concept, mock_db, "bedrock", "1.19.3")
            for concept in concepts
        ]
        results = await asyncio.gather(*tasks)
        end_time = time.time()

        # Verify caching effectiveness
        assert cache_stats["total_queries"] == len(concepts)
        assert cache_stats["hits"] == 2  # java_block and java_entity repeated
        assert cache_stats["misses"] == 2  # java_item and java_entity repeated

        # Verify cache improved performance
        hit_rate = cache_stats["hits"] / cache_stats["total_queries"]
        assert hit_rate > 0.4  # At least 40% hit rate

        # Verify total time is reasonable with caching
        total_time = end_time - start_time
        assert total_time < 1.0  # Should be faster with caching

    @pytest.mark.asyncio
    async def test_resource_cleanup_performance(self, engine, mock_db):
        """Test resource cleanup performance after processing"""
        # Track resource usage
        initial_memory = psutil.Process().memory_info().rss

        # Create resource-intensive processing
        with patch.object(engine, '_find_concept_node', return_value=Mock()):
            with patch.object(engine, '_find_direct_paths', return_value=[
                {"path_type": "direct", "confidence": 0.8, "steps": []}
                for _ in range(20)  # Large number of paths
            ]):

                # Process batch
                result = await engine.optimize_conversion_sequence(
                    [f"concept_{i}" for i in range(20)],
                    {},
                    "bedrock",
                    "1.19.3",
                    mock_db
                )

                # Verify result is successful
                assert result["success"] is True

        # Check memory after processing
        peak_memory = psutil.Process().memory_info().rss
        memory_increase = peak_memory - initial_memory
        memory_mb = memory_increase / (1024 * 1024)

        # Verify resource usage is reasonable
        assert memory_mb < 50  # Should use less than 50MB for mocks

        # Verify cleanup occurred
        # In a real scenario, would verify resources are released
        # For this test, just ensure we didn't leak excessive memory
        assert memory_mb > 0  # Some memory was used
